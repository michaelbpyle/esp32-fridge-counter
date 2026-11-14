from __future__ import annotations

from conftest import BENCH_KEY, chi


def test_empty_database_gives_an_honest_empty_summary(env):
    s = env.get("summary").json()
    assert s["has_data"] is False
    assert s["today"]["count"] == 0 and s["all_time"]["count"] == 0
    assert s["all_time"]["first_date"] is None and s["busiest_hour"] is None
    assert s["sensor"]["online"] is False and s["sensor"]["last_heard"] is None
    assert env.get("daily").json()["days"] == []
    assert env.get("hourly").json()["hours"] == []
    assert env.get("heatmap").json()["cells"] == []
    assert env.get("durations").json()["measured"] == 0
    csv_text = env.get("export.csv").text
    assert csv_text.strip() == "date,weekday,openings,avg_open_seconds,held_open,complete_day"


def test_daily_counts_and_zero_filling(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    env.add([chi(2026, 11, 10, 8, 15), chi(2026, 11, 10, 17, 40), chi(2026, 11, 13, 12, 5)])
    data = env.get("daily", start="2026-11-01", end="2026-11-14").json()
    got = [(d["date"], d["count"]) for d in data["days"]]
    # Starts at the first day with data (days before the counter existed are
    # not reported as zero), then every day appears, zeros included.
    assert got == [
        ("2026-11-10", 2), ("2026-11-11", 0), ("2026-11-12", 0), ("2026-11-13", 1), ("2026-11-14", 0),
    ]
    assert data["effective_start"] == "2026-11-10"
    assert data["days"][0]["weekday"] == 1  # Tuesday
    assert data["days"][-1]["complete"] is False and data["days"][0]["complete"] is True


def test_hourly_zero_filling_stops_at_the_published_hour(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    env.add([chi(2026, 11, 14, 8, 15), chi(2026, 11, 14, 8, 50), chi(2026, 11, 14, 13, 1)])
    hours = env.get("hourly", start="2026-11-14", end="2026-11-14").json()["hours"]
    assert [h["hour"] for h in hours] == list(range(15))  # 00:00 .. 14:00; 15:00 is still open
    assert [h["count"] for h in hours] == [0] * 8 + [2] + [0] * 4 + [1, 0]
    assert hours[8]["t"] == "2026-11-14T08:00:00-06:00"


def test_short_openings_are_stored_but_not_counted(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    t = chi(2026, 11, 13, 10, 0)
    env.post(env.body(events=[
        env.ev(t, dur_ms=300),        # bounce: stored, not counted
        env.ev(t + 60, dur_ms=999),   # just under the threshold
        env.ev(t + 120, dur_ms=1000), # exactly the threshold: counted
        env.ev(t + 180, dur_ms=9000),
        env.ev(t + 240, dur_ms=-1),   # held open: counted once
        env.ev(t + 300, dur_ms=None), # duration not reported: counted
    ]))
    env.backdate()
    assert env.rows("SELECT COUNT(*) FROM events") == [(6,)]
    day = env.get("daily", start="2026-11-13", end="2026-11-13").json()["days"][0]
    assert day["count"] == 4
    assert day["avg_open_s"] == 5.0      # (1.0 + 9.0) / 2; held-open and unreported excluded
    assert day["held_open"] == 1
    d = env.get("durations", start="2026-11-13", end="2026-11-13").json()
    assert (d["measured"], d["held_open"], d["not_reported"], d["too_short_excluded"]) == (2, 1, 1, 2)
    assert [b["count"] for b in d["bins"]] == [1, 1, 0, 0, 0, 0, 0]
    assert d["bins"][0]["min_s"] == 1.0 and d["bins"][-1]["max_s"] is None
    assert env.get("summary").json()["all_time"]["count"] == 4


def test_bounce_threshold_is_configurable(make_env):
    env = make_env(min_open_ms=0)
    env.clock.now = chi(2026, 11, 14, 15, 20)
    env.post(env.body(events=[env.ev(chi(2026, 11, 13, 10, 0), dur_ms=50)]))
    env.backdate()
    assert env.get("summary").json()["all_time"]["count"] == 1


def test_test_device_is_excluded_unless_asked_for(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    env.add([chi(2026, 11, 13, 9, 0), chi(2026, 11, 13, 9, 30)])
    env.add([chi(2026, 11, 13, 9, 10)] * 1 + [chi(2026, 11, 13, 20, 0)] * 4,
            device="bench-01", key=BENCH_KEY)
    rd = {"t": chi(2026, 11, 13, 9, 0), "sensor": "bmp280", "metric": "temp_c", "value": 99.0}
    env.post(env.body(readings=[rd], device="bench-01"), key=BENCH_KEY)
    env.backdate()

    assert env.rows("SELECT COUNT(*) FROM events WHERE device_id='bench-01'") == [(5,)]  # stored
    pub = env.get("summary").json()
    assert pub["all_time"]["count"] == 2
    assert pub["metrics"] == []
    assert [d["device_id"] for d in pub["sensor"]["devices"]] == ["fridge-01"]
    assert env.get("daily", start="2026-11-13", end="2026-11-13").json()["days"][0]["count"] == 2
    hours = env.get("hourly", start="2026-11-13", end="2026-11-13").json()["hours"]
    assert sum(h["count"] for h in hours) == 2 and hours[20]["count"] == 0
    assert sum(c["total"] for c in env.get("heatmap", start="2026-11-13", end="2026-11-13").json()["cells"]) == 2
    assert env.get("readings", metric="temp_c", start="2026-11-13", end="2026-11-13").json()["series"] == []
    assert "2026-11-13,Friday,2," in env.get("export.csv", start="2026-11-13", end="2026-11-13").text

    bench = env.get("summary", device="bench-01").json()
    assert bench["all_time"]["count"] == 5 and bench["metrics"] == ["temp_c"]
    assert bench["sensor"]["devices"][0]["test"] is True
    assert env.get("daily", start="2026-11-13", end="2026-11-13", device="bench-01").json()["days"][0]["count"] == 5
    only = env.get("summary", device="fridge-01").json()
    assert only["all_time"]["count"] == 2


def test_unknown_or_invalid_device(env):
    assert env.get("summary", device="nobody").status_code == 404
    assert env.get("summary", device="x; DROP TABLE events").status_code == 400


def test_dst_fall_back_day_has_25_hours(env):
    # 2026-11-01: clocks go back at 2:00 CDT -> 1:00 CST, so 1 AM happens twice.
    env.clock.now = chi(2026, 11, 3, 12, 0)
    first_1am = chi(2026, 11, 1, 1, 30, fold=0)   # 01:30 CDT (-05:00)
    second_1am = chi(2026, 11, 1, 1, 30, fold=1)  # 01:30 CST (-06:00), one hour later
    assert second_1am - first_1am == 3600
    env.add([first_1am, first_1am + 60, second_1am, chi(2026, 11, 1, 23, 59, 59), chi(2026, 11, 2, 0, 0, 0)])

    hours = env.get("hourly", start="2026-11-01", end="2026-11-01").json()["hours"]
    assert len(hours) == 25
    assert [h["hour"] for h in hours[:4]] == [0, 1, 1, 2]
    assert hours[1]["t"] == "2026-11-01T01:00:00-05:00" and hours[1]["count"] == 2
    assert hours[2]["t"] == "2026-11-01T01:00:00-06:00" and hours[2]["count"] == 1
    assert hours[-1]["hour"] == 23 and hours[-1]["count"] == 1
    assert sum(h["count"] for h in hours) == 4

    days = env.get("daily", start="2026-11-01", end="2026-11-02").json()["days"]
    assert [(d["date"], d["count"]) for d in days] == [("2026-11-01", 4), ("2026-11-02", 1)]

    hm = env.get("heatmap", start="2026-11-01", end="2026-11-01").json()
    cell = {(c["weekday"], c["hour"]): c for c in hm["cells"]}
    sunday_1am = cell[(6, 1)]
    assert sunday_1am["total"] == 3 and sunday_1am["hours"] == 2 and sunday_1am["avg"] == 1.5
    assert cell[(6, 2)]["hours"] == 1

    csv_lines = env.get("export.csv", grain="hour", start="2026-11-01", end="2026-11-01").text.strip().splitlines()
    assert len(csv_lines) == 26
    assert csv_lines[2] == "2026-11-01,1,2026-11-01T01:00:00-05:00,2"
    assert csv_lines[3] == "2026-11-01,1,2026-11-01T01:00:00-06:00,1"


def test_dst_spring_forward_day_has_23_hours(env):
    # 2026-03-08: clocks jump from 2:00 CST to 3:00 CDT; 2 AM does not exist.
    env.clock.now = chi(2026, 3, 10, 12, 0)
    env.add([chi(2026, 3, 8, 1, 59, 59), chi(2026, 3, 8, 3, 0, 0), chi(2026, 3, 7, 23, 30), chi(2026, 3, 9, 0, 10)])
    hours = env.get("hourly", start="2026-03-08", end="2026-03-08").json()["hours"]
    assert len(hours) == 23
    assert [h["hour"] for h in hours[:4]] == [0, 1, 3, 4]
    assert hours[1]["t"] == "2026-03-08T01:00:00-06:00" and hours[1]["count"] == 1
    assert hours[2]["t"] == "2026-03-08T03:00:00-05:00" and hours[2]["count"] == 1
    days = env.get("daily", start="2026-03-07", end="2026-03-09").json()["days"]
    assert [(d["date"], d["count"]) for d in days] == [("2026-03-07", 1), ("2026-03-08", 2), ("2026-03-09", 1)]
    hm = env.get("heatmap", start="2026-03-08", end="2026-03-08").json()
    assert next(c for c in hm["cells"] if (c["weekday"], c["hour"]) == (6, 2))["hours"] == 0


def test_local_day_boundary_uses_chicago_not_utc(env):
    # 23:30 CDT on 2026-07-04 is 04:30 UTC on 2026-07-05; it belongs to July 4.
    env.clock.now = chi(2026, 7, 6, 12, 0)
    env.add([chi(2026, 7, 4, 23, 30), chi(2026, 7, 5, 0, 30)])
    days = env.get("daily", start="2026-07-04", end="2026-07-05").json()["days"]
    assert [(d["date"], d["count"]) for d in days] == [("2026-07-04", 1), ("2026-07-05", 1)]
    assert env.rows("SELECT local_date, local_hour FROM events ORDER BY ts") == [("2026-07-04", 23), ("2026-07-05", 0)]


def test_heatmap_averages_divide_by_real_occurrences(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)  # a Saturday
    # Two Mondays (Nov 2 and 9) in range: 4 openings at 5 PM on one, 2 on the other.
    env.add([chi(2026, 11, 2, 17, m) for m in (1, 2, 3, 4)] + [chi(2026, 11, 9, 17, m) for m in (5, 6)])
    hm = env.get("heatmap", start="2026-11-02", end="2026-11-14").json()
    cell = next(c for c in hm["cells"] if (c["weekday"], c["hour"]) == (0, 17))
    assert (cell["total"], cell["hours"], cell["avg"]) == (6, 2, 3.0)
    assert len(hm["cells"]) == 168
    monday = hm["by_weekday"][0]
    assert (monday["total"], monday["days"], monday["avg"]) == (6, 2, 3.0)
    five_pm = hm["by_hour"][17]
    assert five_pm["total"] == 6 and five_pm["hours"] == 12  # Nov 2..13 complete; Nov 14 not yet at 5 PM
    assert five_pm["avg"] == 0.5


def test_summary_numbers(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)  # Saturday 3:20 PM; published through 3:00 PM
    times = (
        [chi(2026, 11, 14, 9, m) for m in (1, 2, 3)]            # today: 3
        + [chi(2026, 11, 13, 9, m) for m in (1, 2)]              # yesterday before 3 PM: 2
        + [chi(2026, 11, 13, 18, 0)]                             # yesterday after 3 PM: 1
        + [chi(2026, 11, 9, 17, m) for m in range(10)]           # Monday: 10
        + [chi(2026, 11, 3, 12, m) for m in range(4)]            # previous week: 4
        + [chi(2026, 10, 1, 12, 0)]                              # long ago: 1
    )
    env.add(times)
    env.post(env.body())  # heartbeat
    s = env.get("summary").json()
    assert s["has_data"] is True
    assert s["today"] == {"date": "2026-11-14", "count": 3, "yesterday_same_time": 2}
    assert s["yesterday"] == {"date": "2026-11-13", "count": 3}
    assert s["last_7_days"]["count"] == 16 and s["last_7_days"]["previous"] == 4
    assert s["last_30_days"]["count"] == 20 and s["last_30_days"]["previous"] == 1
    assert s["last_7_days"]["previous_complete"] is True
    assert s["last_30_days"]["previous_complete"] is False  # counter is only 45 days old
    assert s["all_time"]["count"] == 21 and s["all_time"]["first_date"] == "2026-10-01"
    assert s["all_time"]["days"] == 45
    assert s["busiest_hour"]["hour"] == 17
    assert s["busiest_weekday"]["name"] == "Monday"
    assert s["typical_open_s"] == 8.0
    assert s["data_through"] == "2026-11-14T15:00:00-06:00"
    assert s["sensor"]["online"] is True


def test_online_window(env):
    env.post(env.body())
    assert env.get("summary").json()["sensor"]["online"] is True
    env.clock.now += 39 * 60
    assert env.get("summary").json()["sensor"]["online"] is True
    env.clock.now += 2 * 60
    assert env.get("summary").json()["sensor"]["online"] is False


def test_readings_bucketed_avg_min_max(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    base = chi(2026, 11, 13, 10, 0)
    rds = [{"t": base + i * 600, "sensor": "bmp280", "metric": "temp_c", "value": v}
           for i, v in enumerate([20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 30.0])]
    rds += [{"t": base, "sensor": "hx711_1", "metric": "weight_g", "value": 1500.0},
            {"t": base, "sensor": "hx711_2", "metric": "weight_g", "value": 700.0}]
    env.post(env.body(readings=rds))
    env.backdate()
    data = env.get("readings", metric="temp_c", start="2026-11-13", end="2026-11-13", bucket="hour").json()
    assert len(data["series"]) == 1 and data["series"][0]["sensor"] == "bmp280"
    pts = data["series"][0]["points"]
    assert pts[0] == {"t": "2026-11-13T10:00:00-06:00", "avg": 22.5, "min": 20.0, "max": 25.0, "n": 6}
    assert pts[1]["avg"] == 30.0
    day = env.get("readings", metric="temp_c", start="2026-11-13", end="2026-11-13", bucket="day").json()
    assert day["series"][0]["points"] == [{"t": "2026-11-13", "avg": 23.571, "min": 20.0, "max": 30.0, "n": 7}]
    w = env.get("readings", metric="weight_g", start="2026-11-13", end="2026-11-13").json()
    assert [s["sensor"] for s in w["series"]] == ["hx711_1", "hx711_2"]
    assert env.get("summary").json()["metrics"] == ["temp_c", "weight_g"]


def test_query_parameters_are_validated_and_bounded(env):
    bad = [
        ("daily", {"start": "yesterday"}),
        ("daily", {"start": "2026-11-10", "end": "2026-11-01"}),
        ("daily", {"start": "2000-01-01", "end": "2026-11-01"}),
        ("daily", {"start": "2026-13-45"}),
        ("hourly", {"start": "2020-01-01", "end": "2026-11-01"}),
        ("heatmap", {"end": "x" * 500}),
        ("readings", {}),
        ("readings", {"metric": "temp_c; DROP"}),
        ("readings", {"metric": "temp_c", "bucket": "second"}),
        ("readings", {"metric": "temp_c", "bucket": "minute"}),
        ("export.csv", {"grain": "minute"}),
        ("export.csv", {"grain": "event"}),
    ]
    for name, params in bad:
        r = env.get(name, **params)
        assert r.status_code == 400, (name, params, r.text)
        assert r.json()["ok"] is False
    assert env.get("nope").status_code == 404
    assert env.client.post("/fridge/api/v1/summary").status_code == 405


def test_future_end_date_is_capped_at_today(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    env.add([chi(2026, 11, 13, 9, 0)])
    data = env.get("daily", start="2026-11-13", end="2026-12-25").json()
    assert data["end"] == "2026-11-14" and [d["date"] for d in data["days"]] == ["2026-11-13", "2026-11-14"]


def test_caching_headers_and_health(env):
    r = env.get("summary")
    assert r.headers["cache-control"] == "public, max-age=60"
    r = env.get("export.csv")
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    h = env.get("health")
    assert h.status_code == 200 and h.json()["ok"] is True
    assert h.headers["cache-control"] == "no-store"
    assert env.post(env.body()).headers["cache-control"] == "no-store"


def test_seven_day_average(env):
    env.clock.now = chi(2026, 11, 14, 15, 20)
    times = []
    for day in range(1, 14):                     # Nov 1..13, `day` openings each day
        times += [chi(2026, 11, day, 10, m) for m in range(day)]
    env.add(times)
    days = env.get("daily", start="2026-11-05", end="2026-11-14").json()["days"]
    by = {d["date"]: d for d in days}
    assert by["2026-11-05"]["avg7"] is None       # only 5 complete days of history so far
    assert by["2026-11-07"]["avg7"] == 4.0        # mean of 1..7
    assert by["2026-11-13"]["avg7"] == 10.0       # mean of 7..13
    assert by["2026-11-14"]["avg7"] is None       # today is not complete
