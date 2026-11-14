// Transport abstraction. The door, queue and sensor code only ever talk to
// this interface; which implementation is linked in is decided by a single
// build flag (-DUPLINK_WIFI or -DUPLINK_WALTER, set by the PlatformIO env).
#pragma once

#include <Arduino.h>
#include <string>

class Uplink {
 public:
  virtual ~Uplink() {}

  // Short name sent to the server in the "uplink" field.
  virtual const char* name() const = 0;

  // One-time start-up. Must not block for long.
  virtual void begin() = 0;

  // Call from the main loop: keeps the link up (reconnects, time sync).
  virtual void loop() = 0;

  // True when a POST can be attempted right now.
  virtual bool isConnected() = 0;

  // POST a JSON body to `path` on the configured server.
  // Returns the HTTP status code (e.g. 200, 404), or a value <= 0 when no
  // HTTP response was received (DNS/TLS/timeout...). On a positive status the
  // response body is stored in `response`.
  virtual int postJson(const char* path, const std::string& body, std::string& response) = 0;

  // Current UTC epoch seconds, or 0 if the clock has not been set yet.
  virtual uint32_t epochNow();

  // Signal strength in dBm (WiFi RSSI / LTE RSRP), 0 if unknown.
  virtual int signalDbm() = 0;

  // One human-readable status line for the serial console.
  virtual void printStatus(Print& out) = 0;
};

// The uplink selected at build time.
Uplink& uplinkInstance();

// Shared clock helpers (system clock, UTC).
uint32_t clockEpoch();               // 0 while the clock is not set
void clockSet(uint32_t epoch);       // set the system clock
