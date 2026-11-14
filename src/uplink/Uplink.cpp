#include "Uplink.h"

#include <sys/time.h>
#include <time.h>

// Any time before this (2023-11-14) means "the clock was never set".
static const time_t kMinValidEpoch = 1700000000;

uint32_t clockEpoch() {
  time_t now = time(nullptr);
  return (now >= kMinValidEpoch) ? (uint32_t)now : 0;
}

void clockSet(uint32_t epoch) {
  struct timeval tv;
  tv.tv_sec = (time_t)epoch;
  tv.tv_usec = 0;
  settimeofday(&tv, nullptr);
}

uint32_t Uplink::epochNow() { return clockEpoch(); }
