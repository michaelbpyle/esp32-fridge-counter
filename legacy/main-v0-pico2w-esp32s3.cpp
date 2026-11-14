/*
 * Community Fridge Door Counter
 * Supports: Raspberry Pi Pico 2W and ESP32-S3-DevKitM-1
 *
 * Counts the number of times a refrigerator door is opened using a reed switch.
 * Transmits the count via WiFi.
 *
 * Hardware:
 *   - Pico 2W or ESP32-S3-DevKitM-1
 *   - Reed switch (normally open) connected to GPIO and GND
 *
 * Wiring (Pico 2W):
 *   Reed Switch Wire 1 → GND (pin 38)
 *   Reed Switch Wire 2 → GP15 (pin 20)
 *
 * Wiring (ESP32-S3):
 *   Reed Switch Wire 1 → GND (right side, near USB)
 *   Reed Switch Wire 2 → GPIO4 (right side, near bottom)
 *
 * How it works:
 *   - Reed switch is CLOSED when magnet is near (door closed)
 *   - Reed switch is OPEN when magnet is away (door open)
 *   - We use INPUT_PULLUP, so:
 *     - Door closed (switch closed) = GPIO reads LOW
 *     - Door open (switch open) = GPIO reads HIGH (pulled up internally)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"

// ============================================================================
// Platform-specific LED pin
// ============================================================================
#ifdef USE_PICO2W
  // Pico W/2W: LED_BUILTIN is defined by arduino-pico core
  #define STATUS_LED LED_BUILTIN
  #define PLATFORM_NAME "Pico 2W"
#elif defined(USE_ESP32S3)
  // ESP32-S3-DevKitM-1: GPIO48 RGB LED
  #define STATUS_LED LED_PIN
  #define PLATFORM_NAME "ESP32-S3"
#endif

// ============================================================================
// Global Variables
// ============================================================================

// Door open counter - how many times has the door been opened?
unsigned long doorOpenCount = 0;

// Track the previous state of the reed switch for edge detection
bool lastDoorState = false;  // false = closed, true = open

// Debounce tracking
unsigned long lastStateChangeTime = 0;

// For periodic sending
unsigned long lastSendTime = 0;

// ============================================================================
// Function Declarations
// ============================================================================

void connectToWiFi();
void sendCountToServer();
void blinkLED(int times, int delayMs);
void setLED(bool on);

// ============================================================================
// Setup - Runs once at startup
// ============================================================================

void setup() {
  // Initialize serial communication for debugging
  Serial.begin(115200);

  // Wait a moment for serial to initialize
  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println("  Community Fridge Door Counter");
  Serial.printf("  Platform: %s\n", PLATFORM_NAME);
  Serial.println("================================");
  Serial.println();

  // Configure the reed switch pin
  // INPUT_PULLUP means:
  //   - Pin is configured as an input
  //   - Internal pull-up resistor is enabled
  //   - Pin reads HIGH when switch is open (door open)
  //   - Pin reads LOW when switch is closed (door closed)
  pinMode(REED_SWITCH_PIN, INPUT_PULLUP);
  Serial.printf("Reed switch on GPIO %d\n", REED_SWITCH_PIN);

  // Configure onboard LED for visual feedback
  pinMode(STATUS_LED, OUTPUT);
  setLED(false);

  // Read initial door state
  lastDoorState = digitalRead(REED_SWITCH_PIN) == HIGH;
  Serial.printf("Initial door state: %s\n", lastDoorState ? "OPEN" : "CLOSED");

  // Connect to WiFi
  connectToWiFi();

  Serial.println();
  Serial.println("Door counter ready!");
  Serial.printf("Current count: %lu\n", doorOpenCount);
  Serial.println();
  Serial.println("Monitoring door...");
  Serial.println("---------------------------------");

  // Blink LED to indicate ready
  blinkLED(3, 200);
}

// ============================================================================
// Main Loop - Runs repeatedly
// ============================================================================

void loop() {
  // Read the current state of the reed switch
  // HIGH = door open (switch open, pulled up)
  // LOW = door closed (switch closed, connected to GND)
  bool currentDoorState = digitalRead(REED_SWITCH_PIN) == HIGH;

  // Get current time for debouncing
  unsigned long currentTime = millis();

  // Check if enough time has passed since last state change (debounce)
  if (currentTime - lastStateChangeTime >= DEBOUNCE_MS) {

    // Detect door opening (state changed from closed to open)
    if (currentDoorState && !lastDoorState) {
      // Door just opened!
      doorOpenCount++;
      lastStateChangeTime = currentTime;

      Serial.printf("Door OPENED! Count: %lu\n", doorOpenCount);

      // Visual feedback - turn on LED briefly
      setLED(true);

      // Send to server immediately if configured
      #if SEND_INTERVAL_MS == 0
      if (strlen(SERVER_URL) > 0) {
        sendCountToServer();
      }
      #endif

      // Turn off LED
      delay(100);
      setLED(false);
    }

    // Detect door closing (state changed from open to closed)
    else if (!currentDoorState && lastDoorState) {
      lastStateChangeTime = currentTime;
      Serial.println("Door closed.");
    }

    // Update the last known state
    lastDoorState = currentDoorState;
  }

  // Periodic sending (if configured)
  #if SEND_INTERVAL_MS > 0
  if (strlen(SERVER_URL) > 0 && currentTime - lastSendTime >= SEND_INTERVAL_MS) {
    sendCountToServer();
    lastSendTime = currentTime;
  }
  #endif

  // Small delay to prevent CPU hogging
  delay(10);
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Set the onboard LED state
 */
void setLED(bool on) {
  digitalWrite(STATUS_LED, on ? HIGH : LOW);
}

/**
 * Connect to WiFi network
 * Retries until connected or timeout
 */
void connectToWiFi() {
  Serial.printf("Connecting to WiFi: %s", WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");

    // Check for timeout
    if (millis() - startTime > WIFI_TIMEOUT_MS) {
      Serial.println();
      Serial.println("WiFi connection FAILED!");
      Serial.println("Continuing without WiFi - counting will still work.");
      Serial.println("Check your SSID and password in include/config.h");
      return;
    }
  }

  Serial.println();
  Serial.println("WiFi connected!");
  Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
}

/**
 * Send the current count to a server via HTTP POST
 */
void sendCountToServer() {
  if (strlen(SERVER_URL) == 0) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping send.");
    return;
  }

  Serial.printf("Sending count to server: %lu\n", doorOpenCount);

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload
  String payload = "{\"count\":" + String(doorOpenCount) + ",\"device\":\"fridge-counter-" PLATFORM_NAME "\"}";

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.printf("Server response: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK) {
      String response = http.getString();
      Serial.printf("Response: %s\n", response.c_str());
    }
  } else {
    Serial.printf("HTTP error: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
}

/**
 * Blink the onboard LED
 */
void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    setLED(true);
    delay(delayMs);
    setLED(false);
    delay(delayMs);
  }
}
