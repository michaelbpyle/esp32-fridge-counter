// fridge_core: hardware-independent logic for the fridge door counter.
// Nothing in this library may include Arduino or ESP-IDF headers, so it can
// be unit-tested on a PC (PlatformIO "native" env) as well as on the board.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace fc {

// One door opening, as stored in the queue and sent to the server.
struct DoorEventRec {
  uint32_t boot;    // boot_id of the boot in which the door opened
  uint32_t n;       // opening number within that boot, from 1
  uint32_t t;       // UTC epoch second of the opening, 0 = clock was unknown
  int32_t dur_ms;   // how long the door was open; -1 = held open past the limit
  uint32_t up_s;    // device uptime (s) at the opening; only meaningful in boot `boot`
};

// One sensor reading waiting to be sent (RAM only, never persisted).
struct ReadingRec {
  uint32_t t;       // UTC epoch second of the sample, 0 = clock was unknown
  uint32_t up_s;    // device uptime (s) at the sample (always the current boot)
  char sensor[12];  // e.g. "bmp280", "hx711_1"
  char metric[16];  // e.g. "temp_c"
  float value;
};

}  // namespace fc
