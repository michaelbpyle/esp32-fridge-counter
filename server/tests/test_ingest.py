from __future__ import annotations

import json

from conftest import API, BENCH_KEY, KEY, chi


def test_contract_example_is_accepted(env):
    now = env.clock.now
    body = {
        "device_id": "fridge-01", "fw": "1.0.0", "boot_id": 2893746123, "uplink": "wifi",
        "sent_at": now, "uptime_s": 1234, "door_total": 42,
        "events": [{"boot": 2893746123, "n": 17, "t": now - 10, "age_s": 10, "dur_ms": 8200}],
        "readings": [{"t": now - 100, "age_s": 100, "sensor": "bmp280", "metric": "temp_c", "value": 23.4}],
        "status": {"rssi": -61, "heap": 123456, "door_open": False, "queue": 0, "dropped": 0,
                   "reset_reason": "poweron"},
    }
    r = env.post(body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True and data["accepted"] == 1 and data["duplicates"] == 0
    assert data["server_time"] == now
    assert env.rows("SELECT device_id, boot, n, ts, time_quality, dur_ms FROM events") == [
        ("fridge-01", 2893746123, 17, now - 10, "device", 8200)
    ]
    assert env.rows("SELECT sensor, metric, value FROM readings") == [("bmp280", "temp_c", 23.4)]
    dev = env.rows("SELECT fw, uplink, rssi, heap, door_open, door_total, reset_reason FROM devices")
    assert dev == [("1.0.0", "wifi", -61, 123456, 0, 42, "poweron")]


def test_duplicates_are_ignored_and_counted(env):
    now = env.clock.now
    evs = [env.ev(now - 60), env.ev(now - 30)]
    assert env.post(env.body(events=evs)).json()["accepted"] == 2
    extra = env.ev(now - 5)
    data = env.post(env.body(events=evs + [extra])).json()  # a retry plus one new event
    assert (data["accepted"], data["duplicates"]) == (1, 2)
    assert env.rows("SELECT COUNT(*) FROM events") == [(3,)]


def test_same_n_from_a_different_boot_is_a_new_event(env):
    now = env.clock.now
    a = {"boot": 1, "n": 5, "t": now - 50, "age_s": 50, "dur_ms": 3000}
    b = {"boot": 2, "n": 5, "t": now - 40, "age_s": 40, "dur_ms": 3000}
    assert env.post(env.body(events=[a, b])).json()["accepted"] == 2


def test_no_clock_uses_receive_time_minus_age(env):
    now = env.clock.now
    env.post(env.body(events=[{"boot": 9, "n": 1, "t": 0, "age_s": 90, "dur_ms": 4000}]))
    assert env.rows("SELECT ts, time_quality FROM events") == [(now - 90, "approx")]


def test_no_clock_and_no_age_uses_receive_time(env):
    now = env.clock.now
    env.post(env.body(events=[{"boot": 9, "n": 1, "t": 0, "dur_ms": 4000}]))
    assert env.rows("SELECT ts, time_quality FROM events") == [(now, "received")]


def test_missing_t_field_is_treated_as_no_clock(env):
    now = env.clock.now
    env.post(env.body(events=[{"boot": 9, "n": 1, "age_s": 30, "dur_ms": 4000}]))
    assert env.rows("SELECT ts, time_quality FROM events") == [(now - 30, "approx")]


def test_future_timestamp_is_clamped_and_marked(env):
    now = env.clock.now
    r = env.post(env.body(events=[{"boot": 9, "n": 1, "t": now + 10 * 365 * 86400, "age_s": 20, "dur_ms": 4000}]))
    assert r.status_code == 200
    assert env.rows("SELECT ts, time_quality FROM events") == [(now - 20, "clamped")]


def test_prehistoric_timestamp_is_treated_as_no_clock(env):
    now = env.clock.now
    env.post(env.body(events=[{"boot": 9, "n": 1, "t": 12345, "age_s": 15, "dur_ms": 4000}]))
    assert env.rows("SELECT ts, time_quality FROM events") == [(now - 15, "approx")]


def test_held_open_is_stored_and_counts_once(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    env.post(env.body(events=[env.ev(chi(2026, 11, 14, 9, 5), dur_ms=-1)]))
    assert env.rows("SELECT dur_ms FROM events") == [(-1,)]
    env.backdate()
    day = env.get("daily", start="2026-11-14", end="2026-11-14").json()["days"][0]
    assert day["count"] == 1 and day["held_open"] == 1 and day["avg_open_s"] is None


def test_heartbeat_with_no_events_updates_last_seen(env):
    r = env.post(env.body())
    assert r.status_code == 200 and r.json()["accepted"] == 0
    first = env.rows("SELECT last_seen, post_count FROM devices")[0]
    env.clock.now += 600
    env.post(env.body(events=None, readings=None))
    second = env.rows("SELECT last_seen, post_count FROM devices")[0]
    assert second == (first[0] + 600, 2)


def test_missing_or_bad_key_is_401(env):
    body = env.body(events=[env.ev(env.clock.now - 5)])
    assert env.post(body, key=None).status_code == 401
    assert env.post(body, key="").status_code == 401
    assert env.post(body, key="wrong").status_code == 401
    assert env.post(body, key=KEY + "x").status_code == 401
    assert env.rows("SELECT COUNT(*) FROM events") == [(0,)]


def test_key_of_another_device_is_401(env):
    body = env.body(events=[env.ev(env.clock.now - 5)], device="fridge-01")
    r = env.post(body, key=BENCH_KEY)
    assert r.status_code == 401
    assert env.rows("SELECT COUNT(*) FROM events") == [(0,)]


def test_malformed_bodies_are_400_with_a_reason(env):
    hdr = {"Content-Type": "application/json", "X-Device-Key": KEY}
    cases = [
        b"{not json",
        b"",
        b"[1,2,3]",
        b'"just a string"',
        json.dumps({"events": []}).encode(),                                   # no device_id
        json.dumps({"device_id": "bad id!", "events": []}).encode(),
        json.dumps({"device_id": "fridge-01", "events": "nope"}).encode(),
        json.dumps({"device_id": "fridge-01", "readings": {"a": 1}}).encode(),
        json.dumps({"device_id": "fridge-01", "status": [1]}).encode(),
        b"\xff\xfe\x00",
    ]
    for raw in cases:
        r = env.client.post(f"{API}/ingest", content=raw, headers=hdr)
        assert r.status_code == 400, raw
        assert r.json()["ok"] is False and r.json()["error"]


def test_too_many_events_is_400(env):
    evs = [env.ev(env.clock.now - 5) for _ in range(201)]
    r = env.post(env.body(events=evs))
    assert r.status_code == 400 and "too many events" in r.json()["error"]
    assert env.post(env.body(events=evs[:200])).status_code == 200


def test_bad_items_are_skipped_not_fatal(env):
    now = env.clock.now
    evs = [
        env.ev(now - 5),
        "garbage",
        {"boot": 1, "n": "seven", "t": now, "dur_ms": 100},
        {"boot": 1, "n": 2, "t": now, "dur_ms": -7},
        {"boot": 1, "n": True, "t": now},
        {"boot": 1, "n": 3, "t": "yesterday", "age_s": "soon", "dur_ms": 2500},  # bad time -> receive time
    ]
    rds = [
        {"t": now, "sensor": "bmp280", "metric": "temp_c", "value": 21.5},
        {"t": now, "sensor": "bmp280", "metric": "temp_c", "value": "hot"},
        {"t": now, "sensor": "BAD NAME", "metric": "temp_c", "value": 1},
        5,
    ]
    r = env.post(env.body(events=evs, readings=rds))
    assert r.status_code == 200
    data = r.json()
    assert (data["accepted"], data["rejected"], data["readings_accepted"]) == (2, 4, 1)
    assert env.rows("SELECT time_quality FROM events WHERE n = 3") == [("received",)]


def test_oversize_body_is_413(env):
    big = env.body(events=[], padding="x" * 70_000)
    r = env.post(big)
    assert r.status_code == 413
    # Also when the size is not declared up front (chunked upload).
    def chunks():
        yield b'{"device_id":"fridge-01","padding":"'
        for _ in range(80):
            yield b"x" * 1000
        yield b'"}'
    r = env.client.post(f"{API}/ingest", content=chunks(),
                        headers={"Content-Type": "application/json", "X-Device-Key": KEY})
    assert r.status_code == 413
    assert env.rows("SELECT COUNT(*) FROM devices") == [(0,)]


def test_ingest_rate_limit(make_env):
    env = make_env(ingest_per_min=5)
    codes = [env.post(env.body()).status_code for _ in range(7)]
    assert codes == [200] * 5 + [429] * 2
    env.clock.now += 61
    assert env.post(env.body()).status_code == 200


def test_repeated_bad_keys_are_throttled(make_env):
    env = make_env(auth_fail_per_min=3)
    codes = [env.post(env.body(), key="nope").status_code for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]


def test_get_on_ingest_is_not_allowed(env):
    assert env.client.get(f"{API}/ingest").status_code == 405


def test_keys_never_reach_the_logs(env, capsys):
    env.post(env.body(events=[env.ev(env.clock.now - 5)]))
    env.post(env.body(), key="a-wrong-key-value-123")
    env.post(env.body(device="fridge-01"), key=BENCH_KEY)
    out = capsys.readouterr()
    text = out.out + out.err
    assert "ingest" in text
    for secret in (KEY, BENCH_KEY, "a-wrong-key-value-123"):
        assert secret not in text


def test_readings_are_stored_generically(env):
    now = env.clock.now
    rds = [
        {"t": now - 60, "sensor": "hx711_1", "metric": "weight_g", "value": 1520.5},
        {"t": now - 60, "sensor": "hx711_2", "metric": "weight_g", "value": 980},
        {"t": now - 60, "sensor": "ds18b20", "metric": "fridge_temp_c", "value": 3.5},
        {"t": now - 60, "sensor": "newthing", "metric": "brand_new_metric", "value": 1},
    ]
    assert env.post(env.body(readings=rds)).json()["readings_accepted"] == 4
    assert env.post(env.body(readings=rds)).json()["readings_accepted"] == 0  # retry is deduplicated
