#include "fc_sensor_math.h"

namespace fc {

namespace {
uint16_t u16le(const uint8_t* p) { return (uint16_t)(p[0] | (p[1] << 8)); }
int16_t s16le(const uint8_t* p) { return (int16_t)u16le(p); }
}  // namespace

void bmx280ParseTP(const uint8_t* b, Bmx280Calib& c) {
  c.T1 = u16le(b + 0);
  c.T2 = s16le(b + 2);
  c.T3 = s16le(b + 4);
  c.P1 = u16le(b + 6);
  c.P2 = s16le(b + 8);
  c.P3 = s16le(b + 10);
  c.P4 = s16le(b + 12);
  c.P5 = s16le(b + 14);
  c.P6 = s16le(b + 16);
  c.P7 = s16le(b + 18);
  c.P8 = s16le(b + 20);
  c.P9 = s16le(b + 22);
}

void bmx280ParseH(uint8_t h1, const uint8_t* b, Bmx280Calib& c) {
  c.H1 = h1;
  c.H2 = s16le(b + 0);
  c.H3 = b[2];
  // H4 and H5 are 12-bit signed values sharing register 0xE5.
  c.H4 = (int16_t)(((int16_t)(int8_t)b[3] << 4) | (b[4] & 0x0F));
  c.H5 = (int16_t)(((int16_t)(int8_t)b[5] << 4) | (b[4] >> 4));
  c.H6 = (int8_t)b[6];
}

double bmx280TempC(int32_t adcT, const Bmx280Calib& c, double& tFine) {
  double var1 = ((double)adcT / 16384.0 - (double)c.T1 / 1024.0) * (double)c.T2;
  double var2 = ((double)adcT / 131072.0 - (double)c.T1 / 8192.0);
  var2 = var2 * var2 * (double)c.T3;
  tFine = var1 + var2;
  return tFine / 5120.0;
}

double bmx280PressurePa(int32_t adcP, const Bmx280Calib& c, double tFine) {
  double var1 = tFine / 2.0 - 64000.0;
  double var2 = var1 * var1 * (double)c.P6 / 32768.0;
  var2 = var2 + var1 * (double)c.P5 * 2.0;
  var2 = var2 / 4.0 + (double)c.P4 * 65536.0;
  var1 = ((double)c.P3 * var1 * var1 / 524288.0 + (double)c.P2 * var1) / 524288.0;
  var1 = (1.0 + var1 / 32768.0) * (double)c.P1;
  if (var1 == 0.0) return 0.0;  // avoid division by zero (bad calibration)
  double p = 1048576.0 - (double)adcP;
  p = (p - var2 / 4096.0) * 6250.0 / var1;
  var1 = (double)c.P9 * p * p / 2147483648.0;
  var2 = p * (double)c.P8 / 32768.0;
  return p + (var1 + var2 + (double)c.P7) / 16.0;
}

double bme280HumidityPct(int32_t adcH, const Bmx280Calib& c, double tFine) {
  double h = tFine - 76800.0;
  h = ((double)adcH - ((double)c.H4 * 64.0 + (double)c.H5 / 16384.0 * h)) *
      ((double)c.H2 / 65536.0 *
       (1.0 + (double)c.H6 / 67108864.0 * h * (1.0 + (double)c.H3 / 67108864.0 * h)));
  h = h * (1.0 - (double)c.H1 * h / 524288.0);
  if (h > 100.0) h = 100.0;
  if (h < 0.0) h = 0.0;
  return h;
}

DhtType dhtDecode(const uint8_t b[5], DhtType forced, float& tempC, float& humPct) {
  uint8_t sum = (uint8_t)(b[0] + b[1] + b[2] + b[3]);
  if (sum != b[4]) return DHT_AUTO;
  if ((b[0] | b[1] | b[2] | b[3]) == 0) return DHT_AUTO;  // all zero: no real data

  DhtType type = forced;
  if (type == DHT_AUTO) {
    // DHT22 sends humidity*10 as 16 bits, so its first byte is at most 3
    // (1000 = 0x03E8). A DHT11 sends whole-percent humidity (20..90) there.
    type = (b[0] > 3) ? DHT_11 : DHT_22;
  }
  if (type == DHT_11) {
    humPct = (float)b[0] + (float)b[1] * 0.1f;
    tempC = (float)b[2] + (float)(b[3] & 0x7F) * 0.1f;
    if (b[3] & 0x80) tempC = -tempC;
  } else {
    humPct = (float)(((uint16_t)b[0] << 8) | b[1]) * 0.1f;
    tempC = (float)((((uint16_t)b[2] & 0x7F) << 8) | b[3]) * 0.1f;
    if (b[2] & 0x80) tempC = -tempC;
  }
  if (humPct > 100.0f || tempC < -40.0f || tempC > 80.0f) return DHT_AUTO;
  return type;
}

uint8_t crc8Dallas(const uint8_t* data, int len) {
  uint8_t crc = 0;
  for (int i = 0; i < len; i++) {
    uint8_t in = data[i];
    for (int b = 0; b < 8; b++) {
      uint8_t mix = (uint8_t)((crc ^ in) & 0x01);
      crc >>= 1;
      if (mix) crc ^= 0x8C;
      in >>= 1;
    }
  }
  return crc;
}

bool ds18b20Decode(const uint8_t sp[9], float& tempC) {
  bool allZero = true, allOnes = true;
  for (int i = 0; i < 9; i++) {
    if (sp[i] != 0x00) allZero = false;
    if (sp[i] != 0xFF) allOnes = false;
  }
  if (allZero || allOnes) return false;
  if (crc8Dallas(sp, 8) != sp[8]) return false;
  int16_t raw = (int16_t)((uint16_t)sp[0] | ((uint16_t)sp[1] << 8));
  tempC = (float)raw / 16.0f;
  return true;
}

bool hx711ToGrams(int32_t raw, int32_t tareOffset, float countsPerGram, float& grams) {
  if (countsPerGram == 0.0f) return false;
  grams = (float)((double)(raw - tareOffset) / (double)countsPerGram);
  return true;
}

}  // namespace fc
