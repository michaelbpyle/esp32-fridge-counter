"""Settings, read once from environment variables.

Every tunable (data-quality rule, limit, window) lives here so there is one
place to look. Each can be overridden with an environment variable of the same
name prefixed FRIDGE_ (see fridge.env.example).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
NAME_RE = re.compile(r"^[a-z0-9_]{1,32}$")  # sensor and metric names


def _int(env: dict, name: str, default: int, lo: int, hi: int) -> int:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not lo <= val <= hi:
        raise ValueError(f"{name} must be between {lo} and {hi}")
    return val


def parse_device_keys(raw: str) -> dict[str, str]:
    """'fridge-01:KEY,bench-01:KEY' -> {'fridge-01': 'KEY', ...}."""
    out: dict[str, str] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        dev, sep, key = part.partition(":")
        dev, key = dev.strip(), key.strip()
        if not sep or not key or not DEVICE_ID_RE.match(dev):
            # Never echo the offending text: it may contain a key.
            raise ValueError("FRIDGE_DEVICE_KEYS has a malformed entry (want id:key,id:key)")
        if dev in out:
            raise ValueError(f"FRIDGE_DEVICE_KEYS lists device {dev} twice")
        out[dev] = key
    return out


@dataclass(frozen=True)
class Settings:
    db_path: str = "./data/fridge.db"
    device_keys: dict[str, str] = field(default_factory=dict)
    test_devices: frozenset[str] = frozenset()
    tz_name: str = "America/Chicago"

    # ---- data-quality rules (applied in queries; raw rows are never changed) ----
    # An opening shorter than this is treated as bounce / accidental and left
    # out of every public count. 0 disables the rule.
    min_open_ms: int = 1000
    # A device counts as "online" if it was heard from within this window.
    online_window_s: int = 40 * 60
    # Privacy: public numbers only include events before the most recent
    # boundary of this size (3600 = the top of the hour), so watching the
    # numbers change cannot reveal when a door opened more precisely than
    # this. 0 publishes immediately.
    publish_granularity_s: int = 3600

    # ---- ingest limits ----
    max_body_bytes: int = 64 * 1024
    max_events: int = 200
    max_readings: int = 500
    # A device timestamp further ahead of the server clock than this is not
    # believed; the row is re-timed from the receive time and marked.
    future_tolerance_s: int = 300
    # A device timestamp before this (2024-01-01 UTC) means "clock not set".
    min_valid_epoch: int = 1704067200
    # An age_s larger than this (90 days) is not believed.
    max_age_s: int = 90 * 86400
    ingest_per_min: int = 120  # per authenticated device
    auth_fail_per_min: int = 20  # per client address

    # ---- query limits ----
    max_hourly_days: int = 366
    max_daily_days: int = 3660
    max_readings_hour_days: int = 92
    cache_max_age_s: int = 60

    # Dev only: serve a folder of static files at / (never set in production).
    dev_static_dir: str = ""

    @property
    def public_devices_excluded(self) -> tuple[str, ...]:
        return tuple(sorted(self.test_devices))


def load_settings(env: dict | None = None) -> Settings:
    env = dict(os.environ) if env is None else env
    tests = frozenset(
        d.strip() for d in env.get("FRIDGE_TEST_DEVICES", "").split(",") if d.strip()
    )
    for d in tests:
        if not DEVICE_ID_RE.match(d):
            raise ValueError("FRIDGE_TEST_DEVICES has an invalid device id")
    d = Settings()
    return Settings(
        db_path=env.get("FRIDGE_DB_PATH", d.db_path),
        device_keys=parse_device_keys(env.get("FRIDGE_DEVICE_KEYS", "")),
        test_devices=tests,
        tz_name=env.get("FRIDGE_TZ", d.tz_name),
        min_open_ms=_int(env, "FRIDGE_MIN_OPEN_MS", d.min_open_ms, 0, 60_000),
        online_window_s=_int(env, "FRIDGE_ONLINE_WINDOW_S", d.online_window_s, 60, 86400),
        publish_granularity_s=_int(
            env, "FRIDGE_PUBLISH_GRANULARITY_S", d.publish_granularity_s, 0, 86400
        ),
        max_body_bytes=_int(env, "FRIDGE_MAX_BODY_BYTES", d.max_body_bytes, 1024, 1_048_576),
        max_events=_int(env, "FRIDGE_MAX_EVENTS", d.max_events, 1, 5000),
        max_readings=_int(env, "FRIDGE_MAX_READINGS", d.max_readings, 1, 5000),
        future_tolerance_s=_int(env, "FRIDGE_FUTURE_TOLERANCE_S", d.future_tolerance_s, 0, 86400),
        ingest_per_min=_int(env, "FRIDGE_INGEST_PER_MIN", d.ingest_per_min, 1, 100_000),
        auth_fail_per_min=_int(env, "FRIDGE_AUTH_FAIL_PER_MIN", d.auth_fail_per_min, 1, 100_000),
        cache_max_age_s=_int(env, "FRIDGE_CACHE_MAX_AGE_S", d.cache_max_age_s, 0, 3600),
        dev_static_dir=env.get("FRIDGE_DEV_STATIC_DIR", ""),
    )
