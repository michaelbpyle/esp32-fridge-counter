"""Public, aggregate-only read queries.

Privacy rule (enforced here, tested in tests/test_privacy.py): nothing in this
module returns an individual event or its timestamp. The finest bucket is one
hour, and a row only becomes visible once the publish boundary (by default the
top of the hour) has passed both its event time and its receive time, so even
watching the totals change cannot time an opening more finely than that.
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import date, timedelta

from .config import Settings
from .timeutil import (
    WEEKDAYS,
    iso_local,
    iter_days,
    iter_hours,
    local_dt,
    local_midnight,
    parse_date,
)

# Open-duration histogram edges in seconds. The first bin starts at the
# bounce threshold (min_open_ms); the last bin is open-ended. "Held open"
# (dur_ms = -1) is reported separately, never put in a bin.
DURATION_EDGES_S = [5, 15, 30, 60, 120, 300]


class QueryError(Exception):
    """Bad query parameter; message is safe to show."""


class NotFound(Exception):
    pass


def publish_cutoff(now: int, s: Settings) -> int:
    g = s.publish_granularity_s
    return now - (now % g) if g > 0 else now + 1


class Queries:
    def __init__(self, conn: sqlite3.Connection, s: Settings, now: int, device: str | None = None):
        self.conn = conn
        self.s = s
        self.now = now
        self.cutoff = publish_cutoff(now, s)
        self.device = device
        self.today = local_dt(now, s.tz_name).date()

    # ---- shared WHERE pieces -------------------------------------------------

    def _dev(self, col: str = "device_id") -> tuple[str, list]:
        if self.device is not None:
            return f"{col} = ?", [self.device]
        excluded = self.s.public_devices_excluded
        if not excluded:
            return "1=1", []
        marks = ",".join("?" for _ in excluded)
        return f"{col} NOT IN ({marks})", list(excluded)

    def _visible(self) -> tuple[str, list]:
        """Rows the public may see: published, and from the right device(s)."""
        dev_sql, dev_args = self._dev()
        return f"ts < ? AND received_at < ? AND {dev_sql}", [self.cutoff, self.cutoff, *dev_args]

    def _counted(self) -> tuple[str, list]:
        """Visible rows that count as a real opening (data-quality rule)."""
        vis_sql, vis_args = self._visible()
        return (
            f"{vis_sql} AND (dur_ms IS NULL OR dur_ms = -1 OR dur_ms >= ?)",
            [*vis_args, self.s.min_open_ms],
        )

    def _count(self, extra_sql: str = "1=1", extra_args: list | None = None) -> int:
        sql, args = self._counted()
        row = self.conn.execute(
            f"SELECT COUNT(*) FROM events WHERE {sql} AND {extra_sql}", [*args, *(extra_args or [])]
        ).fetchone()
        return int(row[0])

    # ---- range handling ------------------------------------------------------

    def first_date(self) -> date | None:
        sql, args = self._counted()
        row = self.conn.execute(f"SELECT MIN(local_date) FROM events WHERE {sql}", args).fetchone()
        return parse_date(row[0]) if row and row[0] else None

    def resolve_range(
        self, start: str | None, end: str | None, default_days: int, max_days: int
    ) -> tuple[date, date, date | None]:
        """Validate ?start&end (inclusive local dates).

        Returns (start, end, effective_start). `end` is capped at today.
        effective_start is the later of `start` and the first day with data,
        or None when the range holds nothing: days before the counter existed
        are not reported as zeros.
        """
        try:
            end_d = parse_date(end) if end else self.today
            start_d = parse_date(start) if start else end_d - timedelta(days=default_days - 1)
        except ValueError:
            raise QueryError("start and end must be dates like 2026-11-14") from None
        if start_d > end_d:
            raise QueryError("start must not be after end")
        if (end_d - start_d).days + 1 > max_days:
            raise QueryError(f"range too long (max {max_days} days)")
        end_d = min(end_d, self.today)
        first = self.first_date()
        if first is None or first > end_d or start_d > end_d:
            return start_d, end_d, None
        return start_d, end_d, max(start_d, first)

    def _span(self, eff: date, end: date) -> tuple[int, int]:
        """[start_ts, end_ts) covering the local days eff..end, capped at the cutoff."""
        tzn = self.s.tz_name
        return local_midnight(eff, tzn), min(local_midnight(end + timedelta(days=1), tzn), self.cutoff)

    def _base(self, start: date, end: date, eff: date | None) -> dict:
        return {
            "tz": self.s.tz_name,
            "device": self.device or "all",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "effective_start": eff.isoformat() if eff else None,
            "data_through": iso_local(min(self.cutoff, self.now), self.s.tz_name),
        }

    # ---- endpoints -----------------------------------------------------------

    def hourly(self, start: str | None, end: str | None) -> dict:
        s_d, e_d, eff = self.resolve_range(start, end, 7, self.s.max_hourly_days)
        out = self._base(s_d, e_d, eff)
        out["hours"] = []
        if eff is None:
            return out
        t0, t1 = self._span(eff, e_d)
        sql, args = self._counted()
        rows = self.conn.execute(
            f"SELECT (ts/3600)*3600 AS h, COUNT(*) FROM events "
            f"WHERE {sql} AND ts >= ? AND ts < ? GROUP BY h",
            [*args, t0, t1],
        ).fetchall()
        counts = {int(r[0]): int(r[1]) for r in rows}
        for ts, d, hour, dt in iter_hours(t0, t1, self.s.tz_name):
            out["hours"].append(
                {
                    "t": dt.isoformat(timespec="seconds"),
                    "date": d,
                    "hour": hour,
                    "count": counts.get(ts, 0),
                }
            )
        return out

    def daily(self, start: str | None, end: str | None) -> dict:
        s_d, e_d, eff = self.resolve_range(start, end, 30, self.s.max_daily_days)
        out = self._base(s_d, e_d, eff)
        out["days"] = []
        if eff is None:
            return out
        first = self.first_date()
        lead = max(first, eff - timedelta(days=6))  # extra days so the trend line starts full
        sql, args = self._counted()
        rows = self.conn.execute(
            f"SELECT local_date, COUNT(*), "
            f"AVG(CASE WHEN dur_ms >= 0 THEN dur_ms END), "
            f"SUM(CASE WHEN dur_ms = -1 THEN 1 ELSE 0 END) "
            f"FROM events WHERE {sql} AND local_date >= ? AND local_date <= ? GROUP BY local_date",
            [*args, lead.isoformat(), e_d.isoformat()],
        ).fetchall()
        by_date = {r[0]: r for r in rows}
        window: list[int] = []
        for d in iter_days(lead, e_d):
            key = d.isoformat()
            r = by_date.get(key)
            count = int(r[1]) if r else 0
            complete = d < self.today
            avg7 = None
            if complete:
                window.append(count)
                if len(window) > 7:
                    window.pop(0)
                if len(window) == 7:
                    avg7 = round(sum(window) / 7, 2)
            if d < eff:
                continue
            out["days"].append(
                {
                    "date": key,
                    "weekday": d.weekday(),
                    "count": count,
                    "avg7": avg7,
                    "avg_open_s": round(r[2] / 1000, 1) if r and r[2] is not None else None,
                    "held_open": int(r[3]) if r else 0,
                    "complete": complete,
                }
            )
        return out

    def heatmap(self, start: str | None, end: str | None) -> dict:
        s_d, e_d, eff = self.resolve_range(start, end, 30, self.s.max_daily_days)
        out = self._base(s_d, e_d, eff)
        out.update({"cells": [], "by_hour": [], "by_weekday": [], "weekday_names": WEEKDAYS})
        if eff is None:
            return out
        t0, t1 = self._span(eff, e_d)
        sql, args = self._counted()
        rows = self.conn.execute(
            f"SELECT local_date, local_hour, COUNT(*) FROM events "
            f"WHERE {sql} AND ts >= ? AND ts < ? GROUP BY local_date, local_hour",
            [*args, t0, t1],
        ).fetchall()
        total = [[0] * 24 for _ in range(7)]
        occ = [[0] * 24 for _ in range(7)]
        day_total: dict[str, int] = {}
        for d, hour, c in rows:
            total[parse_date(d).weekday()][hour] += int(c)
            day_total[d] = day_total.get(d, 0) + int(c)
        # Denominators: how many times each (weekday, hour) actually happened
        # in the range. Counting real hours handles DST and partial days.
        for _ts, d, hour, _dt in iter_hours(t0, t1, self.s.tz_name):
            occ[parse_date(d).weekday()][hour] += 1
        for wd in range(7):
            for hour in range(24):
                n = occ[wd][hour]
                out["cells"].append(
                    {
                        "weekday": wd,
                        "hour": hour,
                        "total": total[wd][hour],
                        "hours": n,
                        "avg": round(total[wd][hour] / n, 2) if n else None,
                    }
                )
        for hour in range(24):
            t = sum(total[wd][hour] for wd in range(7))
            n = sum(occ[wd][hour] for wd in range(7))
            out["by_hour"].append(
                {"hour": hour, "total": t, "hours": n, "avg": round(t / n, 2) if n else None}
            )
        # Per-weekday averages use complete days only (today is still filling).
        wd_total, wd_days = [0] * 7, [0] * 7
        for d in iter_days(eff, e_d):
            if d >= self.today:
                continue
            wd_days[d.weekday()] += 1
            wd_total[d.weekday()] += day_total.get(d.isoformat(), 0)
        for wd in range(7):
            out["by_weekday"].append(
                {
                    "weekday": wd,
                    "name": WEEKDAYS[wd],
                    "total": wd_total[wd],
                    "days": wd_days[wd],
                    "avg": round(wd_total[wd] / wd_days[wd], 2) if wd_days[wd] else None,
                }
            )
        return out

    def durations(self, start: str | None, end: str | None) -> dict:
        s_d, e_d, eff = self.resolve_range(start, end, 30, self.s.max_daily_days)
        out = self._base(s_d, e_d, eff)
        min_s = self.s.min_open_ms / 1000
        edges = [min_s] + [e for e in DURATION_EDGES_S if e > min_s]
        bins = [
            {"min_s": lo, "max_s": hi, "count": 0}
            for lo, hi in zip(edges, edges[1:] + [None])
        ]
        out.update(
            {
                "bins": bins,
                "measured": 0,
                "held_open": 0,
                "not_reported": 0,
                "too_short_excluded": 0,
                "median_s": None,
                "mean_s": None,
                "p90_s": None,
            }
        )
        if eff is None:
            return out
        t0, t1 = self._span(eff, e_d)
        vis_sql, vis_args = self._visible()
        rows = self.conn.execute(
            f"SELECT dur_ms FROM events WHERE {vis_sql} AND ts >= ? AND ts < ?",
            [*vis_args, t0, t1],
        ).fetchall()
        measured: list[float] = []
        for (dur,) in rows:
            if dur is None:
                out["not_reported"] += 1
            elif dur == -1:
                out["held_open"] += 1
            elif dur < self.s.min_open_ms:
                out["too_short_excluded"] += 1
            else:
                sec = dur / 1000
                measured.append(sec)
                for b in bins:
                    if sec >= b["min_s"] and (b["max_s"] is None or sec < b["max_s"]):
                        b["count"] += 1
                        break
        out["measured"] = len(measured)
        if measured:
            measured.sort()
            out["median_s"] = round(statistics.median(measured), 1)
            out["mean_s"] = round(statistics.fmean(measured), 1)
            out["p90_s"] = round(measured[min(len(measured) - 1, int(0.9 * len(measured)))], 1)
        return out

    def readings(
        self, metric: str, start: str | None, end: str | None, bucket: str, sensor: str | None
    ) -> dict:
        if bucket not in ("hour", "day"):
            raise QueryError("bucket must be hour or day")
        max_days = self.s.max_readings_hour_days if bucket == "hour" else self.s.max_daily_days
        try:
            end_d = parse_date(end) if end else self.today
            start_d = parse_date(start) if start else end_d - timedelta(days=6)
        except ValueError:
            raise QueryError("start and end must be dates like 2026-11-14") from None
        if start_d > end_d:
            raise QueryError("start must not be after end")
        if (end_d - start_d).days + 1 > max_days:
            raise QueryError(f"range too long for bucket={bucket} (max {max_days} days)")
        end_d = min(end_d, self.today)
        out = self._base(start_d, end_d, start_d if start_d <= end_d else None)
        out.update({"metric": metric, "bucket": bucket, "series": []})
        if start_d > end_d:
            return out
        t0, t1 = self._span(start_d, end_d)
        vis_sql, vis_args = self._visible()
        key = "(ts/3600)*3600" if bucket == "hour" else "local_date"
        extra, extra_args = ("AND sensor = ?", [sensor]) if sensor else ("", [])
        rows = self.conn.execute(
            f"SELECT sensor, {key} AS b, AVG(value), MIN(value), MAX(value), COUNT(*) "
            f"FROM readings WHERE {vis_sql} AND metric = ? AND ts >= ? AND ts < ? {extra} "
            f"GROUP BY sensor, b ORDER BY sensor, b",
            [*vis_args, metric, t0, t1, *extra_args],
        ).fetchall()
        series: dict[str, list] = {}
        for sensor_name, b, avg, lo, hi, n in rows:
            label = iso_local(int(b), self.s.tz_name) if bucket == "hour" else b
            series.setdefault(sensor_name, []).append(
                {"t": label, "avg": round(avg, 3), "min": round(lo, 3), "max": round(hi, 3), "n": int(n)}
            )
        out["series"] = [{"sensor": k, "points": v} for k, v in series.items()]
        return out

    def metrics(self) -> list[str]:
        vis_sql, vis_args = self._visible()
        rows = self.conn.execute(
            f"SELECT DISTINCT metric FROM readings WHERE {vis_sql} ORDER BY metric", vis_args
        ).fetchall()
        return [r[0] for r in rows]

    def sensor_status(self) -> dict:
        dev_sql, dev_args = self._dev()
        rows = self.conn.execute(
            f"SELECT device_id, last_seen FROM devices WHERE {dev_sql} ORDER BY device_id", dev_args
        ).fetchall()
        g = self.s.publish_granularity_s
        devices = []
        newest = None
        for dev, last_seen in rows:
            online = (self.now - last_seen) <= self.s.online_window_s
            coarse = last_seen - (last_seen % g) if g > 0 else last_seen
            newest = coarse if newest is None else max(newest, coarse)
            devices.append(
                {
                    "device_id": dev,
                    "online": online,
                    "last_heard": iso_local(coarse, self.s.tz_name),
                    "test": dev in self.s.test_devices,
                }
            )
        return {
            "online": any(d["online"] for d in devices),
            # Rounded down to the publish boundary: heartbeats can coincide
            # with door openings, so the exact time is not published.
            "last_heard": iso_local(newest, self.s.tz_name) if newest is not None else None,
            "online_window_min": self.s.online_window_s // 60,
            "devices": devices,
        }

    def summary(self) -> dict:
        s, tzn = self.s, self.s.tz_name
        today = self.today
        yesterday = today - timedelta(days=1)
        mid_today = local_midnight(today, tzn)
        mid_yest = local_midnight(yesterday, tzn)
        into_today = max(0, min(self.cutoff, self.now) - mid_today)
        first = self.first_date()
        total = self._count()

        def window(days: int) -> dict:
            span = days * 86400
            end = min(self.cutoff, self.now)
            return {
                "count": self._count("ts >= ? AND ts < ?", [end - span, end]),
                "previous": self._count("ts >= ? AND ts < ?", [end - 2 * span, end - span]),
                # False until the counter has existed for the whole previous
                # window; the dashboard hides the comparison until then.
                "previous_complete": bool(first and local_midnight(first, tzn) <= end - 2 * span),
            }

        out: dict = {
            "tz": tzn,
            "device": self.device or "all",
            "server_time": self.now,
            "data_through": iso_local(min(self.cutoff, self.now), tzn),
            "publish_granularity_s": s.publish_granularity_s,
            "rev": f"{self.cutoff}.{total}",
            "has_data": total > 0,
            "today": {
                "date": today.isoformat(),
                "count": self._count("local_date = ?", [today.isoformat()]),
                "yesterday_same_time": self._count(
                    "ts >= ? AND ts < ?", [mid_yest, mid_yest + into_today]
                ),
            },
            "yesterday": {
                "date": yesterday.isoformat(),
                "count": self._count("local_date = ?", [yesterday.isoformat()]),
            },
            "last_7_days": window(7),
            "last_30_days": window(30),
            "all_time": {"count": total, "first_date": None, "days": 0, "avg_per_day": None},
            "busiest_hour": None,
            "busiest_weekday": None,
            "typical_open_s": None,
            "sensor": self.sensor_status(),
            "metrics": self.metrics(),
            "rules": {
                "min_open_ms": s.min_open_ms,
                "online_window_min": s.online_window_s // 60,
            },
        }
        if first is None:
            return out
        elapsed_days = max(1.0, (min(self.cutoff, self.now) - local_midnight(first, tzn)) / 86400)
        out["all_time"].update(
            {
                "first_date": first.isoformat(),
                "days": (today - first).days + 1,
                "avg_per_day": round(total / elapsed_days, 1),
            }
        )
        hm = self.heatmap(first.isoformat(), today.isoformat())
        hours = [h for h in hm["by_hour"] if h["avg"] is not None]
        if hours and total:
            best = max(hours, key=lambda h: h["avg"])
            out["busiest_hour"] = {"hour": best["hour"], "avg": best["avg"]}
        wdays = [w for w in hm["by_weekday"] if w["avg"] is not None]
        if wdays and any(w["total"] for w in wdays):
            best = max(wdays, key=lambda w: w["avg"])
            out["busiest_weekday"] = {"weekday": best["weekday"], "name": best["name"], "avg": best["avg"]}
        out["typical_open_s"] = self.durations(first.isoformat(), today.isoformat())["median_s"]
        return out

    # ---- CSV -----------------------------------------------------------------

    def export_rows(self, grain: str, start: str | None, end: str | None) -> list[list]:
        if grain not in ("hour", "day"):
            raise QueryError("grain must be hour or day")
        if start is None and end is None:
            # No range given: the whole history, as far back as the grain allows.
            limit = self.s.max_hourly_days if grain == "hour" else self.s.max_daily_days
            oldest = self.today - timedelta(days=limit - 1)
            start = max(self.first_date() or self.today, oldest).isoformat()
        if grain == "day":
            data = self.daily(start, end)
            rows: list[list] = [
                ["date", "weekday", "openings", "avg_open_seconds", "held_open", "complete_day"]
            ]
            for d in data["days"]:
                rows.append(
                    [
                        d["date"],
                        WEEKDAYS[d["weekday"]],
                        d["count"],
                        "" if d["avg_open_s"] is None else d["avg_open_s"],
                        d["held_open"],
                        "yes" if d["complete"] else "no",
                    ]
                )
            return rows
        if grain == "hour":
            data = self.hourly(start, end)
            rows = [["date", "hour", "hour_start_local", "openings"]]
            for h in data["hours"]:
                rows.append([h["date"], h["hour"], h["t"], h["count"]])
            return rows
        raise QueryError("grain must be hour or day")
