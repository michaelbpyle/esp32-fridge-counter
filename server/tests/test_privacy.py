"""The public API must never reveal when an individual door opening happened.

Only aggregates bucketed to the hour or coarser may leave the service, and the
numbers may only change on a publish boundary (the top of the hour), so that
polling the API cannot be used to time an opening either.
"""

from __future__ import annotations

import re

from conftest import chi

ISO_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2}):(\d{2})[+-]\d{2}:\d{2}$")

ENDPOINTS = [
    ("summary", {}),
    ("hourly", {"start": "2026-11-12", "end": "2026-11-14"}),
    ("daily", {"start": "2026-11-01", "end": "2026-11-14"}),
    ("heatmap", {"start": "2026-11-01", "end": "2026-11-14"}),
    ("durations", {"start": "2026-11-01", "end": "2026-11-14"}),
    ("readings", {"metric": "temp_c", "start": "2026-11-12", "end": "2026-11-14", "bucket": "hour"}),
    ("readings", {"metric": "temp_c", "start": "2026-11-12", "end": "2026-11-14", "bucket": "day"}),
]


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, node


def seed(env):
    env.clock.now = chi(2026, 11, 14, 15, 20, 0)
    # Awkward, recognisable seconds so a leaked timestamp cannot hide.
    times = [
        chi(2026, 11, 12, 7, 13, 37), chi(2026, 11, 12, 18, 41, 9), chi(2026, 11, 13, 6, 2, 51),
        chi(2026, 11, 13, 12, 34, 56), chi(2026, 11, 14, 9, 17, 23), chi(2026, 11, 14, 14, 59, 59),
    ]
    env.add(times)
    env.post(env.body(readings=[
        {"t": chi(2026, 11, 13, 12, 34, 56), "sensor": "bmp280", "metric": "temp_c", "value": 21.25},
    ]))
    env.backdate()
    return times


def test_no_endpoint_exposes_an_event_timestamp(env):
    times = seed(env)
    secret_epochs = set(times)
    for name, params in ENDPOINTS:
        r = env.get(name, **params)
        assert r.status_code == 200, (name, r.text)
        for path, value in walk(r.json()):
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                assert value not in secret_epochs, f"{name}{path} leaks an event epoch"
                # Any epoch-sized number must be the server clock, nothing else.
                if value > 1_000_000_000:
                    assert path == ".server_time", f"{name}{path} is an unexpected epoch"
            elif isinstance(value, str):
                m = ISO_DT.match(value)
                if m:
                    assert (m.group(2), m.group(3)) == ("00", "00"), (
                        f"{name}{path} = {value} is finer than one hour"
                    )
                # No other string may smuggle a clock time.
                elif re.search(r"\d{2}:\d{2}", value):
                    raise AssertionError(f"{name}{path} = {value!r} looks like a time of day")


def test_csv_exports_are_hour_or_day_only(env):
    seed(env)
    hour_csv = env.get("export.csv", grain="hour", start="2026-11-12", end="2026-11-14").text
    for line in hour_csv.strip().splitlines()[1:]:
        stamp = line.split(",")[2]
        assert ISO_DT.match(stamp) and stamp[14:19] == "00:00", line
    day_csv = env.get("export.csv", grain="day", start="2026-11-12", end="2026-11-14").text
    assert not re.search(r"\d{2}:\d{2}", day_csv)
    for forbidden in ("13:37", "41:09", "34:56", "17:23", "59:59"):
        assert forbidden not in hour_csv and forbidden not in day_csv


def test_no_finer_grain_can_be_requested(env):
    seed(env)
    for grain in ("minute", "second", "event", "raw", "5min"):
        assert env.get("export.csv", grain=grain).status_code == 400
        assert env.get("readings", metric="temp_c", bucket=grain).status_code == 400
    # There is no endpoint that lists events.
    for name in ("events", "event", "raw", "events.csv", "ingest"):
        assert env.get(name).status_code in (404, 405)


def test_numbers_only_change_on_the_hour(env):
    """An opening in the current hour stays invisible until the hour is over."""
    env.clock.now = chi(2026, 11, 14, 15, 20, 0)
    env.add([chi(2026, 11, 14, 14, 30, 0)])
    before = env.get("summary").json()
    assert before["today"]["count"] == 1

    env.add([chi(2026, 11, 14, 15, 19, 30)], backdate=False)  # just happened
    for bump in (0, 60, 600, 39 * 60):                 # polling for the rest of the hour
        env.clock.now = chi(2026, 11, 14, 15, 20, 0) + bump
        s = env.get("summary").json()
        assert s["today"]["count"] == 1 and s["all_time"]["count"] == 1
        assert s["rev"] == before["rev"]
        hours = env.get("hourly", start="2026-11-14", end="2026-11-14").json()["hours"]
        assert hours[-1]["hour"] == 14 and sum(h["count"] for h in hours) == 1

    env.clock.now = chi(2026, 11, 14, 16, 0, 0)        # the hour closes: now it is published
    s = env.get("summary").json()
    assert s["today"]["count"] == 2 and s["rev"] != before["rev"]
    hours = env.get("hourly", start="2026-11-14", end="2026-11-14").json()["hours"]
    assert hours[-1]["hour"] == 15 and hours[-1]["count"] == 1


def test_late_upload_does_not_reveal_its_arrival_time(env):
    """An old event uploaded mid-hour also waits for the next boundary."""
    env.clock.now = chi(2026, 11, 14, 15, 20, 0)
    env.add([chi(2026, 11, 14, 9, 0, 0)])
    env.clock.now = chi(2026, 11, 14, 16, 5, 0)
    assert env.get("summary").json()["all_time"]["count"] == 1
    env.add([chi(2026, 11, 14, 10, 0, 0)], backdate=False)  # queued event arrives at 4:05 PM
    assert env.get("summary").json()["all_time"]["count"] == 1
    env.clock.now = chi(2026, 11, 14, 17, 0, 1)
    assert env.get("summary").json()["all_time"]["count"] == 2


def test_last_heard_is_rounded_down_to_the_hour(env):
    env.clock.now = chi(2026, 11, 14, 15, 47, 13)
    env.post(env.body())
    sensor = env.get("summary").json()["sensor"]
    assert sensor["last_heard"] == "2026-11-14T15:00:00-06:00"
    assert sensor["devices"][0]["last_heard"] == "2026-11-14T15:00:00-06:00"


def test_device_internals_are_not_public(env):
    seed(env)
    text = env.get("summary").text
    for private in ("rssi", "heap", "boot_id", "reset_reason", "uptime", "door_open", "queue", "dropped"):
        assert private not in text


def test_live_mode_is_an_explicit_opt_in(make_env):
    env = make_env(publish_granularity_s=0)
    env.clock.now = chi(2026, 11, 14, 15, 20, 0)
    env.add([chi(2026, 11, 14, 15, 19, 30)])
    assert env.get("summary").json()["today"]["count"] == 1
