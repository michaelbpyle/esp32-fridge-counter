// Status LED (WS2812 addressable RGB LED). See docs/firmware.md for the codes.
#pragma once

#include <Arduino.h>

enum class LedMode : uint8_t {
  Boot,         // white, steady
  NoLink,       // blue, slow blink: no WiFi / no cellular registration
  Ok,           // green blip every 5 s: connected, last POST fine
  Sending,      // cyan, steady: POST in progress
  ServerError,  // red, slow blink: connected but the last POST failed
  AuthError     // magenta, slow blink: server rejected the device key
};

void ledBegin();
void ledSetMode(LedMode mode);
void ledSetDoorOpen(bool open);   // amber while the door is open (overrides the mode)
void ledTest();                   // cycle red, green, blue, white (bench check)
