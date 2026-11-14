"""SQLite storage: one file, WAL mode, a fresh connection per request."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per device: the latest heartbeat / status.
CREATE TABLE IF NOT EXISTS devices (
    device_id    TEXT PRIMARY KEY,
    first_seen   INTEGER NOT NULL,   -- UTC epoch, server clock
    last_seen    INTEGER NOT NULL,   -- UTC epoch, server clock
    post_count   INTEGER NOT NULL DEFAULT 0,
    fw           TEXT,
    boot_id      INTEGER,
    uplink       TEXT,
    uptime_s     INTEGER,
    door_total   INTEGER,
    rssi         INTEGER,
    heap         INTEGER,
    door_open    INTEGER,
    queue        INTEGER,
    dropped      INTEGER,
    reset_reason TEXT
);

-- One row per door opening, stored raw. Nothing is ever filtered on the way in.
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY,
    device_id    TEXT    NOT NULL,
    boot         INTEGER NOT NULL,
    n            INTEGER NOT NULL,
    ts           INTEGER NOT NULL,   -- UTC epoch of the opening
    time_quality TEXT    NOT NULL,   -- device | approx | received | clamped
    dur_ms       INTEGER,            -- -1 = held open past the device limit; NULL = not reported
    local_date   TEXT    NOT NULL,   -- YYYY-MM-DD in the configured time zone
    local_hour   INTEGER NOT NULL,   -- 0-23 in the configured time zone
    received_at  INTEGER NOT NULL,
    UNIQUE (device_id, boot, n)
);
CREATE INDEX IF NOT EXISTS idx_events_ts    ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_local ON events (local_date, local_hour);

-- Generic sensor readings: a new sensor or metric needs no schema change.
CREATE TABLE IF NOT EXISTS readings (
    id           INTEGER PRIMARY KEY,
    device_id    TEXT    NOT NULL,
    ts           INTEGER NOT NULL,
    time_quality TEXT    NOT NULL,
    sensor       TEXT    NOT NULL,
    metric       TEXT    NOT NULL,
    value        REAL    NOT NULL,
    local_date   TEXT    NOT NULL,
    received_at  INTEGER NOT NULL,
    UNIQUE (device_id, sensor, metric, ts)
);
CREATE INDEX IF NOT EXISTS idx_readings_metric_ts ON readings (metric, ts);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str, tz_name: str) -> None:
    folder = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(folder, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('tz', ?)", (tz_name,))
    finally:
        conn.close()


@contextmanager
def session(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def write_tx(db_path: str) -> Iterator[sqlite3.Connection]:
    """A single write transaction; takes the write lock up front."""
    conn = connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()
