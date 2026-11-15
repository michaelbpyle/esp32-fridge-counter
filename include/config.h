/*
 * Hollygrove Community Fridge door counter - all tunable settings.
 *
 * Secrets (WiFi passwords, device key) are NOT here: they live in secrets.h,
 * which is gitignored. Copy secrets.h.example to secrets.h and fill it in.
 *
 * Every setting can also be overridden from platformio.ini with a build flag
 * (-DNAME=value), which is why each one is wrapped in #ifndef.
 */
#ifndef CONFIG_H
#define CONFIG_H

#include "secrets.h"

#define FW_VERSION "1.0.0"

// ============================================================================
// Uplink selection. Exactly one is chosen by the PlatformIO environment:
//   esp32s3 -> -DUPLINK_WIFI      walter -> -DUPLINK_WALTER
// ============================================================================
#if !defined(UPLINK_WIFI) && !defined(UPLINK_WALTER)
#error "No uplink selected: build with the esp32s3 (WiFi) or walter (LTE-M) environment."
#endif

// ============================================================================
// Server
// ============================================================================
#ifndef SERVER_PORT
#define SERVER_PORT 443
#endif
#ifndef SERVER_PATH
#define SERVER_PATH "/fridge/api/v1/ingest"
#endif
#ifndef HTTP_CONNECT_TIMEOUT_MS
#define HTTP_CONNECT_TIMEOUT_MS 8000
#endif
#ifndef HTTP_RESPONSE_TIMEOUT_MS
#define HTTP_RESPONSE_TIMEOUT_MS 10000
#endif
// Bench testing only: define DEV_HTTP_HOST (and optionally DEV_HTTP_PORT) to
// send plain, unencrypted HTTP to a receiver on the local network instead of
// HTTPS to SERVER_HOST. Never defined in the normal environments; see the
// esp32s3_dev environment in platformio.ini.
#ifndef DEV_HTTP_PORT
#define DEV_HTTP_PORT 8080
#endif

// ============================================================================
// Pins (the same GPIO numbers work on the ESP32-S3-DevKitC-1 style board,
// the Freenove ESP32-S3 WROOM boards and Walter; see docs/wiring/wiring.md)
// ============================================================================
#define PIN_REED 4          // reed switch, other wire to GND
#define PIN_ONEWIRE 5       // DS18B20 data (needs 4.7 k pull-up to 3V3)
#define PIN_DHT 6           // DHT11 / DHT22 data
#define PIN_I2C_SDA 8       // BMP280 / BME280
#define PIN_I2C_SCL 9
#define PIN_HX711_SCK 42    // shared clock for all HX711 boards
#define PIN_HX711_DOUT1 41
#define PIN_HX711_DOUT2 40
#define PIN_HX711_DOUT3 39
#define PIN_HX711_DOUT4 38
// Reserved for the future RS485 (Modbus) link to the solar inverter. The
// firmware does not touch these pins yet; they are listed so nothing else
// gets wired to them.
#define PIN_RS485_DE 16
#define PIN_RS485_TX 17
#define PIN_RS485_RX 18

// Status LED: an addressable WS2812 ("RGB") LED, which needs a data stream,
// not a plain on/off level. It is on GPIO48 on the owner's DevKitC-1 style
// N16R8 boards (confirmed from the factory demo program found on the board)
// and on the Freenove ESP32-S3 WROOM boards. A genuine Espressif DevKitC-1
// v1.1 has it on GPIO38 instead: change STATUS_LED_PIN if you use one.
// Walter has no such LED (GPIO48 goes to its modem), so it is disabled there.
#ifndef STATUS_LED_ENABLED
#if defined(UPLINK_WALTER)
#define STATUS_LED_ENABLED 0
#else
#define STATUS_LED_ENABLED 1
#endif
#endif
#ifndef STATUS_LED_PIN
#define STATUS_LED_PIN 48
#endif
#ifndef STATUS_LED_BRIGHTNESS
#define STATUS_LED_BRIGHTNESS 24   // 0..255; these LEDs are very bright
#endif

// ============================================================================
// Door
// ============================================================================
// Which pin level means "door open". With the switch wired from GPIO4 to GND
// and the internal pull-up on, a switch that is CLOSED while the magnet is
// near (door shut) reads LOW when shut and HIGH when open: that is the bench
// result of 2026-01 and the default (1). If your switch works the other way
// round (closed when the magnet is AWAY), set this to 0. The serial "status"
// command shows the raw pin level so you can check in seconds.
#ifndef DOOR_OPEN_WHEN_HIGH
#define DOOR_OPEN_WHEN_HIGH 1
#endif
// The input must stay in the new state this long before it counts.
#ifndef DOOR_DEBOUNCE_MS
#define DOOR_DEBOUNCE_MS 50
#endif
// How often the door task samples the pin.
#ifndef DOOR_SAMPLE_PERIOD_MS
#define DOOR_SAMPLE_PERIOD_MS 2
#endif
// A door open longer than this is reported once with dur_ms = -1.
#ifndef DOOR_HELD_OPEN_LIMIT_MS
#define DOOR_HELD_OPEN_LIMIT_MS (10UL * 60UL * 1000UL)
#endif

// ============================================================================
// Queue / sending
// ============================================================================
#ifndef EVENT_QUEUE_CAPACITY
#define EVENT_QUEUE_CAPACITY 500   // oldest events are dropped beyond this
#endif
#ifndef MAX_EVENTS_PER_POST
#define MAX_EVENTS_PER_POST 20     // fixed by the server contract
#endif
#ifndef MAX_READINGS_PER_POST
#define MAX_READINGS_PER_POST 40
#endif
// After a door event, wait this long before sending so that a quick
// open-close-open burst goes out as one POST.
#ifndef SEND_COALESCE_MS
#define SEND_COALESCE_MS 3000
#endif
#ifndef HEARTBEAT_INTERVAL_MS
#define HEARTBEAT_INTERVAL_MS (15UL * 60UL * 1000UL)
#endif
// Retry timing when a POST fails.
#ifndef RETRY_BASE_MS
#define RETRY_BASE_MS 5000UL
#endif
#ifndef RETRY_MAX_MS
#define RETRY_MAX_MS (15UL * 60UL * 1000UL)
#endif
// Retry interval after the server rejects the device key (HTTP 401/403).
#ifndef AUTH_RETRY_MS
#define AUTH_RETRY_MS (15UL * 60UL * 1000UL)
#endif

// ============================================================================
// WiFi (esp32s3 environment)
// ============================================================================
// How long to try one network before moving on to the next one in secrets.h.
#ifndef WIFI_ATTEMPT_MS
#define WIFI_ATTEMPT_MS 15000UL
#endif
// WiFi transmit power. At full power (the ESP32 default, about 20 dBm) this DevKitC-style
// board could not join the home network: the access point never answered its
// authentication request (disconnect reason 2, AUTH_EXPIRE), although the network was
// visible at -31 dBm. At 8.5 dBm it joined first time, every time (tested 2026-11-14).
// Lower power costs range; raise it one step at a time if the board is moved far from the
// access point. Values: WIFI_POWER_8_5dBm, WIFI_POWER_11dBm, WIFI_POWER_13dBm,
// WIFI_POWER_15dBm, WIFI_POWER_17dBm, WIFI_POWER_19_5dBm.
#ifndef WIFI_TX_POWER
#define WIFI_TX_POWER WIFI_POWER_8_5dBm
#endif
#define NTP_SERVER_1 "pool.ntp.org"
#define NTP_SERVER_2 "time.cloudflare.com"
#define NTP_SERVER_3 "time.google.com"

// ============================================================================
// Walter / LTE-M (walter environment)
// ============================================================================
#ifndef WALTER_REGISTER_TIMEOUT_MS
#define WALTER_REGISTER_TIMEOUT_MS (5UL * 60UL * 1000UL)
#endif
#ifndef WALTER_HTTP_PROFILE
#define WALTER_HTTP_PROFILE 1
#endif
#ifndef WALTER_TLS_PROFILE
#define WALTER_TLS_PROFILE 2       // profile 1 is reserved for BlueCherry
#endif
#ifndef WALTER_CA_SLOT
#define WALTER_CA_SLOT 12          // modem NVM slot for the root certificate
#endif

// ============================================================================
// Sensors. Each enabled sensor is probed at boot and stays dormant (no
// readings, no errors) if it is not connected. Set to 0 to not even probe.
// ============================================================================
#ifndef SENSOR_BMX280_ENABLED
#define SENSOR_BMX280_ENABLED 1    // BMP280 or BME280 on I2C (0x76 or 0x77)
#endif
#ifndef SENSOR_DS18B20_ENABLED
#define SENSOR_DS18B20_ENABLED 1   // fridge interior temperature
#endif
#ifndef SENSOR_DHT_ENABLED
#define SENSOR_DHT_ENABLED 1       // DHT11 or DHT22
#endif
#ifndef SENSOR_DHT_TYPE
#define SENSOR_DHT_TYPE 0          // 0 = auto-detect, 11 = DHT11, 22 = DHT22
#endif
#ifndef SENSOR_HX711_ENABLED
#define SENSOR_HX711_ENABLED 1     // EXPERIMENTAL shelf scales, up to 4
#endif
#ifndef SENSOR_SAMPLE_INTERVAL_MS
#define SENSOR_SAMPLE_INTERVAL_MS (5UL * 60UL * 1000UL)
#endif
// Look again for sensors that were not found at boot (0 = never).
#ifndef SENSOR_REPROBE_INTERVAL_MS
#define SENSOR_REPROBE_INTERVAL_MS (60UL * 60UL * 1000UL)
#endif

// ============================================================================
// Reliability
// ============================================================================
// If the main loop or the door task stops running for this long, the chip
// resets itself. Must be longer than the slowest network operation.
#ifndef WATCHDOG_TIMEOUT_S
#define WATCHDOG_TIMEOUT_S 120
#endif
#define SERIAL_BAUD 115200

#endif  // CONFIG_H
