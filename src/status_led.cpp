#include "status_led.h"

#include <atomic>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "config.h"

#if STATUS_LED_ENABLED

namespace {

std::atomic<uint8_t> g_mode((uint8_t)LedMode::Boot);
std::atomic<bool> g_doorOpen(false);
std::atomic<bool> g_test(false);

struct Rgb {
  uint8_t r, g, b;
  bool operator!=(const Rgb& o) const { return r != o.r || g != o.g || b != o.b; }
};

uint8_t scale(uint8_t v) { return (uint8_t)(((uint16_t)v * STATUS_LED_BRIGHTNESS) / 255); }

void show(Rgb c) {
  // A WS2812 needs a timed data stream; digitalWrite() cannot drive it.
  // neopixelWrite() generates the stream with the RMT peripheral.
  neopixelWrite(STATUS_LED_PIN, scale(c.r), scale(c.g), scale(c.b));
}

Rgb pattern(uint32_t ms) {
  const Rgb off = {0, 0, 0};
  if (g_doorOpen.load()) return Rgb{255, 120, 0};  // amber
  bool blinkOn = (ms % 1000) < 500;
  switch ((LedMode)g_mode.load()) {
    case LedMode::Boot: return Rgb{255, 255, 255};
    case LedMode::NoLink: return blinkOn ? Rgb{0, 0, 255} : off;
    case LedMode::Ok: return (ms % 5000) < 100 ? Rgb{0, 255, 0} : off;
    case LedMode::Sending: return Rgb{0, 255, 255};
    case LedMode::ServerError: return blinkOn ? Rgb{255, 0, 0} : off;
    case LedMode::AuthError: return blinkOn ? Rgb{255, 0, 255} : off;
  }
  return off;
}

void ledTask(void*) {
  Rgb last = {1, 2, 3};  // impossible value forces the first write
  for (;;) {
    if (g_test.exchange(false)) {
      const Rgb seq[] = {{255, 0, 0}, {0, 255, 0}, {0, 0, 255}, {255, 255, 255}};
      for (const Rgb& c : seq) {
        show(c);
        vTaskDelay(pdMS_TO_TICKS(600));
      }
      last = Rgb{1, 2, 3};
    }
    Rgb c = pattern(millis());
    if (c != last) {
      show(c);
      last = c;
    }
    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

}  // namespace

void ledBegin() {
  show(Rgb{255, 255, 255});
  xTaskCreatePinnedToCore(ledTask, "led", 3072, nullptr, 1, nullptr, 1);
}
void ledSetMode(LedMode mode) { g_mode.store((uint8_t)mode); }
void ledSetDoorOpen(bool open) { g_doorOpen.store(open); }
void ledTest() { g_test.store(true); }

#else  // no status LED on this board

void ledBegin() {}
void ledSetMode(LedMode) {}
void ledSetDoorOpen(bool) {}
void ledTest() {}

#endif
