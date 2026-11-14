"""HTTP layer: POST ingest (device key) and GET aggregate endpoints (public)."""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
import threading
import time
from collections import deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from . import __version__, db, ingest
from .config import DEVICE_ID_RE, NAME_RE, Settings, load_settings
from .queries import NotFound, Queries, QueryError, publish_cutoff

PREFIX = "/fridge/api/v1"

log = logging.getLogger("fridge")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, separators=(",", ":"))


class StdoutHandler(logging.StreamHandler):
    """Writes to whatever sys.stdout is at the time of the log call."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value) -> None:
        pass


def setup_logging() -> None:
    if log.handlers:
        return
    handler = StdoutHandler()
    handler.setFormatter(JsonLogFormatter())
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


def event(msg: str, level: int = logging.INFO, **fields) -> None:
    log.log(level, msg, extra={"fields": fields})


class RateLimiter:
    """Sliding one-minute window per key, in memory (one process, one worker)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, now: float, record: bool = True) -> bool:
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= now - 60:
                q.popleft()
            if len(q) >= limit:
                return False
            if record:
                q.append(now)
            if len(self._hits) > 5000:  # forget idle keys so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= now - 60]:
                    del self._hits[k]
            return True

    def record(self, key: str, now: float) -> None:
        with self._lock:
            self._hits.setdefault(key, deque()).append(now)


def client_addr(request: Request) -> str:
    """Best-effort caller address, used only in memory for rate limiting.

    It is never stored or logged. All public traffic arrives through
    Cloudflare, which sets CF-Connecting-IP.
    """
    h = request.headers
    addr = h.get("cf-connecting-ip") or (h.get("x-forwarded-for") or "").split(",")[0].strip()
    return addr or (request.client.host if request.client else "unknown")


def err(status: int, message: str, **headers: str) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": message},
        status_code=status,
        headers={"Cache-Control": "no-store", **headers},
    )


def create_app(settings: Settings | None = None, clock=time.time) -> FastAPI:
    s = settings or load_settings()
    setup_logging()
    db.init_db(s.db_path, s.tz_name)
    limiter = RateLimiter()
    cache: dict[tuple, tuple[float, object]] = {}
    cache_lock = threading.Lock()
    state = {"data_version": 0}

    app = FastAPI(
        title="Hollygrove Community Fridge door counter",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = s

    event(
        "startup",
        version=__version__,
        devices=sorted(s.device_keys),
        test_devices=sorted(s.test_devices),
        tz=s.tz_name,
        min_open_ms=s.min_open_ms,
        publish_granularity_s=s.publish_granularity_s,
    )
    if not s.device_keys:
        event("no device keys configured; every ingest will be refused", logging.WARNING)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 - last line of defence; never leak a traceback
            log.exception("unhandled error", extra={"fields": {"path": request.url.path}})
            response = err(500, "internal error")
        event(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=round((time.perf_counter() - t0) * 1000, 1),
        )
        return response

    # ---- ingest ---------------------------------------------------------------

    @app.post(f"{PREFIX}/ingest")
    async def ingest_endpoint(request: Request):
        now_f = clock()
        now = int(now_f)
        addr = "ip:" + client_addr(request)

        # Too many recent bad keys from this address: stop checking keys at all.
        if not limiter.allow(addr, s.auth_fail_per_min, now_f, record=False):
            return err(429, "too many failed attempts; slow down", **{"Retry-After": "60"})

        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > s.max_body_bytes:
                    return err(413, f"body too large (max {s.max_body_bytes} bytes)")
            except ValueError:
                return err(400, "bad Content-Length")

        device = ingest.match_device_key(s, request.headers.get("x-device-key"))
        if device is None:
            limiter.record(addr, now_f)
            event("ingest refused", logging.WARNING, reason="bad or missing key")
            return err(401, "bad or missing device key")

        if not limiter.allow("dev:" + device, s.ingest_per_min, now_f):
            event("ingest rate limited", logging.WARNING, device=device)
            return err(429, "rate limit exceeded", **{"Retry-After": "30"})

        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > s.max_body_bytes:
                return err(413, f"body too large (max {s.max_body_bytes} bytes)")

        try:
            body = json.loads(bytes(raw).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            event("ingest malformed", logging.WARNING, device=device, reason="not valid JSON")
            return err(400, "body is not valid JSON")
        try:
            parsed = ingest.validate(body, s)
        except ingest.BadRequest as exc:
            event("ingest malformed", logging.WARNING, device=device, reason=str(exc))
            return err(400, str(exc))
        if parsed["device_id"] != device:
            limiter.record(addr, now_f)
            event("ingest refused", logging.WARNING, reason="key does not belong to device_id")
            return err(401, "device key does not match device_id")

        result = await run_in_threadpool(ingest.store, body, parsed, now, s)
        state["data_version"] += 1
        event("ingest", device=device, uplink=str(body.get("uplink"))[:16], **result)
        return JSONResponse(
            {
                "ok": True,
                "accepted": result["accepted"],
                "duplicates": result["duplicates"],
                "rejected": result["rejected"],
                "readings_accepted": result["readings_accepted"],
                "server_time": now,
            },
            headers={"Cache-Control": "no-store"},
        )

    # ---- public reads ---------------------------------------------------------

    def cache_headers() -> dict[str, str]:
        return {"Cache-Control": f"public, max-age={s.cache_max_age_s}"}

    def run_query(request: Request, name: str, fn):
        """Shared wrapper: device check, small in-process cache, error mapping."""
        now = int(clock())
        device = request.query_params.get("device") or None
        if device is not None and device != "all":
            if not DEVICE_ID_RE.match(device):
                raise QueryError("device is not a valid device id")
        else:
            device = None
        params = tuple(sorted((k, v) for k, v in request.query_params.items() if len(v) <= 64))
        key = (name, params, publish_cutoff(now, s), state["data_version"], now // 20)
        with cache_lock:
            hit = cache.get(key)
        if hit is not None:
            return hit[1]
        with db.session(s.db_path) as conn:
            if device is not None:
                known = device in s.device_keys or conn.execute(
                    "SELECT 1 FROM devices WHERE device_id = ?", (device,)
                ).fetchone()
                if not known:
                    raise NotFound("unknown device")
            result = fn(Queries(conn, s, now, device))
        with cache_lock:
            if len(cache) > 500:
                cache.clear()
            cache[key] = (time.monotonic(), result)
        return result

    def json_get(name: str, fn_factory):
        def endpoint(request: Request):
            try:
                data = run_query(request, name, fn_factory(request))
            except QueryError as exc:
                return err(400, str(exc))
            except NotFound as exc:
                return err(404, str(exc))
            return JSONResponse(data, headers=cache_headers())

        endpoint.__name__ = f"get_{name}"
        app.get(f"{PREFIX}/{name}")(endpoint)

    def qp(request: Request, name: str) -> str | None:
        v = request.query_params.get(name)
        if v is None or v == "":
            return None
        if len(v) > 64:
            raise QueryError(f"{name} is too long")
        return v

    json_get("summary", lambda r: lambda q: q.summary())
    json_get("hourly", lambda r: lambda q: q.hourly(qp(r, "start"), qp(r, "end")))
    json_get("daily", lambda r: lambda q: q.daily(qp(r, "start"), qp(r, "end")))
    json_get("heatmap", lambda r: lambda q: q.heatmap(qp(r, "start"), qp(r, "end")))
    json_get("durations", lambda r: lambda q: q.durations(qp(r, "start"), qp(r, "end")))

    def readings_factory(r: Request):
        metric = qp(r, "metric")
        sensor = qp(r, "sensor")
        if metric is None or not NAME_RE.match(metric):
            raise QueryError("metric is required (for example temp_c)")
        if sensor is not None and not NAME_RE.match(sensor):
            raise QueryError("sensor is not a valid name")
        bucket = qp(r, "bucket") or "hour"
        return lambda q: q.readings(metric, qp(r, "start"), qp(r, "end"), bucket, sensor)

    json_get("readings", readings_factory)

    @app.get(f"{PREFIX}/export.csv")
    def export_csv(request: Request):
        try:
            grain = qp(request, "grain") or "day"
            if grain not in ("hour", "day"):
                raise QueryError("grain must be hour or day")
            start, end = qp(request, "start"), qp(request, "end")
            rows = run_query(request, "export", lambda q: q.export_rows(grain, start, end))
        except QueryError as exc:
            return err(400, str(exc))
        except NotFound as exc:
            return err(404, str(exc))
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\r\n").writerows(rows)
        headers = cache_headers()
        headers["Content-Disposition"] = f'attachment; filename="hollygrove-fridge-openings-by-{grain}.csv"'
        return Response(buf.getvalue(), media_type="text/csv; charset=utf-8", headers=headers)

    @app.get(f"{PREFIX}/health")
    def health():
        try:
            with db.session(s.db_path) as conn:
                conn.execute("SELECT 1 FROM meta LIMIT 1").fetchone()
            ok = True
        except Exception:  # noqa: BLE001
            log.exception("health check failed")
            ok = False
        return JSONResponse(
            {"ok": ok, "service": "hollygrove-fridge", "version": __version__, "server_time": int(clock())},
            status_code=200 if ok else 503,
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(404)
    async def not_found(_request: Request, _exc):
        return err(404, "not found")

    @app.exception_handler(405)
    async def bad_method(_request: Request, _exc):
        return err(405, "method not allowed")

    if s.dev_static_dir:
        # Local testing only: serve the rendered dashboard next to the API.
        from fastapi.staticfiles import StaticFiles

        event("DEV static files enabled", logging.WARNING, dir=s.dev_static_dir)
        app.mount("/", StaticFiles(directory=s.dev_static_dir, html=True), name="dev-static")

    return app


def app_factory() -> FastAPI:
    """Entry point for: uvicorn app.main:app_factory --factory"""
    return create_app()
