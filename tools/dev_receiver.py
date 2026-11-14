#!/usr/bin/env python3
"""Throwaway local ingest receiver for bench-testing the fridge firmware.

It implements the same contract as the real server
(POST /fridge/api/v1/ingest), over plain HTTP, so a board built with the
esp32s3_dev environment - or tools/fake_device.py - can be tested end to end
without the production server. Nothing is stored on disk.

Standard library only (Python 3.9+).

Examples:
    python tools/dev_receiver.py
    python tools/dev_receiver.py --key my-test-key        # enforce the key (else any key passes)
    python tools/dev_receiver.py --fail-first 3 --fail-status 503   # test retry/backoff
    python tools/dev_receiver.py --always-status 400      # test "drop malformed batch"
"""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INGEST_PATH = "/fridge/api/v1/ingest"
MAX_EVENTS = 20


def validate(body):
    """Return an error string if the payload breaks the contract, else None."""
    if not isinstance(body, dict):
        return "body is not a JSON object"
    need = {
        "device_id": str, "fw": str, "boot_id": int, "uplink": str, "sent_at": int,
        "uptime_s": int, "door_total": int, "events": list, "readings": list, "status": dict,
    }
    for key, typ in need.items():
        if key not in body:
            return "missing field %s" % key
        if not isinstance(body[key], typ) or isinstance(body[key], bool):
            return "field %s has the wrong type" % key
    if len(body["events"]) > MAX_EVENTS:
        return "more than %d events" % MAX_EVENTS
    for ev in body["events"]:
        if not isinstance(ev, dict):
            return "event is not an object"
        for key in ("boot", "n", "t", "dur_ms"):
            if not isinstance(ev.get(key), int) or isinstance(ev.get(key), bool):
                return "event field %s missing or not an integer" % key
        if ev["n"] < 1 or ev["dur_ms"] < -1 or ev["t"] < 0:
            return "event value out of range"
        if "age_s" in ev and ev["age_s"] is not None and not isinstance(ev["age_s"], int):
            return "event age_s is not an integer"
    for rd in body["readings"]:
        if not isinstance(rd, dict):
            return "reading is not an object"
        if not isinstance(rd.get("sensor"), str) or not isinstance(rd.get("metric"), str):
            return "reading sensor/metric missing"
        if not isinstance(rd.get("value"), (int, float)) or isinstance(rd.get("value"), bool):
            return "reading value is not a number"
        if not isinstance(rd.get("t"), int):
            return "reading t missing"
    return None


class State:
    def __init__(self, args):
        self.args = args
        self.seen = set()          # (device_id, boot, n)
        self.requests = 0
        self.events_accepted = 0
        self.readings = 0


class Handler(BaseHTTPRequestHandler):
    server_version = "fridge-dev-receiver/1.0"
    state = None  # set in main()

    def log_message(self, fmt, *args):  # silence the default per-request line
        pass

    def reply(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        st = self.state
        args = st.args
        st.requests += 1
        stamp = time.strftime("%H:%M:%S")
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        who = "%s ua=%r" % (self.client_address[0], self.headers.get("User-Agent"))

        if self.path != INGEST_PATH:
            print("%s  404  %s  path %s" % (stamp, who, self.path), flush=True)
            return self.reply(404, {"ok": False, "error": "not found"})

        if args.always_status:
            print("%s  %d  %s  (forced by --always-status, %d bytes)" % (stamp, args.always_status, who, len(raw)), flush=True)
            return self.reply(args.always_status, {"ok": False, "error": "forced"})
        if st.requests <= args.fail_first:
            print("%s  %d  %s  (forced failure %d of %d)" % (stamp, args.fail_status, who, st.requests, args.fail_first), flush=True)
            return self.reply(args.fail_status, {"ok": False, "error": "forced"})

        if args.key is not None and self.headers.get("X-Device-Key") != args.key:
            print("%s  401  %s  bad or missing X-Device-Key" % (stamp, who), flush=True)
            return self.reply(401, {"ok": False, "error": "bad device key"})
        if self.headers.get("X-Device-Key") is None:
            print("%s  401  %s  no X-Device-Key header" % (stamp, who), flush=True)
            return self.reply(401, {"ok": False, "error": "missing device key"})

        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            print("%s  400  %s  invalid JSON: %s" % (stamp, who, exc), flush=True)
            return self.reply(400, {"ok": False, "error": "invalid json"})
        err = validate(body)
        if err:
            print("%s  400  %s  %s" % (stamp, who, err), flush=True)
            return self.reply(400, {"ok": False, "error": err})

        accepted = duplicates = 0
        for ev in body["events"]:
            key = (body["device_id"], ev["boot"], ev["n"])
            if key in st.seen:
                duplicates += 1
            else:
                st.seen.add(key)
                accepted += 1
        st.events_accepted += accepted
        st.readings += len(body["readings"])
        s = body["status"]
        print("%s  200  %s  device=%s fw=%s boot=%s uplink=%s sent_at=%s uptime=%ss total=%s | "
              "events=%d (new %d, dup %d) readings=%d | rssi=%s heap=%s door_open=%s queue=%s dropped=%s reset=%s"
              % (stamp, who, body["device_id"], body["fw"], body["boot_id"], body["uplink"],
                 body["sent_at"], body["uptime_s"], body["door_total"], len(body["events"]),
                 accepted, duplicates, len(body["readings"]), s.get("rssi"), s.get("heap"),
                 s.get("door_open"), s.get("queue"), s.get("dropped"), s.get("reset_reason")), flush=True)
        if args.verbose:
            for ev in body["events"]:
                print("          event   %s" % json.dumps(ev), flush=True)
            for rd in body["readings"]:
                print("          reading %s" % json.dumps(rd), flush=True)
        self.reply(200, {"ok": True, "accepted": accepted, "duplicates": duplicates,
                         "server_time": int(time.time())})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="0.0.0.0", help="address to listen on (default: all interfaces)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--key", default=None, help="required X-Device-Key value (default: accept any non-empty key)")
    ap.add_argument("--fail-first", type=int, default=0, metavar="N", help="answer the first N requests with --fail-status")
    ap.add_argument("--fail-status", type=int, default=503)
    ap.add_argument("--always-status", type=int, default=0, metavar="CODE", help="answer every ingest request with this status")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every event and reading")
    args = ap.parse_args()

    Handler.state = State(args)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("dev receiver listening on http://%s:%d%s  (Ctrl+C to stop)" % (args.host, args.port, INGEST_PATH), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    st = Handler.state
    print("\n%d request(s), %d unique event(s), %d reading(s)" % (st.requests, st.events_accepted, st.readings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
