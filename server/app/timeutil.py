"""Local-time helpers.

Everything is stored as UTC epoch seconds. Local calendar fields are computed
here with the IANA time-zone database (zoneinfo), never with SQLite's own date
functions, which know nothing about daylight saving time.

America/Chicago is always a whole number of hours from UTC, so a UTC hour and
a local hour start at the same instant. That lets hourly buckets be keyed by
"UTC hour start" and still be exact local hours, including the 23-hour day in
March and the 25-hour day in November.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Iterator
from zoneinfo import ZoneInfo

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@lru_cache(maxsize=8)
def tz(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def local_dt(ts: int, tzname: str) -> datetime:
    return datetime.fromtimestamp(ts, tz(tzname))


def local_parts(ts: int, tzname: str) -> tuple[str, int]:
    """(local 'YYYY-MM-DD', local hour 0-23) for a UTC epoch."""
    dt = local_dt(ts, tzname)
    return dt.strftime("%Y-%m-%d"), dt.hour


def local_midnight(d: date, tzname: str) -> int:
    """UTC epoch of 00:00 local time on date d."""
    return int(datetime(d.year, d.month, d.day, tzinfo=tz(tzname)).timestamp())


def iso_local(ts: int, tzname: str) -> str:
    """ISO 8601 with offset, e.g. 2026-11-01T01:00:00-05:00."""
    return local_dt(ts, tzname).isoformat(timespec="seconds")


def parse_date(text: str) -> date:
    if len(text) != 10:
        raise ValueError("date must be YYYY-MM-DD")
    return datetime.strptime(text, "%Y-%m-%d").date()


def iter_days(start: date, end: date) -> Iterator[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def iter_hours(start_ts: int, end_ts: int, tzname: str) -> Iterator[tuple[int, str, int, datetime]]:
    """Every hour bucket in [start_ts, end_ts): (utc_hour_start, local_date, local_hour, dt).

    Stepping in UTC is what makes DST come out right: the spring-forward day
    yields 23 buckets (no 02:00) and the fall-back day 25 (01:00 twice, with
    different offsets).
    """
    zone = tz(tzname)
    ts = start_ts - (start_ts % 3600)
    if ts < start_ts:
        ts += 3600
    while ts < end_ts:
        dt = datetime.fromtimestamp(ts, timezone.utc).astimezone(zone)
        yield ts, dt.strftime("%Y-%m-%d"), dt.hour, dt
        ts += 3600
