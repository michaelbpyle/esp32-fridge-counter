#!/usr/bin/env python3
"""Fake fridge door counter: exercises an ingest server end to end.

Sends the same JSON the firmware sends to
    POST <base-url>/fridge/api/v1/ingest
with headers Content-Type, X-Device-Key and User-Agent.

Default scenario (in this order):
  1. boot heartbeat (no events) with BMP280 readings
  2. --count door events in batches of at most 20, with readings
  3. the last batch again (duplicate retransmit; the server must report duplicates)
  4. a held-open event (dur_ms = -1)
  5. clock edge cases: an event with t = 0 + age_s, and an event from an
     earlier boot with t = 0 and no age_s
  6. a closing heartbeat

--backfill-days N instead generates a plausible history of the last N days
(door activity following a daily rhythm, several boots, BMP280 temperature
and pressure every 15 minutes) and uploads it.

Standard library only (Python 3.9+).

Examples:
    python tools/fake_device.py --base-url http://127.0.0.1:8080 --key test-key
    python tools/fake_device.py --base-url https://hollygrovenola.org --key SECRET --device-id fridge-test --count 45
    python tools/fake_device.py --base-url http://127.0.0.1:8080 --key test-key --backfill-days 14
    python tools/fake_device.py --dry-run --count 3        # print the payloads, send nothing
"""
import argparse
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request

INGEST_PATH = "/fridge/api/v1/ingest"
FW = "1.0.0"
MAX_EVENTS = 20
MAX_READINGS = 40


class Client:
    def __init__(self, args):
        self.args = args
        self.url = args.base_url.rstrip("/") + INGEST_PATH
        self.posts = 0
        self.failures = 0
        self.accepted = 0
        self.duplicates = 0

    def post(self, body, label, expect_status=200):
        """Send one payload. Returns the parsed JSON reply (or None)."""
        data = json.dumps(body, separators=(",", ":")).encode()
        self.posts += 1
        if self.args.dry_run:
            print("--- %s (dry run, %d bytes)\n%s" % (label, len(data), json.dumps(body, indent=2)))
            return {"ok": True, "accepted": len(body["events"]), "duplicates": 0, "server_time": int(time.time())}
        req = urllib.request.Request(self.url, data=data, method="POST", headers={
            "Content-Type": "application/json",
            "X-Device-Key": self.args.key,
            "User-Agent": "hollygrove-fridge/%s (fake_device.py)" % FW,
        })
        status, text = None, ""
        try:
            with urllib.request.urlopen(req, timeout=self.args.timeout) as resp:
                status, text = resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            status, text = exc.code, exc.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as exc:
            print("FAIL  %-34s no response: %s" % (label, exc))
            self.failures += 1
            return None
        reply = None
        try:
            reply = json.loads(text)
        except ValueError:
            pass
        ok = status == expect_status and (status != 200 or (isinstance(reply, dict) and reply.get("ok") is True))
        print("%s  %-34s HTTP %s  events=%d readings=%d  reply=%s" % (
            "ok  " if ok else "FAIL", label, status, len(body["events"]), len(body["readings"]),
            text.strip()[:160]))
        if not ok:
            self.failures += 1
        if isinstance(reply, dict) and status == 200:
            self.accepted += int(reply.get("accepted") or 0)
            self.duplicates += int(reply.get("duplicates") or 0)
        if self.args.delay:
            time.sleep(self.args.delay)
        return reply if status == 200 else None


def payload(args, boot_id, uptime_s, door_total, events, readings, now=None, door_open=False,
            queue=0, reset_reason="poweron", sent_at=None):
    now = int(time.time()) if now is None else now
    return {
        "device_id": args.device_id,
        "fw": FW,
        "boot_id": boot_id,
        "uplink": "wifi",
        "sent_at": now if sent_at is None else sent_at,
        "uptime_s": uptime_s,
        "door_total": door_total,
        "events": events,
        "readings": readings,
        "status": {
            "rssi": random.randint(-72, -48),
            "heap": random.randint(205000, 245000),
            "door_open": door_open,
            "queue": queue,
            "dropped": 0,
            "reset_reason": reset_reason,
        },
    }


def new_boot_id():
    return random.randint(1, 0xFFFFFFFF)


def weather(t):
    """Plausible New Orleans porch weather for epoch second t: (temp_c, pressure_hpa)."""
    day = (t % 86400) / 86400.0
    season = math.cos((time.gmtime(t).tm_yday - 200) / 365.0 * 2 * math.pi)  # warmest in mid-July
    temp = 21 + 8 * season + 4.5 * math.sin((day - 0.42) * 2 * math.pi) + random.gauss(0, 0.3)
    pressure = 1016 + 4 * math.sin(t / 86400.0 / 3.1) + 1.2 * math.sin(day * 4 * math.pi) + random.gauss(0, 0.15)
    return round(temp, 2), round(pressure, 2)


def bmp280_readings(t, now):
    temp, pressure = weather(t)
    age = max(0, now - t)
    return [
        {"t": t, "age_s": age, "sensor": "bmp280", "metric": "temp_c", "value": temp},
        {"t": t, "age_s": age, "sensor": "bmp280", "metric": "pressure_hpa", "value": pressure},
    ]


def door_duration_ms():
    """Most openings are a quick grab; a few are long restocking sessions."""
    if random.random() < 0.08:
        return random.randint(45000, 240000)
    return int(min(60000, max(1200, random.lognormvariate(8.9, 0.6))))


def run_scenario(args, client):
    boot = new_boot_id()
    start = int(time.time())
    uptime = 12
    total = random.randint(100, 5000)
    n = 0

    # 1. boot heartbeat
    client.post(payload(args, boot, uptime, total, [], bmp280_readings(start - 5, start)), "boot heartbeat")

    # 2. door events in batches
    events = []
    t = start - args.count * 40
    for _ in range(args.count):
        n += 1
        total += 1
        t += random.randint(15, 60)
        events.append({"boot": boot, "n": n, "t": t, "age_s": 0, "dur_ms": door_duration_ms()})
    last_batch = None
    for i in range(0, len(events), MAX_EVENTS):
        now = int(time.time())
        batch = [dict(e, age_s=max(0, now - e["t"])) for e in events[i:i + MAX_EVENTS]]
        uptime += 30
        remaining = max(0, len(events) - i - len(batch))
        last_batch = payload(args, boot, uptime, total, batch, bmp280_readings(now - 60, now), queue=remaining)
        reply = client.post(last_batch, "event batch %d" % (i // MAX_EVENTS + 1))
        if reply and reply.get("accepted") != len(batch) and not args.dry_run:
            print("      note: expected accepted=%d (were these already uploaded?)" % len(batch))

    # 3. duplicate retransmit of the last batch
    if last_batch:
        reply = client.post(last_batch, "duplicate retransmit")
        if reply is not None and not args.dry_run and reply.get("duplicates") != len(last_batch["events"]):
            print("FAIL  server did not report %d duplicates (got %r)" % (len(last_batch["events"]), reply.get("duplicates")))
            client.failures += 1

    # 4. held-open event: door opened 11 minutes ago and is still open
    now = int(time.time())
    n += 1
    total += 1
    uptime += 700
    held = {"boot": boot, "n": n, "t": now - 660, "age_s": 660, "dur_ms": -1}
    client.post(payload(args, boot, uptime, total, [held], [], door_open=True), "held-open event")

    # 5. clock edge cases
    n += 1
    total += 1
    no_clock = {"boot": boot, "n": n, "t": 0, "age_s": 42, "dur_ms": 5300}
    client.post(payload(args, boot, uptime + 50, total, [no_clock], [], sent_at=0), "event without clock (age_s)")
    old_boot = {"boot": new_boot_id(), "n": 7, "t": 0, "dur_ms": 4100}
    client.post(payload(args, boot, uptime + 60, total, [old_boot], []), "old-boot event, no t, no age_s")

    # 6. closing heartbeat
    now = int(time.time())
    client.post(payload(args, boot, uptime + 900, total, [], bmp280_readings(now - 300, now) + bmp280_readings(now, now)),
                "closing heartbeat")


def hourly_rate(hour_local):
    """Relative door activity by local hour: quiet at night, busy late morning and after work."""
    profile = [0.2, 0.1, 0.1, 0.1, 0.1, 0.3, 0.8, 1.5, 2.2, 2.6, 3.0, 3.4,
               3.6, 3.0, 2.6, 2.8, 3.4, 4.0, 3.6, 2.6, 1.8, 1.2, 0.7, 0.4]
    return profile[hour_local % 24]


def run_backfill(args, client):
    now = int(time.time())
    start = now - args.backfill_days * 86400
    tz_offset = -6 * 3600  # America/Chicago standard time, close enough for a daily rhythm

    # Build the history: events and readings, split over several boots.
    items = []  # (t, kind, data)
    boot = new_boot_id()
    boot_start = start
    n = 0
    t = start
    next_reboot = start + random.randint(2, 6) * 86400
    while t < now:
        if t >= next_reboot:
            boot, boot_start, n = new_boot_id(), t, 0
            next_reboot = t + random.randint(2, 6) * 86400
        hour = int(((t + tz_offset) % 86400) // 3600)
        weekday = time.gmtime(t + tz_offset).tm_wday
        rate = hourly_rate(hour) * (1.25 if weekday >= 5 else 1.0) * args.opens_per_day / 44.1
        # Poisson arrivals within this 15-minute slot
        slot = 900
        expected = rate * slot / 3600.0
        count = 0
        acc = math.exp(-expected)
        r = random.random()
        cum = acc
        while r > cum and count < 50:
            count += 1
            acc *= expected / count
            cum += acc
        for _ in range(count):
            et = t + random.randint(0, slot - 1)
            if et >= now:
                continue
            n += 1
            dur = -1 if random.random() < 0.004 else door_duration_ms()
            items.append((et, "event", {"boot": boot, "n": n, "t": et, "dur_ms": dur}, boot, boot_start))
        temp, pressure = weather(t)
        items.append((t, "reading", {"t": t, "sensor": "bmp280", "metric": "temp_c", "value": temp}, boot, boot_start))
        items.append((t, "reading", {"t": t, "sensor": "bmp280", "metric": "pressure_hpa", "value": pressure}, boot, boot_start))
        t += slot
    items.sort(key=lambda x: x[0])
    n_events = sum(1 for i in items if i[1] == "event")
    n_readings = len(items) - n_events
    print("backfill: %d day(s), %d door events, %d readings" % (args.backfill_days, n_events, n_readings))

    # Upload in contract-sized POSTs, as a device catching up would.
    total = args.start_total
    events, readings = [], []
    cur_boot, cur_boot_start, last_t = None, start, start

    def flush():
        nonlocal events, readings
        if not events and not readings:
            return
        send_now = int(time.time())
        for e in events:
            e["age_s"] = max(0, send_now - e["t"])
        for r in readings:
            r["age_s"] = max(0, send_now - r["t"])
        body = payload(args, cur_boot, max(1, last_t - cur_boot_start), total, events, readings, now=send_now,
                       reset_reason="poweron" if cur_boot_start == start else "task_wdt")
        client.post(body, "backfill POST %d" % (client.posts + 1))
        events, readings = [], []

    for (t, kind, data, boot, boot_start) in items:
        if cur_boot is None:
            cur_boot, cur_boot_start = boot, boot_start
        if boot != cur_boot:
            flush()
            cur_boot, cur_boot_start = boot, boot_start
        last_t = t
        if kind == "event":
            total += 1
            events.append(data)
        else:
            readings.append(data)
        if len(events) >= MAX_EVENTS or len(readings) >= MAX_READINGS:
            flush()
    flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://127.0.0.1:8080", help="server base URL without the /fridge/... path")
    ap.add_argument("--device-id", default="fridge-test")
    ap.add_argument("--key", default="test-key", help="value for the X-Device-Key header")
    ap.add_argument("--count", type=int, default=25, help="door events in the default scenario (default 25)")
    ap.add_argument("--backfill-days", type=int, default=0, metavar="N", help="upload N days of generated history instead")
    ap.add_argument("--opens-per-day", type=float, default=140.0, help="average door openings per day for --backfill-days")
    ap.add_argument("--start-total", type=int, default=0, help="door_total at the start of the backfill")
    ap.add_argument("--seed", type=int, default=None, help="random seed for repeatable data")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds to wait between POSTs")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--dry-run", action="store_true", help="print payloads instead of sending them")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    client = Client(args)
    if not args.dry_run:
        print("target: %s  device_id: %s" % (client.url, args.device_id))
    if args.backfill_days > 0:
        run_backfill(args, client)
    else:
        run_scenario(args, client)
    print("\n%d POST(s), %d failure(s); server accepted %d event(s), reported %d duplicate(s)"
          % (client.posts, client.failures, client.accepted, client.duplicates))
    return 1 if client.failures else 0


if __name__ == "__main__":
    sys.exit(main())
