// Bosch BMP280 (temperature + pressure) or BME280 (+ humidity) on I2C.
// Both chips are handled by one driver: the chip-ID register says which one
// is fitted, at address 0x76 or 0x77.
#pragma once

#include <Wire.h>

#include <fc_sensor_math.h>

#include "Sensors.h"

class Bmx280Sensor : public Sensor {
 public:
  const char* label() const override { return "BMP280/BME280 (I2C)"; }

  bool probe() override {
    const uint8_t addrs[] = {0x76, 0x77};
    for (uint8_t a : addrs) {
      // Address-only probe first: quiet when nothing is connected.
      Wire.beginTransmission(a);
      if (Wire.endTransmission() != 0) continue;
      uint8_t id = 0;
      if (!readRegs(a, 0xD0, &id, 1)) continue;
      bool bme = (id == 0x60);
      bool bmp = (id == 0x58 || id == 0x56 || id == 0x57);
      if (!bme && !bmp) continue;
      addr_ = a;
      isBme_ = bme;
      writeReg(0xE0, 0xB6);  // soft reset
      delay(5);
      uint8_t tp[24];
      if (!readRegs(a, 0x88, tp, sizeof(tp))) continue;
      fc::bmx280ParseTP(tp, cal_);
      if (bme) {
        uint8_t h1 = 0, h[7];
        if (!readRegs(a, 0xA1, &h1, 1) || !readRegs(a, 0xE1, h, sizeof(h))) continue;
        fc::bmx280ParseH(h1, h, cal_);
      }
      writeReg(0xF5, 0x00);  // no IIR filter, no standby: one-shot use
      return true;
    }
    return false;
  }

  bool sample(SensorSink& sink) override {
    if (isBme_ && !writeReg(0xF2, 0x01)) return false;  // humidity oversampling x1
    if (!writeReg(0xF4, 0x25)) return false;            // temp x1, pressure x1, forced mode
    delay(15);                                          // conversion takes < 10 ms
    uint8_t d[8] = {0};
    if (!readRegs(addr_, 0xF7, d, isBme_ ? 8 : 6)) return false;
    int32_t adcP = ((int32_t)d[0] << 12) | ((int32_t)d[1] << 4) | (d[2] >> 4);
    int32_t adcT = ((int32_t)d[3] << 12) | ((int32_t)d[4] << 4) | (d[5] >> 4);
    if (adcT == 0x80000 || adcP == 0x80000) return false;  // "measurement skipped" marker
    double tFine = 0;
    double t = fc::bmx280TempC(adcT, cal_, tFine);
    double p = fc::bmx280PressurePa(adcP, cal_, tFine) / 100.0;
    if (t < -45 || t > 90 || p < 300 || p > 1100) return false;  // outside the chip's range
    const char* name = isBme_ ? "bme280" : "bmp280";
    sink.add(name, "temp_c", (float)t);
    sink.add(name, "pressure_hpa", (float)p);
    if (isBme_) {
      int32_t adcH = ((int32_t)d[6] << 8) | d[7];
      if (adcH != 0x8000) sink.add(name, "humidity_pct", (float)fc::bme280HumidityPct(adcH, cal_, tFine));
    }
    return true;
  }

  void describe(Print& out) override {
    out.printf("%s at I2C address 0x%02X", isBme_ ? "BME280" : "BMP280", addr_);
  }

 private:
  bool readRegs(uint8_t addr, uint8_t reg, uint8_t* buf, size_t len) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom((int)addr, (int)len) != (int)len) return false;
    for (size_t i = 0; i < len; i++) buf[i] = (uint8_t)Wire.read();
    return true;
  }
  bool writeReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(addr_);
    Wire.write(reg);
    Wire.write(val);
    return Wire.endTransmission() == 0;
  }

  uint8_t addr_ = 0x76;
  bool isBme_ = false;
  fc::Bmx280Calib cal_ = {};
};
