#include "Sensors.h"

#include <Wire.h>

#include "config.h"

#if SENSOR_BMX280_ENABLED
#include "Bmx280Sensor.h"
#endif
#if SENSOR_DS18B20_ENABLED
#include "Ds18b20Sensor.h"
#endif
#if SENSOR_DHT_ENABLED
#include "DhtSensor.h"
#endif
#if SENSOR_HX711_ENABLED
#include "Hx711Sensor.h"
#endif

namespace {

#if SENSOR_BMX280_ENABLED
Bmx280Sensor g_bmx;
#endif
#if SENSOR_DS18B20_ENABLED
Ds18b20Sensor g_ds18b20;
#endif
#if SENSOR_DHT_ENABLED
DhtSensor g_dht;
#endif
#if SENSOR_HX711_ENABLED
Hx711Sensor g_hx711;
#endif

// The registry: add new sensors here.
Sensor* const kSensors[] = {
#if SENSOR_BMX280_ENABLED
    &g_bmx,
#endif
#if SENSOR_DS18B20_ENABLED
    &g_ds18b20,
#endif
#if SENSOR_DHT_ENABLED
    &g_dht,
#endif
#if SENSOR_HX711_ENABLED
    &g_hx711,
#endif
    nullptr,  // keeps the array non-empty when every sensor is disabled
};
const size_t kSensorCount = sizeof(kSensors) / sizeof(kSensors[0]) - 1;

const uint8_t kMaxFailures = 3;  // consecutive failed samples before going dormant

void probeOne(Sensor* s, Print& log, bool quietIfAbsent) {
  bool found = s->probe();
  s->setPresent(found);
  s->failures = 0;
  if (found) {
    log.printf("[sensor] %s: FOUND (", s->label());
    s->describe(log);
    log.println(")");
  } else if (!quietIfAbsent) {
    log.printf("[sensor] %s: not connected (dormant)\n", s->label());
  }
}

}  // namespace

void sensorsBegin(Print& log) {
#if SENSOR_BMX280_ENABLED
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000U);
  Wire.setTimeOut(50);
#endif
  // DHT sensors need about a second after power-up before they answer.
  while (millis() < 1200) delay(10);
  for (size_t i = 0; i < kSensorCount; i++) probeOne(kSensors[i], log, false);
}

void sensorsSampleAll(SensorSink& sink, Print& log) {
  for (size_t i = 0; i < kSensorCount; i++) {
    Sensor* s = kSensors[i];
    if (!s->present()) continue;
    if (s->sample(sink)) {
      s->failures = 0;
    } else if (++s->failures >= kMaxFailures) {
      // Unplugged or broken: go dormant instead of logging forever. The
      // periodic re-probe will pick it up again if it comes back.
      s->setPresent(false);
      log.printf("[sensor] %s: stopped answering, now dormant\n", s->label());
    } else {
      log.printf("[sensor] %s: read failed (%u of %u)\n", s->label(), (unsigned)s->failures,
                 (unsigned)kMaxFailures);
    }
  }
}

void sensorsReprobe(Print& log) {
  for (size_t i = 0; i < kSensorCount; i++) {
    if (!kSensors[i]->present()) probeOne(kSensors[i], log, true);
  }
}

size_t sensorsPresentCount() {
  size_t n = 0;
  for (size_t i = 0; i < kSensorCount; i++) {
    if (kSensors[i]->present()) n++;
  }
  return n;
}

void sensorsPrint(Print& out) {
  if (kSensorCount == 0) out.println("sensors: all disabled in config.h");
  for (size_t i = 0; i < kSensorCount; i++) {
    Sensor* s = kSensors[i];
    out.printf("sensor: %s: ", s->label());
    if (s->present()) {
      out.print("present, ");
      s->describe(out);
      out.println();
    } else {
      out.println("not connected (dormant)");
    }
  }
}

#if SENSOR_HX711_ENABLED
bool scaleTare(uint8_t channel, Print& out) { return g_hx711.tare(channel, out); }
bool scaleCalibrate(uint8_t channel, float knownGrams, Print& out) {
  return g_hx711.calibrate(channel, knownGrams, out);
}
void scalePrint(Print& out) { g_hx711.printAll(out); }
#else
bool scaleTare(uint8_t, Print& out) {
  out.println("scale: HX711 support is disabled in config.h");
  return false;
}
bool scaleCalibrate(uint8_t, float, Print& out) {
  out.println("scale: HX711 support is disabled in config.h");
  return false;
}
void scalePrint(Print& out) { out.println("scale: HX711 support is disabled in config.h"); }
#endif
