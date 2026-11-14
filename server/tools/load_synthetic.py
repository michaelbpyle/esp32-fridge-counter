"""Load a few weeks of made-up door openings into a LOCAL test server.

It talks to the service exactly as a device would (POST /fridge/api/v1/ingest
with X-Device-Key, at most 20 events per request), so it exercises the real
ingest path. Never point it at production: the data is fake.

    python tools/load_synthetic.py --url http://127.0.0.1:8765 --device fridge-01 \
        --key local-dev-key-fridge-01 --weeks 6 --readings --backdate-db ./data/fridge.db

--backdate-db: the public API only shows a row once the hour in which it was
RECEIVED is over. History loaded all at once would therefore stay hidden until
the top of the next hour. This option rewrites received_at = event time in the
given local database file so the history shows up at once. Test use only.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import sys
import time
import urllib.error
import urllib.request

HOUR_PROFILE = [0.1, 0.05, 0.05, 0.05, 0.1, 0.4, 1.2, 2.2, 2.6, 2.2, 2.0, 2.6,
                3.2, 2.6, 2.2, 2.4, 3.0, 3.8, 3.6, 2.6, 1.8, 1.0, 0.5, 0.2]
WEEKDAY_FACTOR = [0.9, 0.95, 1.0, 1.0, 1.1, 1.3, 1.15]  # Monday first


def post(url: str, key: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/fridge/api/v1/ingest", data=data, method="POST",
        headers={"Content-Type": "application/json", "X-Device-Key": key},
    )
    for _ in range(40):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:  # rate limited: wait and retry, as a device would
                time.sleep(float(exc.headers.get("Retry-After", "5")))
                continue
            raise SystemExit(f"server said {exc.code}: {exc.read().decode(errors='replace')}")
    raise SystemExit("gave up after repeated rate limiting")


def poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8765")
    ap.add_argument("--device", default="fridge-01")
    ap.add_argument("--key", required=True)
    ap.add_argument("--weeks", type=float, default=6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--readings", action="store_true", help="also send temperature, pressure, humidity, fridge temperature and shelf weights")
    ap.add_argument("--backdate-db", default="", help="local SQLite file to backdate (see above)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    now = int(time.time())
    start = now - int(args.weeks * 7 * 86400)
    boot = rng.randrange(1, 2**32)
    n = 0
    events = []
    hour = start - start % 3600
    while hour < now:
        lt = time.localtime(hour)
        growth = 0.65 + 0.45 * (hour - start) / max(1, now - start)
        lam = HOUR_PROFILE[lt.tm_hour] * WEEKDAY_FACTOR[lt.tm_wday] * growth
        for _ in range(poisson(rng, lam)):
            t = hour + rng.randrange(3600)
            if t >= now:
                continue
            roll = rng.random()
            if roll < 0.03:
                dur = rng.randrange(80, 900)          # bounce: stored but not counted
            elif roll < 0.04:
                dur = -1                              # held open past the device limit
            else:
                dur = int(min(280_000, max(1200, rng.lognormvariate(math.log(13_000), 0.8))))
            n += 1
            events.append({"boot": boot, "n": n, "t": t, "age_s": now - t, "dur_ms": dur})
        if rng.random() < 0.004:                      # an occasional reboot
            boot, n = rng.randrange(1, 2**32), 0
        hour += 3600
    events.sort(key=lambda e: e["t"])

    readings = []
    if args.readings:
        weight = [2400.0, 1800.0, 3100.0, 900.0]
        t = start
        while t < now:
            day_frac = (time.localtime(t).tm_hour + time.localtime(t).tm_min / 60) / 24
            season = 6 * math.sin((t - start) / 86400 / 6)
            temp = 19 + season + 5 * math.sin((day_frac - 0.4) * 2 * math.pi) + rng.gauss(0, 0.3)
            common = {"t": t, "age_s": now - t}
            readings += [
                {**common, "sensor": "bmp280", "metric": "temp_c", "value": round(temp, 2)},
                {**common, "sensor": "bmp280", "metric": "pressure_hpa", "value": round(1016 + 5 * math.sin(t / 250_000) + rng.gauss(0, 0.2), 2)},
                {**common, "sensor": "sht31", "metric": "humidity_pct", "value": round(min(99, max(30, 72 - 1.8 * (temp - 19) + rng.gauss(0, 1.5))), 1)},
                {**common, "sensor": "ds18b20", "metric": "fridge_temp_c", "value": round(3.2 + 0.8 * math.sin(t / 2400) + rng.gauss(0, 0.15), 2)},
            ]
            for i in range(4):
                weight[i] = max(100.0, weight[i] - rng.random() * 90)
                if weight[i] < 900 and rng.random() < 0.08:
                    weight[i] += rng.uniform(2500, 5000)  # a restock
                readings.append({**common, "sensor": f"hx711_{i + 1}", "metric": "weight_g", "value": round(weight[i], 1)})
            t += 1800

    def envelope(evs, rds):
        return {
            "device_id": args.device, "fw": "synthetic", "boot_id": boot, "uplink": "wifi",
            "sent_at": int(time.time()), "uptime_s": 1234, "door_total": n,
            "events": evs, "readings": rds,
            "status": {"rssi": -60, "heap": 150000, "door_open": False, "queue": 0, "dropped": 0, "reset_reason": "poweron"},
        }

    accepted = dupes = r_acc = posts = 0
    for i in range(0, len(events), 20):
        res = post(args.url, args.key, envelope(events[i:i + 20], []))
        accepted += res["accepted"]
        dupes += res["duplicates"]
        posts += 1
    for i in range(0, len(readings), 400):
        res = post(args.url, args.key, envelope([], readings[i:i + 400]))
        r_acc += res["readings_accepted"]
        posts += 1
    post(args.url, args.key, envelope([], []))  # final heartbeat
    print(f"sent {len(events)} events in {posts + 1} posts: accepted={accepted} duplicates={dupes} readings_accepted={r_acc}")

    if args.backdate_db:
        conn = sqlite3.connect(args.backdate_db)
        conn.execute("UPDATE events SET received_at = ts WHERE device_id = ?", (args.device,))
        conn.execute("UPDATE readings SET received_at = ts WHERE device_id = ?", (args.device,))
        conn.commit()
        conn.close()
        print(f"backdated received_at in {args.backdate_db} (test use only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
