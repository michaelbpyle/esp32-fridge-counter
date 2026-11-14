"""Validate and store one device POST."""

from __future__ import annotations

import hmac
import math
from typing import Any

from . import db
from .config import DEVICE_ID_RE, NAME_RE, Settings
from .timeutil import local_parts

INT64_MAX = 2**63 - 1


class BadRequest(Exception):
    """Malformed body; the message is short and safe to return to the client."""


def match_device_key(settings: Settings, presented: str | None) -> str | None:
    """Return the device id whose key equals `presented`, else None.

    Every configured key is compared, each in constant time, so the time taken
    does not depend on which key (if any) matched.
    """
    if not presented:
        presented = ""
    found: str | None = None
    given = presented.encode("utf-8", "surrogatepass")
    for dev, key in settings.device_keys.items():
        if hmac.compare_digest(given, key.encode("utf-8")) and key:
            found = dev
    return found


def _as_int(value: Any, lo: int = 0, hi: int = INT64_MAX) -> int | None:
    """An integer in range, or None. Rejects booleans, NaN, fractions."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value) or value != int(value):
            return None
        value = int(value)
    if not isinstance(value, int):
        return None
    return value if lo <= value <= hi else None


def _as_num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    f = float(value)
    return f if math.isfinite(f) else None


def _text(value: Any, limit: int = 32) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if ch.isprintable())[:limit]
    return cleaned or None


def resolve_time(t: Any, age_s: Any, now: int, s: Settings) -> tuple[int, str]:
    """Decide the UTC time of an item and how much to trust it.

    device   - the device had a clock and its timestamp is plausible
    approx   - no usable clock; receive time minus the reported age
    received - no clock and no age; the receive time is all we have
    clamped  - the device timestamp was in the future; re-timed from the
               receive time (minus age if given) so it cannot land in the future
    """
    t_int = _as_int(t)
    age = _as_num(age_s)
    if age is not None and not 0 <= age <= s.max_age_s:
        age = None
    fallback = now - int(age) if age is not None else now
    if t_int is not None and t_int >= s.min_valid_epoch:
        if t_int > now + s.future_tolerance_s:
            return fallback, "clamped"
        return min(t_int, now), "device"
    return (fallback, "approx") if age is not None else (now, "received")


def validate(body: Any, s: Settings) -> dict:
    """Check the envelope. Raises BadRequest for anything structurally wrong."""
    if not isinstance(body, dict):
        raise BadRequest("body must be a JSON object")
    device_id = body.get("device_id")
    if not isinstance(device_id, str) or not DEVICE_ID_RE.match(device_id):
        raise BadRequest("device_id missing or invalid")
    events = body.get("events", [])
    readings = body.get("readings", [])
    status = body.get("status", {})
    if events is None:
        events = []
    if readings is None:
        readings = []
    if status is None:
        status = {}
    if not isinstance(events, list):
        raise BadRequest("events must be a list")
    if not isinstance(readings, list):
        raise BadRequest("readings must be a list")
    if not isinstance(status, dict):
        raise BadRequest("status must be an object")
    if len(events) > s.max_events:
        raise BadRequest(f"too many events (max {s.max_events})")
    if len(readings) > s.max_readings:
        raise BadRequest(f"too many readings (max {s.max_readings})")
    return {"device_id": device_id, "events": events, "readings": readings, "status": status}


def store(body: dict, parsed: dict, now: int, s: Settings) -> dict:
    """Write one POST in a single transaction. Returns the counts."""
    device_id = parsed["device_id"]
    boot_id = _as_int(body.get("boot_id"))
    accepted = duplicates = rejected = 0
    r_accepted = r_duplicates = r_rejected = 0
    status = parsed["status"]
    door_open = status.get("door_open")

    with db.write_tx(s.db_path) as conn:
        for ev in parsed["events"]:
            if not isinstance(ev, dict):
                rejected += 1
                continue
            n = _as_int(ev.get("n"))
            boot = _as_int(ev.get("boot"))
            if boot is None:
                boot = boot_id
            if n is None or boot is None:
                rejected += 1
                continue
            dur = ev.get("dur_ms")
            if dur is not None:
                dur = _as_int(dur, lo=-1, hi=INT64_MAX)
                if dur is None:
                    rejected += 1
                    continue
            ts, quality = resolve_time(ev.get("t"), ev.get("age_s"), now, s)
            local_date, local_hour = local_parts(ts, s.tz_name)
            cur = conn.execute(
                "INSERT OR IGNORE INTO events "
                "(device_id, boot, n, ts, time_quality, dur_ms, local_date, local_hour, received_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (device_id, boot, n, ts, quality, dur, local_date, local_hour, now),
            )
            if cur.rowcount == 1:
                accepted += 1
            else:
                duplicates += 1

        for rd in parsed["readings"]:
            if not isinstance(rd, dict):
                r_rejected += 1
                continue
            sensor, metric = rd.get("sensor"), rd.get("metric")
            value = _as_num(rd.get("value"))
            if (
                not isinstance(sensor, str)
                or not isinstance(metric, str)
                or not NAME_RE.match(sensor)
                or not NAME_RE.match(metric)
                or value is None
            ):
                r_rejected += 1
                continue
            ts, quality = resolve_time(rd.get("t"), rd.get("age_s"), now, s)
            local_date, _ = local_parts(ts, s.tz_name)
            cur = conn.execute(
                "INSERT OR IGNORE INTO readings "
                "(device_id, ts, time_quality, sensor, metric, value, local_date, received_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (device_id, ts, quality, sensor, metric, value, local_date, now),
            )
            if cur.rowcount == 1:
                r_accepted += 1
            else:
                r_duplicates += 1

        # Every POST, including an empty heartbeat, refreshes the device row.
        conn.execute(
            "INSERT INTO devices (device_id, first_seen, last_seen, post_count, fw, boot_id, uplink, "
            "uptime_s, door_total, rssi, heap, door_open, queue, dropped, reset_reason) "
            "VALUES (?,?,?,1,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(device_id) DO UPDATE SET "
            "last_seen=excluded.last_seen, post_count=devices.post_count+1, fw=excluded.fw, "
            "boot_id=excluded.boot_id, uplink=excluded.uplink, uptime_s=excluded.uptime_s, "
            "door_total=excluded.door_total, rssi=excluded.rssi, heap=excluded.heap, "
            "door_open=excluded.door_open, queue=excluded.queue, dropped=excluded.dropped, "
            "reset_reason=excluded.reset_reason",
            (
                device_id,
                now,
                now,
                _text(body.get("fw")),
                boot_id,
                _text(body.get("uplink")),
                _as_int(body.get("uptime_s")),
                _as_int(body.get("door_total")),
                _as_int(status.get("rssi"), lo=-1000, hi=1000),
                _as_int(status.get("heap")),
                (1 if door_open else 0) if isinstance(door_open, bool) else None,
                _as_int(status.get("queue")),
                _as_int(status.get("dropped")),
                _text(status.get("reset_reason")),
            ),
        )

    return {
        "accepted": accepted,
        "duplicates": duplicates,
        "rejected": rejected,
        "readings_accepted": r_accepted,
        "readings_duplicates": r_duplicates,
        "readings_rejected": r_rejected,
    }
