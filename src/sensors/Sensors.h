// Sensor framework: a small interface plus a registry.
//
// Every sensor is probed at boot. A sensor that is not connected stays
// dormant: it produces no readings and no errors. To add a sensor, write a
// class implementing Sensor and add it to the list in Sensors.cpp.
#pragma once

#include <Arduino.h>

// Receives readings from a sensor.
class SensorSink {
 public:
  virtual ~SensorSink() {}
  // sensor: e.g. "bmp280"; metric: e.g. "temp_c" (names fixed by the server contract).
  virtual void add(const char* sensor, const char* metric, float value) = 0;
};

class Sensor {
 public:
  virtual ~Sensor() {}
  // Name for the serial log, e.g. "BMP280/BME280 (I2C)".
  virtual const char* label() const = 0;
  // Look for the hardware. Returns true if it answered. Must be safe to call
  // with nothing connected and may be called again later (re-probe).
  virtual bool probe() = 0;
  // Take one sample and hand the readings to `sink`. Only called while
  // present() is true. Return false if the sensor stopped answering.
  virtual bool sample(SensorSink& sink) = 0;
  // Extra detail for the "sensors" console command.
  virtual void describe(Print& out) { (void)out; }

  bool present() const { return present_; }
  void setPresent(bool p) { present_ = p; }
  uint8_t failures = 0;

 private:
  bool present_ = false;
};

// Probe all enabled sensors. Prints one line per sensor.
void sensorsBegin(Print& log);
// Sample every present sensor.
void sensorsSampleAll(SensorSink& sink, Print& log);
// Probe again for sensors that are not present.
void sensorsReprobe(Print& log);
// Number of sensors currently present.
size_t sensorsPresentCount();
// Print the state of every sensor.
void sensorsPrint(Print& out);

// HX711 scale helpers (EXPERIMENTAL). channel = 1..4.
bool scaleTare(uint8_t channel, Print& out);
bool scaleCalibrate(uint8_t channel, float knownGrams, Print& out);
void scalePrint(Print& out);
