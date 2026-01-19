/*
 * Configuration file for Fridge Door Counter
 * Supports: Pico 2W and ESP32-S3
 *
 * WiFi credentials are in secrets.h (gitignored).
 * Copy secrets.h.example to secrets.h and fill in your values.
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// WiFi & Server Configuration (in secrets.h - gitignored)
// ============================================================================
#include "secrets.h"

// ============================================================================
// Hardware Configuration - Platform-specific
// ============================================================================

#ifdef USE_PICO2W
  // Pico 2W: GP15 (physical pin 20)
  #define REED_SWITCH_PIN 15
  // LED_BUILTIN is defined by arduino-pico core (via WiFi chip)

#elif defined(USE_ESP32S3)
  // ESP32-S3: GPIO4 (safe pin, near GND)
  #define REED_SWITCH_PIN 4
  // Onboard RGB LED on ESP32-S3-DevKitM-1
  #define LED_PIN 48

#else
  #error "No platform defined! Build with pico2w or esp32s3 environment."
#endif

// ============================================================================
// Timing Configuration
// ============================================================================

// Debounce time in milliseconds
// Prevents counting multiple times for a single door open
// Increase if you're getting double-counts
// Decrease if counts are being missed
#define DEBOUNCE_MS 200

// How often to send data to server (milliseconds)
// 0 = send immediately on each door open
// 60000 = send every 60 seconds (1 minute)
// 300000 = send every 5 minutes
#define SEND_INTERVAL_MS 0

// WiFi connection timeout (milliseconds)
#define WIFI_TIMEOUT_MS 10000

#endif // CONFIG_H
