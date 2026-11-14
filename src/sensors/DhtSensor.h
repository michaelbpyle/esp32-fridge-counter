// DHT11 / DHT22 (AM2302) temperature + humidity sensor, single data wire.
// The type is detected from the data unless SENSOR_DHT_TYPE forces it.
#pragma once

#include <fc_sensor_math.h>

#include "Sensors.h"
#include "config.h"

class DhtSensor : public Sensor {
 public:
  const char* label() const override { return "DHT11/DHT22"; }

  bool probe() override {
    // Sensors need about a second after power-up, and at least 2 s between reads.
    for (int attempt = 0; attempt < 2; attempt++) {
      uint8_t d[5];
      int r = readRaw(d);
      if (r == kNoResponse) return false;  // nothing connected: stay dormant, no retry
      float t, h;
      fc::DhtType type = (r == kOk) ? fc::dhtDecode(d, forced(), t, h) : fc::DHT_AUTO;
      if (type != fc::DHT_AUTO) {
        type_ = type;
        return true;
      }
      delay(2100);
    }
    return false;
  }

  bool sample(SensorSink& sink) override {
    uint8_t d[5];
    float t, h;
    for (int attempt = 0; attempt < 2; attempt++) {
      if (readRaw(d) == kOk && fc::dhtDecode(d, type_, t, h) != fc::DHT_AUTO) {
        const char* name = (type_ == fc::DHT_11) ? "dht11" : "dht22";
        sink.add(name, "temp_c", t);
        sink.add(name, "humidity_pct", h);
        return true;
      }
      delay(2100);
    }
    return false;
  }

  void describe(Print& out) override {
    out.printf("%s on GPIO%d", type_ == fc::DHT_11 ? "DHT11" : "DHT22", PIN_DHT);
  }

 private:
  enum { kOk = 0, kNoResponse = 1, kBadTiming = 2 };

  static fc::DhtType forced() { return (fc::DhtType)SENSOR_DHT_TYPE; }

  // Wait while the pin stays at `level`; return how long it did (microseconds)
  // or -1 if it took longer than timeoutUs.
  static int32_t pulse(int level, uint32_t timeoutUs) {
    uint32_t start = micros();
    while (digitalRead(PIN_DHT) == level) {
      if (micros() - start > timeoutUs) return -1;
    }
    return (int32_t)(micros() - start);
  }

  int readRaw(uint8_t d[5]) {
    memset(d, 0, 5);
    // Start signal: hold the line low (>= 18 ms for a DHT11), then release.
    pinMode(PIN_DHT, OUTPUT);
    digitalWrite(PIN_DHT, LOW);
    delay(20);
    static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
    int result = kOk;
    // The reply is ~5 ms of microsecond-scale pulses: keep interrupts off
    // on this core while timing them.
    // (Released before the critical section: pinMode may not be called with
    // interrupts off. If we are a little late the reply has simply started.)
    pinMode(PIN_DHT, INPUT_PULLUP);
    portENTER_CRITICAL(&mux);
    if (pulse(HIGH, 300) < 0) {
      result = kNoResponse;  // line never went low: no sensor
    } else if (pulse(LOW, 200) < 0 || pulse(HIGH, 200) < 0) {
      result = kBadTiming;
    } else {
      for (int i = 0; i < 40 && result == kOk; i++) {
        if (pulse(LOW, 150) < 0) {
          result = kBadTiming;
          break;
        }
        int32_t high = pulse(HIGH, 200);
        if (high < 0) {
          result = kBadTiming;
          break;
        }
        // 0 bit: ~27 us high, 1 bit: ~70 us high.
        if (high > 48) d[i / 8] |= (uint8_t)(0x80 >> (i % 8));
      }
    }
    portEXIT_CRITICAL(&mux);
    return result;
  }

  fc::DhtType type_ = fc::DHT_22;
};
