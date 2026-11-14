/*
 * Hollygrove Community Fridge door counter - main program.
 *
 * What runs where (see docs/firmware.md for the full picture):
 *   door task  (door_task.cpp)  samples the reed switch every 2 ms, debounces,
 *                               times each opening, hands finished events over
 *   led task   (status_led.cpp) animates the status LED
 *   main loop  (this file)      stores events in the flash-backed queue, reads
 *                               sensors, talks to the server, serial console
 *
 * The transport (WiFi now, Walter LTE-M later) is behind the Uplink
 * interface and is picked by the PlatformIO environment, not by this file.
 */

#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>
#include <esp_task_wdt.h>
#include <esp_timer.h>

#include <fc_protocol.h>
#include <fc_queue.h>

#include "config.h"
#include "door_task.h"
#include "journal_fs.h"
#include "sensors/Sensors.h"
#include "status_led.h"
#include "uplink/Uplink.h"

// TLS handshakes need more stack than the Arduino default of 8 KB.
SET_LOOP_TASK_STACK_SIZE(16 * 1024);

namespace {

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
uint32_t g_bootId = 0;
const char* g_resetReason = "unknown";

Preferences g_prefs;            // NVS namespace "fridge"
uint32_t g_doorTotal = 0;       // lifetime openings, persisted
uint32_t g_dropped = 0;         // lifetime events dropped (queue full), persisted
uint32_t g_rejected = 0;        // events discarded after an HTTP 400, this boot

LittleFsJournal g_journal;
fc::EventQueue g_queue(EVENT_QUEUE_CAPACITY, &g_journal, EVENT_QUEUE_CAPACITY * 2);
fc::Ring<fc::ReadingRec, 96> g_readings;
uint32_t g_readingsLost = 0;

fc::Backoff g_backoff(RETRY_BASE_MS, RETRY_MAX_MS);
uint32_t g_nextAttemptMs = 0;   // do not POST before this (millis)
bool g_haveOkPost = false;
uint32_t g_lastOkPostMs = 0;
uint32_t g_lastEventMs = 0;     // when the newest event was queued
bool g_forceSend = false;
bool g_authError = false;
bool g_lastPostFailed = false;
int g_lastHttpStatus = 0;
uint32_t g_postsOk = 0, g_postsFailed = 0;

// Copy of the last batch the server acknowledged, for the "resend" test
// command (proves the server recognises a retransmit as duplicates).
fc::DoorEventRec g_lastAcked[MAX_EVENTS_PER_POST];
size_t g_lastAckedCount = 0;

uint32_t g_lastSampleMs = 0;
uint32_t g_lastReprobeMs = 0;

uint32_t uptimeS() { return (uint32_t)(esp_timer_get_time() / 1000000LL); }

const char* resetReasonName(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "poweron";
    case ESP_RST_EXT: return "external";
    case ESP_RST_SW: return "software";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "int_wdt";
    case ESP_RST_TASK_WDT: return "task_wdt";
    case ESP_RST_WDT: return "wdt";
    case ESP_RST_DEEPSLEEP: return "deepsleep";
    case ESP_RST_BROWNOUT: return "brownout";
    case ESP_RST_SDIO: return "sdio";
    default: return "unknown";
  }
}

void watchdogBegin() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  esp_task_wdt_config_t cfg = {};
  cfg.timeout_ms = WATCHDOG_TIMEOUT_S * 1000;
  cfg.idle_core_mask = 0;
  cfg.trigger_panic = true;
  if (esp_task_wdt_reconfigure(&cfg) != ESP_OK) esp_task_wdt_init(&cfg);
#else
  esp_task_wdt_init(WATCHDOG_TIMEOUT_S, true);
#endif
  esp_task_wdt_add(nullptr);  // watch the main loop task
}

// ---------------------------------------------------------------------------
// Sensor readings -> RAM ring buffer
// ---------------------------------------------------------------------------
class ReadingSink : public SensorSink {
 public:
  explicit ReadingSink(bool echo) : echo_(echo) {}
  void add(const char* sensor, const char* metric, float value) override {
    fc::ReadingRec r;
    r.t = clockEpoch();
    r.up_s = uptimeS();
    strlcpy(r.sensor, sensor, sizeof(r.sensor));
    strlcpy(r.metric, metric, sizeof(r.metric));
    r.value = value;
    if (g_readings.push(r)) g_readingsLost++;
    count++;
    if (echo_) Serial.printf("[sensor] %s %s = %.2f\n", sensor, metric, (double)value);
  }
  int count = 0;

 private:
  bool echo_;
};

void sampleSensors(bool echo) {
  if (sensorsPresentCount() == 0) {
    if (echo) Serial.println("[sensor] no sensors connected");
    return;
  }
  ReadingSink sink(echo);
  sensorsSampleAll(sink, Serial);
  if (!echo) Serial.printf("[sensor] sampled %d reading(s)\n", sink.count);
}

// ---------------------------------------------------------------------------
// Door notices from the door task
// ---------------------------------------------------------------------------
void handleDoorNotices() {
  DoorNotice n;
  while (doorPoll(n)) {
    switch (n.kind) {
      case DoorNotice::Opened:
        g_doorTotal++;
        g_prefs.putUInt("total", g_doorTotal);  // one small NVS write per opening
        Serial.printf("[door] OPENED  (#%lu this boot, %lu lifetime)\n",
                      (unsigned long)doorOpeningsThisBoot(), (unsigned long)g_doorTotal);
        break;
      case DoorNotice::Closed:
        Serial.println("[door] closed");
        break;
      case DoorNotice::Event: {
        bool dropped = g_queue.push(n.event);
        if (dropped) {
          g_dropped++;
          g_prefs.putUInt("dropped", g_dropped);
          Serial.println("[queue] FULL: oldest event dropped");
        }
        g_lastEventMs = millis();
        if (n.event.dur_ms < 0) {
          Serial.printf("[door] event n=%lu HELD OPEN past %lu s (queued, %u waiting)\n",
                        (unsigned long)n.event.n, (unsigned long)(DOOR_HELD_OPEN_LIMIT_MS / 1000),
                        (unsigned)g_queue.size());
        } else {
          Serial.printf("[door] event n=%lu open for %ld ms (queued, %u waiting)\n",
                        (unsigned long)n.event.n, (long)n.event.dur_ms, (unsigned)g_queue.size());
        }
        if (!g_queue.storeHealthy()) Serial.println("[queue] WARNING: flash journal write failed; event held in RAM only");
        break;
      }
    }
  }
  ledSetDoorOpen(doorIsOpen());
}

// ---------------------------------------------------------------------------
// Sending
// ---------------------------------------------------------------------------
void attemptPost() {
  Uplink& up = uplinkInstance();

  // Copy the batch out of the queue. Only this loop task changes the queue,
  // so the first nEv entries are still the same ones after the POST returns.
  static fc::DoorEventRec events[MAX_EVENTS_PER_POST];
  static fc::ReadingRec readings[MAX_READINGS_PER_POST];
  size_t nEv = g_queue.size() < (size_t)MAX_EVENTS_PER_POST ? g_queue.size() : (size_t)MAX_EVENTS_PER_POST;
  for (size_t i = 0; i < nEv; i++) events[i] = g_queue.at(i);
  size_t nRd = g_readings.size() < (size_t)MAX_READINGS_PER_POST ? g_readings.size() : (size_t)MAX_READINGS_PER_POST;
  for (size_t i = 0; i < nRd; i++) readings[i] = g_readings.at(i);

  fc::PayloadHeader h;
  h.deviceId = DEVICE_ID;
  h.fw = FW_VERSION;
  h.bootId = g_bootId;
  h.uplink = up.name();
  h.sentAt = up.epochNow();
  h.uptimeS = uptimeS();
  h.doorTotal = g_doorTotal;

  fc::StatusInfo st;
  st.rssi = up.signalDbm();
  st.heap = ESP.getFreeHeap();
  st.doorOpen = doorIsOpen();
  st.queue = (uint32_t)(g_queue.size() - nEv);
  st.dropped = g_dropped;
  st.resetReason = g_resetReason;

  std::string body = fc::buildPayload(h, events, nEv, readings, nRd, st);
  std::string response;

  ledSetMode(LedMode::Sending);
  uint32_t t0 = millis();
  int status = up.postJson(SERVER_PATH, body, response);
  uint32_t took = millis() - t0;
  esp_task_wdt_reset();

  fc::IngestResponse ir;
  bool bodyOk = (status == 200) && fc::parseIngestResponse(response, ir);
  fc::PostAction action = fc::classifyResponse(status, bodyOk);
  g_lastHttpStatus = status;
  uint32_t now = millis();

  switch (action) {
    case fc::PostAction::Ack:
      if (nEv > 0) {
        for (size_t i = 0; i < nEv; i++) g_lastAcked[i] = events[i];
        g_lastAckedCount = nEv;
      }
      g_queue.popFront(nEv);
      g_readings.popFront(nRd);
      g_backoff.reset();
      g_haveOkPost = true;
      g_lastOkPostMs = now;
      g_authError = false;
      g_lastPostFailed = false;
      g_postsOk++;
      g_nextAttemptMs = now + 250;  // more batches may be waiting
      Serial.printf("[post] OK in %lu ms: %u event(s), %u reading(s) sent; server accepted %lu, duplicates %lu; %u still queued\n",
                    (unsigned long)took, (unsigned)nEv, (unsigned)nRd, (unsigned long)ir.accepted,
                    (unsigned long)ir.duplicates, (unsigned)g_queue.size());
      if (clockEpoch() == 0 && ir.serverTime != 0) {
        clockSet(ir.serverTime);
        Serial.printf("[time] clock set from server_time %lu\n", (unsigned long)ir.serverTime);
      }
      break;

    case fc::PostAction::DropBatch:
      // The server says this batch is malformed. Re-sending it would fail
      // forever and block everything behind it, so it is discarded.
      g_queue.popFront(nEv);
      g_readings.popFront(nRd);
      g_rejected += (uint32_t)nEv;
      g_lastPostFailed = true;
      g_postsFailed++;
      g_nextAttemptMs = now + RETRY_BASE_MS;
      Serial.printf("[post] *** HTTP 400: server rejected the batch as malformed. %u event(s) and %u reading(s) DISCARDED. ***\n",
                    (unsigned)nEv, (unsigned)nRd);
      break;

    case fc::PostAction::RetryAuth:
      g_authError = true;
      g_lastPostFailed = true;
      g_postsFailed++;
      g_nextAttemptMs = now + AUTH_RETRY_MS;
      Serial.printf("[post] *** HTTP %d: the server refused the device key. Check DEVICE_ID / DEVICE_KEY in secrets.h. ***\n", status);
      Serial.printf("[post] nothing was discarded (%u event(s) waiting); next try in %lu s\n",
                    (unsigned)g_queue.size(), (unsigned long)(AUTH_RETRY_MS / 1000));
      break;

    case fc::PostAction::RetryBackoff: {
      uint32_t wait = g_backoff.next(esp_random());
      g_lastPostFailed = true;
      g_postsFailed++;
      g_nextAttemptMs = now + wait;
      if (status > 0) {
        Serial.printf("[post] failed: HTTP %d%s after %lu ms", status,
                      status == 200 ? " with an unexpected body" : "", (unsigned long)took);
      } else {
        Serial.printf("[post] failed: no HTTP response (error %d) after %lu ms", status, (unsigned long)took);
      }
      Serial.printf("; %u event(s) kept; retry %lu in %lu s\n", (unsigned)g_queue.size(),
                    (unsigned long)g_backoff.failures(), (unsigned long)(wait / 1000));
      break;
    }
  }
}

void updateLedMode() {
  Uplink& up = uplinkInstance();
  if (!up.isConnected()) ledSetMode(LedMode::NoLink);
  else if (g_authError) ledSetMode(LedMode::AuthError);
  else if (g_lastPostFailed) ledSetMode(LedMode::ServerError);
  else ledSetMode(LedMode::Ok);
}

void maybeSend() {
  Uplink& up = uplinkInstance();
  uint32_t now = millis();
  bool eventsReady = !g_queue.empty() && (now - g_lastEventMs >= SEND_COALESCE_MS ||
                                          g_queue.size() >= (size_t)MAX_EVENTS_PER_POST);
  bool heartbeatDue = !g_haveOkPost || (now - g_lastOkPostMs >= HEARTBEAT_INTERVAL_MS);
  bool allowed = g_forceSend || (int32_t)(now - g_nextAttemptMs) >= 0;
  if ((eventsReady || heartbeatDue || g_forceSend) && allowed && up.isConnected()) {
    g_forceSend = false;
    attemptPost();
  }
}

// ---------------------------------------------------------------------------
// Serial console
// ---------------------------------------------------------------------------
void printStatus() {
  uint32_t now = millis();
  uint32_t epoch = clockEpoch();
  Serial.println("---------------- status ----------------");
  Serial.printf("firmware: %s, device_id %s, boot_id %lu, uptime %lu s, reset reason: %s\n", FW_VERSION,
                DEVICE_ID, (unsigned long)g_bootId, (unsigned long)uptimeS(), g_resetReason);
  if (epoch) Serial.printf("clock: UTC epoch %lu\n", (unsigned long)epoch);
  else Serial.println("clock: NOT SET yet (events are sent with age_s instead of a timestamp)");
  int raw = doorRawLevel();
  Serial.printf("door: GPIO%d raw level = %s -> door is %s%s (config: open when %s)\n", PIN_REED,
                raw == HIGH ? "HIGH" : "LOW", doorIsOpen() ? "OPEN" : "CLOSED",
                doorHeldOpen() ? " [held open]" : "", DOOR_OPEN_WHEN_HIGH ? "HIGH" : "LOW");
  Serial.printf("door: %lu opening(s) this boot, %lu lifetime\n", (unsigned long)doorOpeningsThisBoot(),
                (unsigned long)g_doorTotal);
  Serial.printf("queue: %u of %u event(s) waiting, %lu dropped (lifetime), %lu rejected by server (this boot), journal %s (%u records)\n",
                (unsigned)g_queue.size(), (unsigned)g_queue.capacity(), (unsigned long)g_dropped,
                (unsigned long)g_rejected, g_queue.storeHealthy() ? "ok" : "NOT WRITABLE",
                (unsigned)g_queue.journalRecords());
  Serial.printf("readings: %u waiting, %lu lost\n", (unsigned)g_readings.size(), (unsigned long)g_readingsLost);
  uplinkInstance().printStatus(Serial);
  Serial.printf("posts: %lu ok, %lu failed, last HTTP status %d", (unsigned long)g_postsOk,
                (unsigned long)g_postsFailed, g_lastHttpStatus);
  if (g_haveOkPost) Serial.printf(", last ok %lu s ago", (unsigned long)((now - g_lastOkPostMs) / 1000));
  int32_t wait = (int32_t)(g_nextAttemptMs - now);
  if (wait > 0) Serial.printf(", next attempt in %ld s", (long)(wait / 1000));
  Serial.println();
  Serial.printf("memory: %lu bytes free heap (lowest %lu); door notices lost: %lu\n",
                (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMinFreeHeap(),
                (unsigned long)doorNoticesLost());
  sensorsPrint(Serial);
  Serial.println("----------------------------------------");
}

void printHelp() {
  Serial.println("commands:");
  Serial.println("  status          show everything (door pin level, queue, link, sensors)");
  Serial.println("  sim [ms]        simulate a door opening lasting [ms] (default 3000; works without a switch)");
  Serial.println("  send            send a heartbeat to the server now");
  Serial.println("  resend          test: send the last delivered events again (server must report duplicates)");
  Serial.println("  sensors         read all connected sensors now");
  Serial.println("  probe           look again for newly connected sensors");
  Serial.println("  scale           show the HX711 scale channels");
  Serial.println("  tare <1-4>      zero a scale with the shelf empty");
  Serial.println("  cal <1-4> <g>   calibrate a scale with a known weight of <g> grams on it");
  Serial.println("  led             cycle the status LED red, green, blue, white");
  Serial.println("  pins            show the level of the spare GPIOs (board identification)");
  Serial.println("  clearqueue      delete all waiting events (asks for 'clearqueue yes')");
  Serial.println("  reboot          restart the device");
}

// Reads a few otherwise unused pins with the internal pull-down and pull-up.
// A pin that stays HIGH against the pull-down has something on the board
// pulling it up (for example the SD-card slot on a Freenove WROOM board);
// a pin that follows both is not connected to anything.
void printPins() {
#if defined(UPLINK_WALTER)
  const uint8_t pins[] = {1, 2, 7, 10, 11, 12, 13, 15};  // 14, 21 and 47 belong to the modem
#else
  const uint8_t pins[] = {1, 2, 7, 10, 11, 12, 13, 14, 15, 21, 47};
#endif
  Serial.println("spare pins (level with pull-down / with pull-up):");
  for (uint8_t p : pins) {
    pinMode(p, INPUT_PULLDOWN);
    delay(2);
    int down = digitalRead(p);
    pinMode(p, INPUT_PULLUP);
    delay(2);
    int upLevel = digitalRead(p);
    pinMode(p, INPUT);
    const char* verdict = (down == LOW && upLevel == HIGH) ? "free (floating)"
                          : (down == HIGH && upLevel == HIGH) ? "pulled HIGH by something on the board"
                          : (down == LOW && upLevel == LOW) ? "pulled LOW by something on the board"
                          : "odd";
    Serial.printf("  GPIO%-2d  %s / %s  -> %s\n", p, down ? "HIGH" : "LOW", upLevel ? "HIGH" : "LOW", verdict);
  }
  Serial.printf("  flash chip: %lu MB, PSRAM: %lu bytes\n", (unsigned long)(ESP.getFlashChipSize() / (1024 * 1024)),
                (unsigned long)ESP.getPsramSize());
}

void handleCommand(char* line) {
  char* cmd = strtok(line, " \t");
  if (!cmd) return;
  char* a1 = strtok(nullptr, " \t");
  char* a2 = strtok(nullptr, " \t");
  if (!strcmp(cmd, "status") || !strcmp(cmd, "s")) {
    printStatus();
  } else if (!strcmp(cmd, "help") || !strcmp(cmd, "?")) {
    printHelp();
  } else if (!strcmp(cmd, "sim")) {
    long ms = a1 ? atol(a1) : 3000;
    if (ms < 1) ms = 1;
    if (ms > 3600000L) ms = 3600000L;
    if (doorSimulating()) {
      Serial.println("[sim] a simulation is already running; wait for it to finish");
    } else {
      doorSimulate((uint32_t)ms);
      Serial.printf("[sim] simulating: door shut, open for %ld ms, shut again (real switch ignored meanwhile)\n", ms);
    }
  } else if (!strcmp(cmd, "send")) {
    g_forceSend = true;
    Serial.println("[post] sending now (if the link is up)");
  } else if (!strcmp(cmd, "resend")) {
    if (g_lastAckedCount == 0) {
      Serial.println("[resend] nothing has been acknowledged by the server yet");
    } else {
      for (size_t i = 0; i < g_lastAckedCount; i++) g_queue.push(g_lastAcked[i]);
      g_forceSend = true;
      Serial.printf("[resend] re-sending the last acknowledged batch (%u event(s)); the server should count them as duplicates\n",
                    (unsigned)g_lastAckedCount);
    }
  } else if (!strcmp(cmd, "sensors")) {
    sampleSensors(true);
  } else if (!strcmp(cmd, "probe")) {
    sensorsReprobe(Serial);
    sensorsPrint(Serial);
  } else if (!strcmp(cmd, "scale")) {
    scalePrint(Serial);
  } else if (!strcmp(cmd, "tare")) {
    scaleTare((uint8_t)(a1 ? atoi(a1) : 0), Serial);
  } else if (!strcmp(cmd, "cal")) {
    scaleCalibrate((uint8_t)(a1 ? atoi(a1) : 0), a2 ? (float)atof(a2) : 0.0f, Serial);
  } else if (!strcmp(cmd, "led")) {
    ledTest();
    Serial.println("[led] test: red, green, blue, white");
  } else if (!strcmp(cmd, "pins")) {
    printPins();
  } else if (!strcmp(cmd, "clearqueue")) {
    if (a1 && !strcmp(a1, "yes")) {
      g_queue.popFront(g_queue.size());
      Serial.println("[queue] cleared");
    } else {
      Serial.printf("[queue] %u event(s) waiting. Type 'clearqueue yes' to delete them.\n", (unsigned)g_queue.size());
    }
  } else if (!strcmp(cmd, "reboot")) {
    Serial.println("rebooting...");
    Serial.flush();
    ESP.restart();
  } else {
    Serial.printf("unknown command '%s' (type 'help')\n", cmd);
  }
}

void pollConsole() {
  static char line[64];
  static size_t len = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      if (len > 0) {
        line[len] = 0;
        len = 0;
        handleCommand(line);
      }
    } else if (len < sizeof(line) - 1) {
      line[len++] = c;
    }
  }
}

}  // namespace

// ---------------------------------------------------------------------------
// Arduino entry points
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(300);
  g_resetReason = resetReasonName(esp_reset_reason());
  do {
    g_bootId = esp_random();
  } while (g_bootId == 0);

  Serial.println();
  Serial.println("========================================");
  Serial.println(" Hollygrove Community Fridge door counter");
  Serial.printf(" firmware %s, uplink: %s\n", FW_VERSION, uplinkInstance().name());
  Serial.printf(" device_id %s, boot_id %lu, reset reason: %s\n", DEVICE_ID, (unsigned long)g_bootId, g_resetReason);
  Serial.println("========================================");

  watchdogBegin();
  ledBegin();

  // Lifetime counters (NVS).
  g_prefs.begin("fridge", false);
  g_doorTotal = g_prefs.getUInt("total", 0);
  g_dropped = g_prefs.getUInt("dropped", 0);

  // Door first: counting must not wait for the network or the filesystem.
  doorBegin(g_bootId);
  Serial.printf("[door] GPIO%d raw level %s -> door is %s at start-up; lifetime count %lu\n", PIN_REED,
                doorRawLevel() == HIGH ? "HIGH" : "LOW", doorIsOpen() ? "OPEN" : "CLOSED",
                (unsigned long)g_doorTotal);

  // Event queue (LittleFS journal).
  if (!g_journal.begin()) Serial.println("[queue] WARNING: could not mount the flash filesystem; queue is RAM-only");
  g_queue.load();
  Serial.printf("[queue] %u event(s) restored from flash, %lu dropped lifetime\n", (unsigned)g_queue.size(),
                (unsigned long)g_dropped);
  if (g_queue.corruptRecordsSeen()) Serial.println("[queue] note: a damaged journal record was skipped (power loss during a write)");

  uplinkInstance().begin();

  sensorsBegin(Serial);
  sampleSensors(false);
  g_lastSampleMs = millis();
  g_lastReprobeMs = millis();

  Serial.println("ready. Type 'help' for commands.");
}

void loop() {
  esp_task_wdt_reset();
  pollConsole();
  handleDoorNotices();

  uplinkInstance().loop();

  uint32_t now = millis();
  if (now - g_lastSampleMs >= SENSOR_SAMPLE_INTERVAL_MS) {
    g_lastSampleMs = now;
    sampleSensors(false);
  }
  if (SENSOR_REPROBE_INTERVAL_MS > 0 && now - g_lastReprobeMs >= SENSOR_REPROBE_INTERVAL_MS) {
    g_lastReprobeMs = now;
    sensorsReprobe(Serial);
  }

  maybeSend();
  updateLedMode();
  delay(10);
}
