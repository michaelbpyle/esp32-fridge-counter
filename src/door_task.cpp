#include "door_task.h"

#include <atomic>

#include <esp_task_wdt.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include <fc_door.h>

#include "config.h"
#include "uplink/Uplink.h"

namespace {

QueueHandle_t g_notices = nullptr;
fc::DoorMonitor* g_monitor = nullptr;

std::atomic<bool> g_open(false);
std::atomic<bool> g_held(false);
std::atomic<uint32_t> g_openings(0);
std::atomic<uint32_t> g_lost(0);
// Simulation: a request (open time in samples) is picked up by the door task,
// which then plays closed -> open -> closed and re-baselines on the real pin.
std::atomic<uint32_t> g_simRequest(0);
std::atomic<bool> g_simActive(false);
// Shut long enough on each side of the opening for the debouncer to see it.
const uint32_t kSimShutSamples = (DOOR_DEBOUNCE_MS + 30) / DOOR_SAMPLE_PERIOD_MS + 1;

void sendNotice(const DoorNotice& n) {
  if (xQueueSend(g_notices, &n, 0) != pdTRUE) g_lost++;
}

bool readDoorOpen() {
  bool high = digitalRead(PIN_REED) == HIGH;
#if DOOR_OPEN_WHEN_HIGH
  return high;
#else
  return !high;
#endif
}

void doorTask(void*) {
  esp_task_wdt_add(nullptr);
  TickType_t lastWake = xTaskGetTickCount();
  uint32_t loops = 0;
  uint32_t simPos = 0, simOpen = 0;  // position in / open length of the running simulation
  for (;;) {
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(DOOR_SAMPLE_PERIOD_MS));
    uint64_t nowMs = (uint64_t)(esp_timer_get_time() / 1000);

    bool open = readDoorOpen();
    if (!g_simActive.load()) {
      uint32_t req = g_simRequest.exchange(0);
      if (req > 0) {
        simOpen = req;
        simPos = 0;
        g_simActive.store(true);
      }
    }
    if (g_simActive.load()) {
      uint32_t total = kSimShutSamples + simOpen + kSimShutSamples;
      if (simPos < total) {
        open = (simPos >= kSimShutSamples && simPos < kSimShutSamples + simOpen);
        simPos++;
      } else {
        // Simulation over: start again from the real pin, exactly like at
        // power-up (an already-open door is not counted).
        g_simActive.store(false);
        g_monitor->begin(open, nowMs);
      }
    }

    fc::DoorOutput out = g_monitor->update(open, nowMs, clockEpoch());
    g_open.store(g_monitor->isOpen());
    g_held.store(g_monitor->heldOpen());
    g_openings.store(g_monitor->openingsThisBoot());

    DoorNotice n;
    n.event = out.event;
    if (out.opened) {
      n.kind = DoorNotice::Opened;
      sendNotice(n);
    }
    if (out.eventReady) {
      n.kind = DoorNotice::Event;
      sendNotice(n);
    }
    if (out.closed) {
      n.kind = DoorNotice::Closed;
      sendNotice(n);
    }

    if ((++loops % 256) == 0) esp_task_wdt_reset();
  }
}

}  // namespace

void doorBegin(uint32_t bootId) {
  pinMode(PIN_REED, INPUT_PULLUP);
  delay(2);  // let the pull-up settle before the first read
  g_notices = xQueueCreate(64, sizeof(DoorNotice));
  static fc::DoorMonitor monitor(bootId, DOOR_DEBOUNCE_MS, DOOR_HELD_OPEN_LIMIT_MS);
  g_monitor = &monitor;
  bool open = readDoorOpen();
  monitor.begin(open, (uint64_t)(esp_timer_get_time() / 1000));
  g_open.store(open);
  // Priority 10: above the Arduino loop (1), below the WiFi/system tasks.
  // Pinned to core 1 (the application core) so the radio stack on core 0
  // cannot delay it.
  xTaskCreatePinnedToCore(doorTask, "door", 4096, nullptr, 10, nullptr, 1);
}

bool doorPoll(DoorNotice& out) {
  return g_notices && xQueueReceive(g_notices, &out, 0) == pdTRUE;
}

bool doorIsOpen() { return g_open.load(); }
bool doorHeldOpen() { return g_held.load(); }
int doorRawLevel() { return digitalRead(PIN_REED); }
uint32_t doorOpeningsThisBoot() { return g_openings.load(); }
uint32_t doorNoticesLost() { return g_lost.load(); }

void doorSimulate(uint32_t ms) {
  uint32_t samples = ms / DOOR_SAMPLE_PERIOD_MS;
  if (samples == 0) samples = 1;
  g_simRequest.store(samples);
}

bool doorSimulating() { return g_simActive.load() || g_simRequest.load() != 0; }
