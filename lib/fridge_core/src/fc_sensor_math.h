// Pure conversion maths for the supported sensors (unit-testable).
#pragma once

#include <stdint.h>

namespace fc {

// ---- Bosch BMP280 / BME280 -------------------------------------------------
struct Bmx280Calib {
  uint16_t T1; int16_t T2, T3;
  uint16_t P1; int16_t P2, P3, P4, P5, P6, P7, P8, P9;
  uint8_t H1; int16_t H2; uint8_t H3; int16_t H4, H5; int8_t H6;  // BME280 only
};

// Parse the 24 calibration bytes read from register 0x88 (T1..P9).
void bmx280ParseTP(const uint8_t* b24, Bmx280Calib& c);
// Parse humidity calibration: h1 = register 0xA1, b7 = registers 0xE1..0xE7.
void bmx280ParseH(uint8_t h1, const uint8_t* b7, Bmx280Calib& c);

// Datasheet compensation formulas (floating point version).
// tFine is produced by the temperature call and consumed by the other two.
double bmx280TempC(int32_t adcT, const Bmx280Calib& c, double& tFine);
double bmx280PressurePa(int32_t adcP, const Bmx280Calib& c, double tFine);
double bme280HumidityPct(int32_t adcH, const Bmx280Calib& c, double tFine);

// ---- DHT11 / DHT22 ---------------------------------------------------------
enum DhtType { DHT_AUTO = 0, DHT_11 = 11, DHT_22 = 22 };
// Decode the 5 data bytes. Returns the detected type (DHT_11/DHT_22) or
// DHT_AUTO (0) if the checksum is wrong or the values are implausible.
DhtType dhtDecode(const uint8_t b[5], DhtType forced, float& tempC, float& humPct);

// ---- DS18B20 ---------------------------------------------------------------
uint8_t crc8Dallas(const uint8_t* data, int len);
// Convert a 9-byte scratchpad to degrees C. Returns false on CRC error or an
// all-zero/all-ones scratchpad (no sensor).
bool ds18b20Decode(const uint8_t sp[9], float& tempC);

// ---- HX711 -----------------------------------------------------------------
inline int32_t hx711SignExtend(uint32_t raw24) {
  return (raw24 & 0x800000UL) ? (int32_t)(raw24 | 0xFF000000UL) : (int32_t)raw24;
}
// countsPerGram == 0 means "not calibrated" (returns false).
bool hx711ToGrams(int32_t raw, int32_t tareOffset, float countsPerGram, float& grams);

}  // namespace fc
