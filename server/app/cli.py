"""Small operator commands, run inside the container.

    docker exec hollygrove-fridge python -m app.cli devices
    docker exec hollygrove-fridge python -m app.cli counts
    docker exec hollygrove-fridge python -m app.cli backup /data/backup/fridge-YYYYMMDD.db
    docker exec hollygrove-fridge python -m app.cli relocalize
    docker exec hollygrove-fridge python -m app.cli genkey

These read the private tables directly (full device status, raw row counts),
which the public API deliberately does not expose.
"""

from __future__ import annotations

import secrets
import sqlite3
import sys
import time

from . import db
from .config import load_settings
from .timeutil import iso_local, local_parts


def cmd_devices(s) -> int:
    now = int(time.time())
    with db.session(s.db_path) as conn:
        rows = conn.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
    if not rows:
        print("no device has reported yet")
        return 0
    for r in rows:
        age = now - r["last_seen"]
        flag = "TEST" if r["device_id"] in s.test_devices else "public"
        state = "online" if age <= s.online_window_s else "OFFLINE"
        print(f"{r['device_id']} [{flag}] {state}, last heard {age // 60} min ago "
              f"({iso_local(r['last_seen'], s.tz_name)})")
        print(f"  posts={r['post_count']} fw={r['fw']} uplink={r['uplink']} rssi={r['rssi']} "
              f"heap={r['heap']} uptime_s={r['uptime_s']} door_total={r['door_total']} "
              f"door_open={r['door_open']} queue={r['queue']} dropped={r['dropped']} "
              f"reset_reason={r['reset_reason']}")
    return 0


def cmd_counts(s) -> int:
    with db.session(s.db_path) as conn:
        for dev, n, short, held, approx in conn.execute(
            "SELECT device_id, COUNT(*), "
            "SUM(CASE WHEN dur_ms >= 0 AND dur_ms < ? THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN dur_ms = -1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN time_quality != 'device' THEN 1 ELSE 0 END) "
            "FROM events GROUP BY device_id ORDER BY device_id",
            (s.min_open_ms,),
        ):
            print(f"{dev}: {n} events stored, {short} shorter than {s.min_open_ms} ms (not counted), "
                  f"{held} held open, {approx} with approximate time")
        for dev, metric, n in conn.execute(
            "SELECT device_id, metric, COUNT(*) FROM readings GROUP BY device_id, metric ORDER BY 1, 2"
        ):
            print(f"{dev}: {n} readings of {metric}")
    return 0


def cmd_backup(s, dest: str) -> int:
    """Consistent copy of the live database (safe while the service runs)."""
    src = sqlite3.connect(s.db_path)
    out = sqlite3.connect(dest)
    try:
        src.backup(out)
        check = out.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        out.close()
        src.close()
    print(f"backup written to {dest}; integrity_check: {check}")
    return 0 if check == "ok" else 1


def cmd_relocalize(s) -> int:
    """Recompute local_date/local_hour (only needed if FRIDGE_TZ is changed)."""
    with db.write_tx(s.db_path) as conn:
        rows = conn.execute("SELECT id, ts FROM events").fetchall()
        for r in rows:
            d, h = local_parts(r["ts"], s.tz_name)
            conn.execute("UPDATE events SET local_date=?, local_hour=? WHERE id=?", (d, h, r["id"]))
        rrows = conn.execute("SELECT id, ts FROM readings").fetchall()
        for r in rrows:
            d, _ = local_parts(r["ts"], s.tz_name)
            conn.execute("UPDATE readings SET local_date=? WHERE id=?", (d, r["id"]))
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('tz', ?)", (s.tz_name,))
    print(f"recomputed local time for {len(rows)} events and {len(rrows)} readings in {s.tz_name}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 1 and argv[0] == "genkey":
        print(secrets.token_urlsafe(32))
        return 0
    s = load_settings()
    if argv[:1] == ["devices"]:
        return cmd_devices(s)
    if argv[:1] == ["counts"]:
        return cmd_counts(s)
    if argv[:1] == ["backup"] and len(argv) == 2:
        return cmd_backup(s, argv[1])
    if argv[:1] == ["relocalize"]:
        return cmd_relocalize(s)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
