// Unit tests for lib/fridge_core (the hardware-independent logic).
//
// Run on the board:  pio test -e esp32s3
// Run on the PC:     pio test -e native      (needs a host C++ compiler)
#include <unity.h>

#include <string>
#include <vector>

#include <fc_door.h>
#include <fc_protocol.h>
#include <fc_queue.h>
#include <fc_sensor_math.h>

#ifdef ARDUINO
#include <Arduino.h>
#endif

using namespace fc;

void setUp() {}
void tearDown() {}

// ---------------------------------------------------------------------------
// Debouncer
// ---------------------------------------------------------------------------
static void test_debounce_ignores_short_glitch() {
  Debouncer d(50);
  d.reset(false, 0);
  TEST_ASSERT_FALSE(d.update(true, 10));
  TEST_ASSERT_FALSE(d.update(true, 40));   // 30 ms so far
  TEST_ASSERT_FALSE(d.update(false, 45));  // glitch ended
  TEST_ASSERT_FALSE(d.update(false, 200));
  TEST_ASSERT_FALSE(d.state());
}

static void test_debounce_reports_stable_change_with_edge_time() {
  Debouncer d(50);
  d.reset(false, 0);
  TEST_ASSERT_FALSE(d.update(true, 100));
  TEST_ASSERT_FALSE(d.update(true, 149));
  TEST_ASSERT_TRUE(d.update(true, 150));
  TEST_ASSERT_TRUE(d.state());
  TEST_ASSERT_EQUAL_UINT32(100, (uint32_t)d.edgeMs());  // when it first changed
  TEST_ASSERT_FALSE(d.update(true, 151));               // no repeat
}

static void test_debounce_bounce_restarts_timer() {
  Debouncer d(50);
  d.reset(false, 0);
  // Contact bounce: toggles every 5 ms for 30 ms, then settles open.
  uint64_t t = 0;
  for (int i = 0; i < 6; i++, t += 5) TEST_ASSERT_FALSE(d.update(i % 2 == 0, t));
  // settles at t=30
  bool changed = false;
  uint64_t when = 0;
  for (; t < 200 && !changed; t += 2) {
    changed = d.update(true, t);
    when = t;
  }
  TEST_ASSERT_TRUE(changed);
  TEST_ASSERT_TRUE(when >= 80 && when <= 84);  // 30 ms settle + 50 ms stable
}

static void test_debounce_never_misses_edge_after_recent_change() {
  // The old firmware ignored every change for 200 ms after a change, so a
  // close followed quickly by a re-open could be lost. This one must see
  // every change that lasts at least the debounce time.
  Debouncer d(50);
  d.reset(false, 0);
  int edges = 0;
  bool raw = false;
  for (uint64_t t = 0; t < 1000; t += 2) {
    if (t == 100) raw = true;    // open
    if (t == 220) raw = false;   // close 120 ms later
    if (t == 300) raw = true;    // re-open 80 ms after that
    if (t == 420) raw = false;   // close
    if (d.update(raw, t)) edges++;
  }
  TEST_ASSERT_EQUAL_INT(4, edges);
}

// ---------------------------------------------------------------------------
// DoorMonitor
// ---------------------------------------------------------------------------
struct Sim {
  DoorMonitor m;
  uint64_t t = 0;
  std::vector<DoorEventRec> events;
  int opened = 0, closed = 0;
  Sim(uint32_t boot, uint32_t held) : m(boot, 50, held) {}
  void run(bool rawOpen, uint64_t ms, uint32_t epochAtStart = 0) {
    uint64_t start = t;
    for (uint64_t end = t + ms; t < end; t += 2) {
      uint32_t epoch = epochAtStart ? epochAtStart + (uint32_t)((t - start) / 1000) : 0;
      DoorOutput o = m.update(rawOpen, t, epoch);
      if (o.opened) opened++;
      if (o.closed) closed++;
      if (o.eventReady) events.push_back(o.event);
    }
  }
};

static void test_door_basic_opening() {
  Sim s(777, 600000);
  s.m.begin(false, 0);
  s.run(false, 1000);
  s.run(true, 8200, 1794599990);
  TEST_ASSERT_EQUAL_INT(1, s.opened);
  TEST_ASSERT_EQUAL_INT(0, (int)s.events.size());  // event only at close
  s.run(false, 1000);
  TEST_ASSERT_EQUAL_INT(1, s.closed);
  TEST_ASSERT_EQUAL_INT(1, (int)s.events.size());
  TEST_ASSERT_EQUAL_UINT32(777, s.events[0].boot);
  TEST_ASSERT_EQUAL_UINT32(1, s.events[0].n);
  TEST_ASSERT_EQUAL_UINT32(1794599990, s.events[0].t);
  TEST_ASSERT_INT_WITHIN(4, 8200, s.events[0].dur_ms);
  TEST_ASSERT_EQUAL_UINT32(1, s.events[0].up_s);
}

static void test_door_counts_sequence_numbers() {
  Sim s(1, 600000);
  s.m.begin(false, 0);
  for (int i = 0; i < 5; i++) {
    s.run(true, 300);
    s.run(false, 300);
  }
  TEST_ASSERT_EQUAL_INT(5, (int)s.events.size());
  for (int i = 0; i < 5; i++) TEST_ASSERT_EQUAL_UINT32((uint32_t)(i + 1), s.events[i].n);
  TEST_ASSERT_EQUAL_UINT32(5, s.m.openingsThisBoot());
}

static void test_door_held_open_emits_once_and_waits_for_close() {
  Sim s(9, 10000);  // 10 s limit for the test
  s.m.begin(false, 0);
  s.run(true, 25000);
  TEST_ASSERT_EQUAL_INT(1, s.opened);
  TEST_ASSERT_EQUAL_INT(1, (int)s.events.size());
  TEST_ASSERT_EQUAL_INT32(-1, s.events[0].dur_ms);
  TEST_ASSERT_TRUE(s.m.heldOpen());
  s.run(true, 60000);                               // still open: nothing more
  TEST_ASSERT_EQUAL_INT(1, (int)s.events.size());
  s.run(false, 500);                                // close: no second event
  TEST_ASSERT_EQUAL_INT(1, (int)s.events.size());
  TEST_ASSERT_FALSE(s.m.heldOpen());
  s.run(true, 500);                                 // next opening counts again
  s.run(false, 500);
  TEST_ASSERT_EQUAL_INT(2, (int)s.events.size());
  TEST_ASSERT_EQUAL_UINT32(2, s.events[1].n);
  TEST_ASSERT_INT_WITHIN(4, 500, s.events[1].dur_ms);
}

static void test_door_open_at_boot_not_counted() {
  Sim s(5, 600000);
  s.m.begin(true, 0);  // door already open when power comes up
  s.run(true, 2000);
  s.run(false, 500);
  TEST_ASSERT_EQUAL_INT(0, s.opened);
  TEST_ASSERT_EQUAL_INT(0, (int)s.events.size());
  s.run(true, 400);
  s.run(false, 400);
  TEST_ASSERT_EQUAL_INT(1, (int)s.events.size());
  TEST_ASSERT_EQUAL_UINT32(1, s.events[0].n);
}

static void test_door_no_clock_gives_t_zero() {
  Sim s(5, 600000);
  s.m.begin(false, 0);
  s.run(true, 400, 0);
  s.run(false, 400, 0);
  TEST_ASSERT_EQUAL_UINT32(0, s.events[0].t);
}

static void test_door_glitches_do_not_count() {
  Sim s(5, 600000);
  s.m.begin(false, 0);
  for (int i = 0; i < 50; i++) {
    s.run(true, 20);   // shorter than the 50 ms debounce
    s.run(false, 100);
  }
  TEST_ASSERT_EQUAL_INT(0, s.opened);
  TEST_ASSERT_EQUAL_INT(0, (int)s.events.size());
}

// ---------------------------------------------------------------------------
// EventQueue + journal
// ---------------------------------------------------------------------------
class MemStore : public JournalStore {
 public:
  std::vector<uint8_t> bytes;
  bool failAppend = false, failReplace = false, failRead = false;
  int appends = 0, replaces = 0;
  bool readAll(std::vector<uint8_t>& out) override {
    if (failRead) return false;
    out = bytes;
    return true;
  }
  bool append(const uint8_t* d, size_t n) override {
    if (failAppend) return false;
    bytes.insert(bytes.end(), d, d + n);
    appends++;
    return true;
  }
  bool replaceAll(const uint8_t* d, size_t n) override {
    if (failReplace) return false;
    bytes.assign(d, d + n);
    replaces++;
    return true;
  }
};

static DoorEventRec ev(uint32_t n, int32_t dur = 1000) {
  DoorEventRec e = {42, n, 1794600000u + n, dur, n * 10};
  return e;
}

static void test_queue_fifo_order() {
  MemStore st;
  EventQueue q(8, &st, 100);
  TEST_ASSERT_TRUE(q.load());
  for (uint32_t i = 1; i <= 5; i++) TEST_ASSERT_FALSE(q.push(ev(i)));
  TEST_ASSERT_EQUAL_UINT32(5, (uint32_t)q.size());
  TEST_ASSERT_EQUAL_UINT32(1, q.at(0).n);
  q.popFront(2);
  TEST_ASSERT_EQUAL_UINT32(3, q.at(0).n);
  TEST_ASSERT_EQUAL_UINT32(3, (uint32_t)q.size());
}

static void test_queue_survives_reboot() {
  MemStore st;
  {
    EventQueue q(8, &st, 100);
    q.load();
    for (uint32_t i = 1; i <= 6; i++) q.push(ev(i, i == 3 ? -1 : 500));
    q.popFront(2);
  }
  EventQueue q2(8, &st, 100);  // "reboot": new object, same flash contents
  TEST_ASSERT_TRUE(q2.load());
  TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)q2.size());
  TEST_ASSERT_EQUAL_UINT32(3, q2.at(0).n);
  TEST_ASSERT_EQUAL_INT32(-1, q2.at(0).dur_ms);
  TEST_ASSERT_EQUAL_UINT32(42, q2.at(0).boot);
  TEST_ASSERT_EQUAL_UINT32(1794600003u, q2.at(0).t);
  TEST_ASSERT_EQUAL_UINT32(30, q2.at(0).up_s);
  TEST_ASSERT_EQUAL_UINT32(6, q2.at(3).n);
}

static void test_queue_drops_oldest_when_full() {
  MemStore st;
  EventQueue q(4, &st, 100);
  q.load();
  int dropped = 0;
  for (uint32_t i = 1; i <= 7; i++) dropped += q.push(ev(i)) ? 1 : 0;
  TEST_ASSERT_EQUAL_INT(3, dropped);
  TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)q.size());
  TEST_ASSERT_EQUAL_UINT32(4, q.at(0).n);
  TEST_ASSERT_EQUAL_UINT32(7, q.at(3).n);
  EventQueue q2(4, &st, 100);
  q2.load();
  TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)q2.size());
  TEST_ASSERT_EQUAL_UINT32(4, q2.at(0).n);
  TEST_ASSERT_EQUAL_UINT32(7, q2.at(3).n);
}

static void test_queue_torn_write_is_recovered() {
  MemStore st;
  {
    EventQueue q(8, &st, 100);
    q.load();
    for (uint32_t i = 1; i <= 3; i++) q.push(ev(i));
  }
  // Power fails half-way through writing a 4th record.
  for (int i = 0; i < 11; i++) st.bytes.push_back(0xE1);
  EventQueue q2(8, &st, 100);
  TEST_ASSERT_TRUE(q2.load());
  TEST_ASSERT_EQUAL_UINT32(3, (uint32_t)q2.size());
  TEST_ASSERT_EQUAL_UINT32(3 * EventQueue::kRecordSize, (uint32_t)st.bytes.size());  // journal repaired
  q2.push(ev(4));
  EventQueue q3(8, &st, 100);
  q3.load();
  TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)q3.size());
  TEST_ASSERT_EQUAL_UINT32(4, q3.at(3).n);
}

static void test_queue_corrupt_record_stops_replay() {
  MemStore st;
  {
    EventQueue q(8, &st, 100);
    q.load();
    for (uint32_t i = 1; i <= 4; i++) q.push(ev(i));
  }
  st.bytes[2 * EventQueue::kRecordSize + 7] ^= 0x55;  // flip bits in record 3
  EventQueue q2(8, &st, 100);
  q2.load();
  TEST_ASSERT_EQUAL_UINT32(2, (uint32_t)q2.size());
  TEST_ASSERT_EQUAL_UINT32(1, q2.corruptRecordsSeen());
}

static void test_queue_compacts_instead_of_growing() {
  MemStore st;
  EventQueue q(4, &st, 16);
  q.load();
  for (uint32_t i = 1; i <= 200; i++) {
    q.push(ev(i));
    if (i % 2 == 0) q.popFront(2);
  }
  TEST_ASSERT_TRUE(st.bytes.size() <= 16 * EventQueue::kRecordSize);
  TEST_ASSERT_TRUE(st.replaces > 0);
  EventQueue q2(4, &st, 16);
  q2.load();
  TEST_ASSERT_EQUAL_UINT32(0, (uint32_t)q2.size());
}

static void test_queue_write_failure_keeps_ram_and_recovers() {
  MemStore st;
  EventQueue q(8, &st, 100);
  q.load();
  q.push(ev(1));
  st.failAppend = true;
  st.failReplace = true;
  q.push(ev(2));
  q.push(ev(3));
  TEST_ASSERT_FALSE(q.storeHealthy());
  TEST_ASSERT_EQUAL_UINT32(3, (uint32_t)q.size());  // nothing lost in RAM
  st.failAppend = false;
  st.failReplace = false;
  q.push(ev(4));                                    // flash works again
  TEST_ASSERT_TRUE(q.storeHealthy());
  EventQueue q2(8, &st, 100);
  q2.load();
  TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)q2.size());  // 2 and 3 made it to flash too
  TEST_ASSERT_EQUAL_UINT32(2, q2.at(1).n);
}

static void test_queue_unreadable_store_is_ram_only() {
  MemStore st;
  st.failRead = true;
  EventQueue q(8, &st, 100);
  TEST_ASSERT_FALSE(q.load());
  q.push(ev(1));
  TEST_ASSERT_EQUAL_UINT32(1, (uint32_t)q.size());
}

static void test_queue_500_capacity_roundtrip() {
  MemStore st;
  EventQueue q(500, &st, 1000);
  q.load();
  int dropped = 0;
  for (uint32_t i = 1; i <= 620; i++) dropped += q.push(ev(i)) ? 1 : 0;
  TEST_ASSERT_EQUAL_INT(120, dropped);
  // Acknowledge in batches of 20 like the real sender.
  for (int b = 0; b < 5; b++) q.popFront(20);
  EventQueue q2(500, &st, 1000);
  q2.load();
  TEST_ASSERT_EQUAL_UINT32(400, (uint32_t)q2.size());
  TEST_ASSERT_EQUAL_UINT32(221, q2.at(0).n);
  TEST_ASSERT_EQUAL_UINT32(620, q2.at(399).n);
}

// ---------------------------------------------------------------------------
// Payload builder
// ---------------------------------------------------------------------------
static PayloadHeader hdr(uint32_t sentAt, uint32_t uptime) {
  PayloadHeader h;
  h.deviceId = "fridge-01";
  h.fw = "1.0.0";
  h.bootId = 2893746123u;
  h.uplink = "wifi";
  h.sentAt = sentAt;
  h.uptimeS = uptime;
  h.doorTotal = 42;
  return h;
}

static StatusInfo status() {
  StatusInfo s;
  s.rssi = -61;
  s.heap = 123456;
  s.doorOpen = false;
  s.queue = 0;
  s.dropped = 0;
  s.resetReason = "poweron";
  return s;
}

static void test_payload_matches_contract_example() {
  DoorEventRec e = {2893746123u, 17, 1794599990u, 8200, 1224};
  ReadingRec r;
  r.t = 1794599900u;
  r.up_s = 1134;
  strcpy(r.sensor, "bmp280");
  strcpy(r.metric, "temp_c");
  r.value = 23.4f;
  std::string s = buildPayload(hdr(1794600000u, 1234), &e, 1, &r, 1, status());
  const char* expect =
      "{\"device_id\":\"fridge-01\",\"fw\":\"1.0.0\",\"boot_id\":2893746123,\"uplink\":\"wifi\","
      "\"sent_at\":1794600000,\"uptime_s\":1234,\"door_total\":42,"
      "\"events\":[{\"boot\":2893746123,\"n\":17,\"t\":1794599990,\"age_s\":10,\"dur_ms\":8200}],"
      "\"readings\":[{\"t\":1794599900,\"age_s\":100,\"sensor\":\"bmp280\",\"metric\":\"temp_c\",\"value\":23.40}],"
      "\"status\":{\"rssi\":-61,\"heap\":123456,\"door_open\":false,\"queue\":0,\"dropped\":0,"
      "\"reset_reason\":\"poweron\"}}";
  TEST_ASSERT_EQUAL_STRING(expect, s.c_str());
}

static void test_payload_heartbeat_has_empty_arrays() {
  std::string s = buildPayload(hdr(0, 5), nullptr, 0, nullptr, 0, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "\"events\":[],\"readings\":[],"));
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "\"sent_at\":0,"));
}

static void test_payload_held_open_and_unknown_clock() {
  // Same boot, clock unknown then and now: t=0, age from uptime.
  DoorEventRec e = {2893746123u, 3, 0, -1, 100};
  std::string s = buildPayload(hdr(0, 160), &e, 1, nullptr, 0, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "{\"boot\":2893746123,\"n\":3,\"t\":0,\"age_s\":60,\"dur_ms\":-1}"));
}

static void test_payload_backfills_time_when_clock_arrives_later() {
  // Same boot, clock was unknown at the opening but is known now.
  DoorEventRec e = {2893746123u, 3, 0, 900, 100};
  std::string s = buildPayload(hdr(1794600000u, 160), &e, 1, nullptr, 0, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "\"t\":1794599940,\"age_s\":60,"));
}

static void test_payload_previous_boot_without_clock_omits_age() {
  DoorEventRec e = {1111, 9, 0, 700, 50};  // other boot, no timestamp
  std::string s = buildPayload(hdr(1794600000u, 20), &e, 1, nullptr, 0, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "{\"boot\":1111,\"n\":9,\"t\":0,\"dur_ms\":700}"));
}

static void test_payload_previous_boot_with_clock_has_age() {
  DoorEventRec e = {1111, 9, 1794590000u, 700, 50};
  std::string s = buildPayload(hdr(1794600000u, 20), &e, 1, nullptr, 0, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "{\"boot\":1111,\"n\":9,\"t\":1794590000,\"age_s\":10000,\"dur_ms\":700}"));
  // ... but not if our own clock is unknown right now.
  s = buildPayload(hdr(0, 20), &e, 1, nullptr, 0, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "{\"boot\":1111,\"n\":9,\"t\":1794590000,\"dur_ms\":700}"));
}

static void test_payload_escapes_strings_and_skips_nan() {
  PayloadHeader h = hdr(0, 1);
  h.deviceId = "a\"b\\c\n";
  ReadingRec r[2];
  memset(r, 0, sizeof(r));
  strcpy(r[0].sensor, "bmp280");
  strcpy(r[0].metric, "temp_c");
  r[0].value = 0.0f / 0.0f;  // NaN
  strcpy(r[1].sensor, "hx711_2");
  strcpy(r[1].metric, "weight_g");
  r[1].value = -12.345f;
  std::string s = buildPayload(h, nullptr, 0, r, 2, status());
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "\"device_id\":\"a\\\"b\\\\c\\u000a\""));
  TEST_ASSERT_NULL(strstr(s.c_str(), "nan"));
  TEST_ASSERT_NOT_NULL(strstr(s.c_str(), "\"readings\":[{\"t\":0,\"age_s\":1,\"sensor\":\"hx711_2\",\"metric\":\"weight_g\",\"value\":-12.35}]"));
}

static void test_payload_20_events_size() {
  DoorEventRec e[20];
  for (int i = 0; i < 20; i++) e[i] = ev((uint32_t)i + 1);
  std::string s = buildPayload(hdr(1794600000u, 5000), e, 20, nullptr, 0, status());
  TEST_ASSERT_TRUE(s.size() < 4000);
  int count = 0;
  for (size_t p = s.find("\"dur_ms\""); p != std::string::npos; p = s.find("\"dur_ms\"", p + 1)) count++;
  TEST_ASSERT_EQUAL_INT(20, count);
}

// ---------------------------------------------------------------------------
// Response parsing + retry policy
// ---------------------------------------------------------------------------
static void test_response_parse_ok() {
  IngestResponse r;
  TEST_ASSERT_TRUE(parseIngestResponse("{\"ok\": true, \"accepted\": 2, \"duplicates\": 0, \"server_time\": 1794600001}", r));
  TEST_ASSERT_TRUE(r.ok);
  TEST_ASSERT_EQUAL_UINT32(2, r.accepted);
  TEST_ASSERT_EQUAL_UINT32(0, r.duplicates);
  TEST_ASSERT_EQUAL_UINT32(1794600001u, r.serverTime);
  TEST_ASSERT_TRUE(parseIngestResponse("  {\"server_time\":5,\"ok\":true}\n", r));
  TEST_ASSERT_EQUAL_UINT32(5, r.serverTime);
}

static void test_response_parse_rejects_garbage() {
  IngestResponse r;
  TEST_ASSERT_FALSE(parseIngestResponse("", r));
  TEST_ASSERT_FALSE(parseIngestResponse("<html>Login to WiFi</html>", r));
  TEST_ASSERT_FALSE(parseIngestResponse("{\"ok\": false, \"error\": \"x\"}", r));
  TEST_ASSERT_FALSE(parseIngestResponse("{\"accepted\": 2}", r));
  TEST_ASSERT_FALSE(parseIngestResponse("[\"ok\", true]", r));
}

static void test_classify_response() {
  TEST_ASSERT_TRUE(classifyResponse(200, true) == PostAction::Ack);
  TEST_ASSERT_TRUE(classifyResponse(200, false) == PostAction::RetryBackoff);
  TEST_ASSERT_TRUE(classifyResponse(400, false) == PostAction::DropBatch);
  TEST_ASSERT_TRUE(classifyResponse(401, false) == PostAction::RetryAuth);
  TEST_ASSERT_TRUE(classifyResponse(403, false) == PostAction::RetryAuth);
  TEST_ASSERT_TRUE(classifyResponse(404, false) == PostAction::RetryBackoff);  // server not deployed yet
  TEST_ASSERT_TRUE(classifyResponse(500, false) == PostAction::RetryBackoff);
  TEST_ASSERT_TRUE(classifyResponse(502, false) == PostAction::RetryBackoff);
  TEST_ASSERT_TRUE(classifyResponse(429, false) == PostAction::RetryBackoff);
  TEST_ASSERT_TRUE(classifyResponse(-1, false) == PostAction::RetryBackoff);   // timeout
  TEST_ASSERT_TRUE(classifyResponse(0, false) == PostAction::RetryBackoff);
}

static void test_backoff_grows_and_caps() {
  Backoff b(5000, 900000);
  uint32_t prevNominal = 0;
  for (int i = 0; i < 12; i++) {
    uint32_t lo = b.next(0);           // minimum jitter
    uint32_t nominal = lo * 4 / 3;     // lo = 75 % of nominal
    TEST_ASSERT_TRUE(nominal >= prevNominal);
    TEST_ASSERT_TRUE(nominal <= 900000 + 4);
    prevNominal = nominal;
  }
  TEST_ASSERT_UINT32_WITHIN(4, 900000, prevNominal);  // capped at 15 min
  // jitter stays within 75 % .. 125 %
  Backoff c(5000, 900000);
  for (uint32_t r = 0; r < 5000; r += 37) {
    Backoff d(5000, 900000);
    uint32_t v = d.next(r * 7919u);
    TEST_ASSERT_TRUE(v >= 3750 && v <= 6250);
  }
  // reset starts over
  b.reset();
  TEST_ASSERT_EQUAL_UINT32(3750, b.next(0));
  TEST_ASSERT_EQUAL_UINT32(7500, b.next(0));
  TEST_ASSERT_EQUAL_UINT32(15000, b.next(0));
  (void)c;
}

static void test_ring_overwrites_oldest() {
  Ring<int, 4> r;
  for (int i = 1; i <= 6; i++) r.push(i);
  TEST_ASSERT_EQUAL_UINT32(4, (uint32_t)r.size());
  TEST_ASSERT_EQUAL_INT(3, r.at(0));
  TEST_ASSERT_EQUAL_INT(6, r.at(3));
  r.popFront(3);
  TEST_ASSERT_EQUAL_INT(6, r.at(0));
  r.popFront(10);
  TEST_ASSERT_EQUAL_UINT32(0, (uint32_t)r.size());
}

// ---------------------------------------------------------------------------
// Sensor maths
// ---------------------------------------------------------------------------
static void test_bmp280_datasheet_example() {
  // Worked example from the Bosch BMP280 datasheet, section 3.12.
  Bmx280Calib c = {};
  c.T1 = 27504; c.T2 = 26435; c.T3 = -1000;
  c.P1 = 36477; c.P2 = -10685; c.P3 = 3024; c.P4 = 2855; c.P5 = 140;
  c.P6 = -7; c.P7 = 15500; c.P8 = -14600; c.P9 = 6000;
  double tFine = 0;
  double t = bmx280TempC(519888, c, tFine);
  double p = bmx280PressurePa(415148, c, tFine);
  TEST_ASSERT_DOUBLE_WITHIN(0.01, 25.08, t);
  TEST_ASSERT_DOUBLE_WITHIN(0.5, 100653.27, p);
}

static void test_bmx280_calibration_parsing() {
  uint8_t tp[24] = {0x70, 0x6B, 0x43, 0x67, 0x18, 0xFC, 0x7D, 0x8E, 0x43, 0xD6, 0xD0, 0x0B,
                    0x27, 0x0B, 0x8C, 0x00, 0xF9, 0xFF, 0x8C, 0x3C, 0xF8, 0xC6, 0x70, 0x17};
  Bmx280Calib c = {};
  bmx280ParseTP(tp, c);
  TEST_ASSERT_EQUAL_UINT16(27504, c.T1);
  TEST_ASSERT_EQUAL_INT16(26435, c.T2);
  TEST_ASSERT_EQUAL_INT16(-1000, c.T3);
  TEST_ASSERT_EQUAL_UINT16(36477, c.P1);
  TEST_ASSERT_EQUAL_INT16(-10685, c.P2);
  TEST_ASSERT_EQUAL_INT16(-7, c.P6);
  TEST_ASSERT_EQUAL_INT16(6000, c.P9);
  uint8_t h[7] = {0x6E, 0x01, 0x00, 0x13, 0x2D, 0x03, 0x1E};
  bmx280ParseH(75, h, c);
  TEST_ASSERT_EQUAL_UINT8(75, c.H1);
  TEST_ASSERT_EQUAL_INT16(366, c.H2);
  TEST_ASSERT_EQUAL_INT16((0x13 << 4) | 0x0D, c.H4);
  TEST_ASSERT_EQUAL_INT16((0x03 << 4) | 0x02, c.H5);
  TEST_ASSERT_EQUAL_INT8(30, c.H6);
}

static void test_bme280_humidity_in_range() {
  Bmx280Calib c = {};
  c.T1 = 27504; c.T2 = 26435; c.T3 = -1000;
  c.H1 = 75; c.H2 = 366; c.H3 = 0; c.H4 = 317; c.H5 = 50; c.H6 = 30;
  double tFine = 0;
  bmx280TempC(519888, c, tFine);
  double h = bme280HumidityPct(30000, c, tFine);
  TEST_ASSERT_TRUE(h > 20.0 && h < 80.0);
  TEST_ASSERT_DOUBLE_WITHIN(0.001, 0.0, bme280HumidityPct(0, c, tFine));        // clamps low
  TEST_ASSERT_DOUBLE_WITHIN(0.001, 100.0, bme280HumidityPct(65535, c, tFine));  // clamps high
}

static void test_dht_decode() {
  float t = 0, h = 0;
  uint8_t d22[5] = {0x02, 0x8C, 0x01, 0x5F, 0xEE};  // 65.2 %, 35.1 C
  TEST_ASSERT_EQUAL_INT(DHT_22, dhtDecode(d22, DHT_AUTO, t, h));
  TEST_ASSERT_FLOAT_WITHIN(0.01, 35.1, t);
  TEST_ASSERT_FLOAT_WITHIN(0.01, 65.2, h);
  uint8_t neg[5] = {0x01, 0xF4, 0x80, 0x65, 0xDA};  // 50.0 %, -10.1 C
  TEST_ASSERT_EQUAL_INT(DHT_22, dhtDecode(neg, DHT_AUTO, t, h));
  TEST_ASSERT_FLOAT_WITHIN(0.01, -10.1, t);
  uint8_t d11[5] = {55, 0, 24, 3, 82};              // 55 %, 24.3 C
  TEST_ASSERT_EQUAL_INT(DHT_11, dhtDecode(d11, DHT_AUTO, t, h));
  TEST_ASSERT_FLOAT_WITHIN(0.01, 24.3, t);
  TEST_ASSERT_FLOAT_WITHIN(0.01, 55.0, h);
  uint8_t bad[5] = {55, 0, 24, 3, 83};              // wrong checksum
  TEST_ASSERT_EQUAL_INT(DHT_AUTO, dhtDecode(bad, DHT_AUTO, t, h));
  uint8_t zero[5] = {0, 0, 0, 0, 0};                // dead line
  TEST_ASSERT_EQUAL_INT(DHT_AUTO, dhtDecode(zero, DHT_AUTO, t, h));
}

static void test_ds18b20_decode() {
  float t = 0;
  // Datasheet examples: 0x0191 = +25.0625 C, 0xFF5E = -10.125 C.
  uint8_t sp[9] = {0x91, 0x01, 0x4B, 0x46, 0x7F, 0xFF, 0x0F, 0x10, 0x00};
  sp[8] = crc8Dallas(sp, 8);
  TEST_ASSERT_TRUE(ds18b20Decode(sp, t));
  TEST_ASSERT_FLOAT_WITHIN(0.001, 25.0625, t);
  sp[0] = 0x5E;
  sp[1] = 0xFF;
  sp[8] = crc8Dallas(sp, 8);
  TEST_ASSERT_TRUE(ds18b20Decode(sp, t));
  TEST_ASSERT_FLOAT_WITHIN(0.001, -10.125, t);
  sp[8] ^= 1;
  TEST_ASSERT_FALSE(ds18b20Decode(sp, t));  // CRC error
  uint8_t zeros[9] = {0};
  TEST_ASSERT_FALSE(ds18b20Decode(zeros, t));  // no sensor (line low)
  uint8_t ones[9];
  memset(ones, 0xFF, 9);
  TEST_ASSERT_FALSE(ds18b20Decode(ones, t));   // no sensor (line high)
  // Known CRC vector from Maxim application note 27.
  uint8_t rom[7] = {0x02, 0x1C, 0xB8, 0x01, 0x00, 0x00, 0x00};
  TEST_ASSERT_EQUAL_HEX8(0xA2, crc8Dallas(rom, 7));
}

static void test_hx711_conversion() {
  TEST_ASSERT_EQUAL_INT32(1, hx711SignExtend(0x000001));
  TEST_ASSERT_EQUAL_INT32(8388607, hx711SignExtend(0x7FFFFF));
  TEST_ASSERT_EQUAL_INT32(-1, hx711SignExtend(0xFFFFFF));
  TEST_ASSERT_EQUAL_INT32(-8388608, hx711SignExtend(0x800000));
  float g = 0;
  TEST_ASSERT_FALSE(hx711ToGrams(1000, 0, 0.0f, g));  // not calibrated
  TEST_ASSERT_TRUE(hx711ToGrams(84200, 42000, 420.0f, g));
  TEST_ASSERT_FLOAT_WITHIN(0.01, 100.476, g);
  TEST_ASSERT_TRUE(hx711ToGrams(41000, 42000, -420.0f, g));  // cell wired reversed
  TEST_ASSERT_FLOAT_WITHIN(0.01, 2.381, g);
}

static void test_crc16_known_vector() {
  TEST_ASSERT_EQUAL_HEX16(0x29B1, crc16((const uint8_t*)"123456789", 9));
}

static void runAll() {
  UNITY_BEGIN();
  RUN_TEST(test_debounce_ignores_short_glitch);
  RUN_TEST(test_debounce_reports_stable_change_with_edge_time);
  RUN_TEST(test_debounce_bounce_restarts_timer);
  RUN_TEST(test_debounce_never_misses_edge_after_recent_change);
  RUN_TEST(test_door_basic_opening);
  RUN_TEST(test_door_counts_sequence_numbers);
  RUN_TEST(test_door_held_open_emits_once_and_waits_for_close);
  RUN_TEST(test_door_open_at_boot_not_counted);
  RUN_TEST(test_door_no_clock_gives_t_zero);
  RUN_TEST(test_door_glitches_do_not_count);
  RUN_TEST(test_queue_fifo_order);
  RUN_TEST(test_queue_survives_reboot);
  RUN_TEST(test_queue_drops_oldest_when_full);
  RUN_TEST(test_queue_torn_write_is_recovered);
  RUN_TEST(test_queue_corrupt_record_stops_replay);
  RUN_TEST(test_queue_compacts_instead_of_growing);
  RUN_TEST(test_queue_write_failure_keeps_ram_and_recovers);
  RUN_TEST(test_queue_unreadable_store_is_ram_only);
  RUN_TEST(test_queue_500_capacity_roundtrip);
  RUN_TEST(test_payload_matches_contract_example);
  RUN_TEST(test_payload_heartbeat_has_empty_arrays);
  RUN_TEST(test_payload_held_open_and_unknown_clock);
  RUN_TEST(test_payload_backfills_time_when_clock_arrives_later);
  RUN_TEST(test_payload_previous_boot_without_clock_omits_age);
  RUN_TEST(test_payload_previous_boot_with_clock_has_age);
  RUN_TEST(test_payload_escapes_strings_and_skips_nan);
  RUN_TEST(test_payload_20_events_size);
  RUN_TEST(test_response_parse_ok);
  RUN_TEST(test_response_parse_rejects_garbage);
  RUN_TEST(test_classify_response);
  RUN_TEST(test_backoff_grows_and_caps);
  RUN_TEST(test_ring_overwrites_oldest);
  RUN_TEST(test_bmp280_datasheet_example);
  RUN_TEST(test_bmx280_calibration_parsing);
  RUN_TEST(test_bme280_humidity_in_range);
  RUN_TEST(test_dht_decode);
  RUN_TEST(test_ds18b20_decode);
  RUN_TEST(test_hx711_conversion);
  RUN_TEST(test_crc16_known_vector);
  UNITY_END();
}

#ifdef ARDUINO
void setup() {
  delay(2000);  // give the test runner time to open the serial port
  runAll();
}
void loop() {}
#else
int main() {
  runAll();
  return 0;
}
#endif
