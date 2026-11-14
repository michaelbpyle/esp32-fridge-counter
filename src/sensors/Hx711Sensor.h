// HX711 load-cell amplifiers for shelf scales - EXPERIMENTAL.
//
// Up to four HX711 boards share one clock pin (SCK) and have one data pin
// (DOUT) each. All boards are clocked together and their data bits are read
// in parallel. Raw readings are converted to grams with a tare offset and a
// counts-per-gram factor stored in NVS (set with the "tare" and "cal"
// console commands). A channel that has not been calibrated sends nothing.
//
// Not yet tested against real hardware: treat the numbers with suspicion
// until a known weight has been checked on each shelf.
#pragma once

#include <Preferences.h>

#include <fc_sensor_math.h>

#include "Sensors.h"
#include "config.h"

class Hx711Sensor : public Sensor {
 public:
  static const int kChannels = 4;

  const char* label() const override { return "HX711 scales (experimental)"; }

  bool probe() override {
    pinMode(PIN_HX711_SCK, OUTPUT);
    digitalWrite(PIN_HX711_SCK, LOW);  // low = powered up
    for (int i = 0; i < kChannels; i++) {
      pinMode(pins_[i], INPUT_PULLUP);
      found_[i] = false;
    }
    // A powered HX711 pulls DOUT low when a conversion is ready (within
    // ~0.5 s of power-up). With nothing connected the pull-up keeps it high.
    uint32_t start = millis();
    bool any = false;
    while (millis() - start < 700) {
      for (int i = 0; i < kChannels; i++) {
        if (!found_[i] && digitalRead(pins_[i]) == LOW) {
          found_[i] = true;
          any = true;
        }
      }
      delay(5);
    }
    if (any) loadCalibration();
    return any;
  }

  bool sample(SensorSink& sink) override {
    int32_t raw[kChannels];
    bool ok[kChannels];
    if (!readAveraged(raw, ok, 4)) return false;
    for (int i = 0; i < kChannels; i++) {
      lastRaw_[i] = raw[i];
      lastOk_[i] = ok[i];
      float grams;
      if (found_[i] && ok[i] && fc::hx711ToGrams(raw[i], offset_[i], countsPerGram_[i], grams)) {
        char name[12];
        snprintf(name, sizeof(name), "hx711_%d", i + 1);
        sink.add(name, "weight_g", grams);
      }
    }
    return true;
  }

  void describe(Print& out) override {
    out.print("channels:");
    for (int i = 0; i < kChannels; i++) {
      if (found_[i]) out.printf(" %d(GPIO%d)", i + 1, pins_[i]);
    }
  }

  bool tare(int ch, Print& out) {
    if (!channelUsable(ch, out)) return false;
    int32_t raw[kChannels];
    bool ok[kChannels];
    if (!readAveraged(raw, ok, 10) || !ok[ch - 1]) {
      out.println("scale: no reading from that channel");
      return false;
    }
    offset_[ch - 1] = raw[ch - 1];
    saveCalibration(ch);
    out.printf("scale %d: tare offset set to %ld\n", ch, (long)offset_[ch - 1]);
    return true;
  }

  bool calibrate(int ch, float knownGrams, Print& out) {
    if (!channelUsable(ch, out)) return false;
    if (knownGrams <= 0) {
      out.println("scale: the known weight must be a positive number of grams");
      return false;
    }
    int32_t raw[kChannels];
    bool ok[kChannels];
    if (!readAveraged(raw, ok, 10) || !ok[ch - 1]) {
      out.println("scale: no reading from that channel");
      return false;
    }
    float cpg = (float)(raw[ch - 1] - offset_[ch - 1]) / knownGrams;
    if (cpg == 0.0f) {
      out.println("scale: reading did not change from the tare value; is the weight on the shelf?");
      return false;
    }
    countsPerGram_[ch - 1] = cpg;
    saveCalibration(ch);
    out.printf("scale %d: %.3f counts per gram\n", ch, cpg);
    return true;
  }

  void printAll(Print& out) {
    for (int i = 0; i < kChannels; i++) {
      out.printf("scale %d: %s, DOUT GPIO%d, tare %ld, counts/gram %.3f%s, last raw %ld%s\n", i + 1,
                 found_[i] ? "present" : "not connected", pins_[i], (long)offset_[i],
                 countsPerGram_[i], countsPerGram_[i] == 0.0f ? " (not calibrated)" : "",
                 (long)lastRaw_[i], lastOk_[i] ? "" : " (no data)");
    }
  }

 private:
  bool channelUsable(int ch, Print& out) {
    if (ch < 1 || ch > kChannels) {
      out.println("scale: channel must be 1 to 4");
      return false;
    }
    if (!present() || !found_[ch - 1]) {
      out.printf("scale %d: no HX711 detected on that channel\n", ch);
      return false;
    }
    return true;
  }

  // One 24-bit conversion from every board at once.
  bool readOnce(int32_t raw[kChannels], bool ok[kChannels]) {
    // Wait until every detected board has data ready (DOUT low).
    uint32_t start = millis();
    bool ready[kChannels];
    for (;;) {
      bool all = true;
      for (int i = 0; i < kChannels; i++) {
        ready[i] = found_[i] && digitalRead(pins_[i]) == LOW;
        if (found_[i] && !ready[i]) all = false;
      }
      if (all || millis() - start > 250) break;
      delay(1);
    }
    uint32_t value[kChannels] = {0, 0, 0, 0};
    static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
    // SCK must never stay high for 60 us or the chips power down, so the
    // bit-banging runs with interrupts off (about 100 us in total).
    portENTER_CRITICAL(&mux);
    for (int bit = 0; bit < 24; bit++) {
      digitalWrite(PIN_HX711_SCK, HIGH);
      delayMicroseconds(1);
      for (int i = 0; i < kChannels; i++) {
        value[i] = (value[i] << 1) | (digitalRead(pins_[i]) ? 1U : 0U);
      }
      digitalWrite(PIN_HX711_SCK, LOW);
      delayMicroseconds(1);
    }
    // 25th pulse: next conversion uses channel A, gain 128.
    digitalWrite(PIN_HX711_SCK, HIGH);
    delayMicroseconds(1);
    digitalWrite(PIN_HX711_SCK, LOW);
    portEXIT_CRITICAL(&mux);

    bool any = false;
    for (int i = 0; i < kChannels; i++) {
      // All ones = line stuck high (no chip); the two extremes = amplifier saturated.
      ok[i] = ready[i] && value[i] != 0xFFFFFF && value[i] != 0x7FFFFF && value[i] != 0x800000;
      raw[i] = fc::hx711SignExtend(value[i]);
      any = any || ok[i];
    }
    return any;
  }

  bool readAveraged(int32_t raw[kChannels], bool ok[kChannels], int samples) {
    int64_t sum[kChannels] = {0, 0, 0, 0};
    int n[kChannels] = {0, 0, 0, 0};
    for (int s = 0; s < samples; s++) {
      int32_t r[kChannels];
      bool o[kChannels];
      if (!readOnce(r, o)) continue;
      for (int i = 0; i < kChannels; i++) {
        if (o[i]) {
          sum[i] += r[i];
          n[i]++;
        }
      }
    }
    bool any = false;
    for (int i = 0; i < kChannels; i++) {
      ok[i] = n[i] > 0;
      raw[i] = ok[i] ? (int32_t)(sum[i] / n[i]) : 0;
      any = any || ok[i];
    }
    return any;
  }

  void loadCalibration() {
    Preferences p;
    if (!p.begin("scale", true)) return;  // nothing stored yet
    for (int i = 0; i < kChannels; i++) {
      char k[8];
      snprintf(k, sizeof(k), "off%d", i + 1);
      offset_[i] = p.getInt(k, 0);
      snprintf(k, sizeof(k), "cpg%d", i + 1);
      countsPerGram_[i] = p.getFloat(k, 0.0f);
    }
    p.end();
  }

  void saveCalibration(int ch) {
    Preferences p;
    if (!p.begin("scale", false)) return;
    char k[8];
    snprintf(k, sizeof(k), "off%d", ch);
    p.putInt(k, offset_[ch - 1]);
    snprintf(k, sizeof(k), "cpg%d", ch);
    p.putFloat(k, countsPerGram_[ch - 1]);
    p.end();
  }

  const uint8_t pins_[kChannels] = {PIN_HX711_DOUT1, PIN_HX711_DOUT2, PIN_HX711_DOUT3,
                                    PIN_HX711_DOUT4};
  bool found_[kChannels] = {false, false, false, false};
  int32_t offset_[kChannels] = {0, 0, 0, 0};
  float countsPerGram_[kChannels] = {0, 0, 0, 0};
  int32_t lastRaw_[kChannels] = {0, 0, 0, 0};
  bool lastOk_[kChannels] = {false, false, false, false};
};
