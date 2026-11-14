from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

CHI = ZoneInfo("America/Chicago")
KEY = "test-key-fridge-01-abcdefghijklmnop"
BENCH_KEY = "test-key-bench-01-qrstuvwxyz012345"
API = "/fridge/api/v1"


def chi(y, mo, d, h=0, mi=0, s=0, fold=0) -> int:
    """UTC epoch of a Chicago wall-clock time (fold=1 = second 1 AM on fall-back day)."""
    return int(datetime(y, mo, d, h, mi, s, tzinfo=CHI, fold=fold).timestamp())


class Clock:
    def __init__(self, now: int):
        self.now = now

    def __call__(self) -> float:
        return float(self.now)


class Env:
    """A running app with a controllable clock and helpers to post and query."""

    def __init__(self, tmp_path, **overrides):
        self.clock = Clock(chi(2026, 11, 14, 15, 20, 0))
        base = dict(
            db_path=str(tmp_path / "fridge.db"),
            device_keys={"fridge-01": KEY, "bench-01": BENCH_KEY},
            test_devices=frozenset({"bench-01"}),
        )
        base.update(overrides)
        self.settings = Settings(**base)
        self.client = TestClient(create_app(self.settings, clock=self.clock))
        self._n = 0

    def post(self, body, key=KEY, **kw):
        headers = {"Content-Type": "application/json"}
        if key is not None:
            headers["X-Device-Key"] = key
        headers.update(kw.pop("headers", {}))
        return self.client.post(f"{API}/ingest", json=body, headers=headers, **kw)

    def body(self, events=(), readings=(), device="fridge-01", **extra):
        b = {
            "device_id": device, "fw": "1.0.0", "boot_id": 111, "uplink": "wifi",
            "sent_at": self.clock.now, "uptime_s": 1234, "door_total": 42,
            "events": None if events is None else list(events),
            "readings": None if readings is None else list(readings),
            "status": {"rssi": -61, "heap": 123456, "door_open": False, "queue": 0,
                       "dropped": 0, "reset_reason": "poweron"},
        }
        b.update(extra)
        return b

    def ev(self, t, dur_ms=8000, boot=111, **extra):
        self._n += 1
        e = {"boot": boot, "n": self._n, "t": t, "age_s": 0, "dur_ms": dur_ms}
        e.update(extra)
        return e

    def add(self, times, device="fridge-01", key=KEY, dur_ms=8000, backdate=True):
        """Post events at the given epochs, in chunks, asserting success."""
        evs = [self.ev(t, dur_ms=dur_ms) for t in times]
        for i in range(0, len(evs), 100):
            r = self.post(self.body(events=evs[i:i + 100], device=device), key=key)
            assert r.status_code == 200, r.text
        if backdate:
            self.backdate()
        return evs

    def backdate(self):
        """Pretend every stored row was uploaded the moment it happened.

        Rows are only published once the hour in which they were *received*
        is over; tests that load history "now" call this so that history is
        visible, exactly as it would be had it arrived live.
        """
        import sqlite3
        conn = sqlite3.connect(self.settings.db_path)
        try:
            conn.execute("UPDATE events SET received_at = ts")
            conn.execute("UPDATE readings SET received_at = ts")
            conn.commit()
        finally:
            conn.close()

    def get(self, name, **params):
        r = self.client.get(f"{API}/{name}", params=params)
        return r

    def rows(self, sql, args=()):
        import sqlite3
        conn = sqlite3.connect(self.settings.db_path)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


@pytest.fixture
def make_env(tmp_path):
    def factory(**overrides):
        return Env(tmp_path, **overrides)
    return factory
