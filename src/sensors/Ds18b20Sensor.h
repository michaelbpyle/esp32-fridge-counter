// DS18B20 one-wire temperature probe (intended for inside the fridge).
// One sensor on the bus, powered from 3V3 (not parasite power), with a 4.7 k
// pull-up resistor from the data line to 3V3.
#pragma once

#include <OneWire.h>

#include <fc_sensor_math.h>

#include "Sensors.h"
#include "config.h"

class Ds18b20Sensor : public Sensor {
 public:
  Ds18b20Sensor() : ow_(PIN_ONEWIRE) {}

  const char* label() const override { return "DS18B20 (1-Wire)"; }

  bool probe() override {
    // Reading the scratchpad is quick and its CRC proves a real sensor is
    // there (a floating pin gives all zeros or all ones, which is rejected).
    uint8_t sp[9];
    float t;
    return readScratchpad(sp) && fc::ds18b20Decode(sp, t);
  }

  bool sample(SensorSink& sink) override {
    float t;
    if (!readTemp(t)) return false;
    sink.add("ds18b20", "fridge_temp_c", t);
    return true;
  }

  void describe(Print& out) override { out.printf("on GPIO%d", PIN_ONEWIRE); }

 private:
  bool readScratchpad(uint8_t sp[9]) {
    if (!ow_.reset()) return false;  // no presence pulse: nothing connected
    ow_.skip();                      // single sensor: address everything
    ow_.write(0xBE);                 // read scratchpad
    for (int i = 0; i < 9; i++) sp[i] = ow_.read();
    return true;
  }

  bool readTemp(float& t) {
    if (!ow_.reset()) return false;
    ow_.skip();
    ow_.write(0x44);                 // start temperature conversion
    delay(760);                      // 12-bit conversion takes up to 750 ms
    uint8_t sp[9];
    if (!readScratchpad(sp) || !fc::ds18b20Decode(sp, t)) return false;
    // 85.0 C is the power-on default: the conversion did not actually run.
    if (sp[0] == 0x50 && sp[1] == 0x05) return false;
    return true;
  }

  OneWire ow_;
};
