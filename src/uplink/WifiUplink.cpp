// WiFi + HTTPS uplink (esp32s3 environment).
#include "config.h"

#if defined(UPLINK_WIFI)

#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "Uplink.h"

// Root certificates: the Mozilla CA bundle that ships inside the ESP32
// Arduino core (compiled into libmbedtls). The server certificate is checked
// against it, so the device accepts hollygrovenola.org whichever public CA
// Cloudflare is using, and rejects impostors.
extern const uint8_t x509_crt_bundle_start[] asm("_binary_x509_crt_bundle_start");
extern const uint8_t x509_crt_bundle_end[] asm("_binary_x509_crt_bundle_end");

namespace {

struct WifiNet {
  const char* ssid;
  const char* password;
};

const WifiNet kNets[] = {
    {WIFI_SSID, WIFI_PASSWORD},
#if defined(WIFI_SSID_2) && defined(WIFI_PASSWORD_2)
    {WIFI_SSID_2, WIFI_PASSWORD_2},
#endif
#if defined(WIFI_SSID_3) && defined(WIFI_PASSWORD_3)
    {WIFI_SSID_3, WIFI_PASSWORD_3},
#endif
};
const size_t kNetCount = sizeof(kNets) / sizeof(kNets[0]);

class WifiUplink : public Uplink {
 public:
  const char* name() const override { return "wifi"; }

  void begin() override {
    WiFi.persistent(false);        // do not write credentials to flash on every connect
    WiFi.mode(WIFI_STA);
    WiFi.setHostname(DEVICE_ID);
    WiFi.setAutoReconnect(true);   // the WiFi driver retries the current network by itself
    // NTP starts as soon as the network is up and re-syncs hourly. UTC only.
    configTime(0, 0, NTP_SERVER_1, NTP_SERVER_2, NTP_SERVER_3);
    startAttempt(0);
  }

  void loop() override {
    bool up = WiFi.status() == WL_CONNECTED;
    if (up && !wasUp_) {
      Serial.printf("[wifi] connected to network %u of %u, IP %s, RSSI %d dBm\n",
                    (unsigned)(netIdx_ + 1), (unsigned)kNetCount,
                    WiFi.localIP().toString().c_str(), (int)WiFi.RSSI());
      reconnects_++;
    } else if (!up && wasUp_) {
      Serial.println("[wifi] connection lost");
      attemptStartMs_ = millis();  // give auto-reconnect a full attempt window
    }
    wasUp_ = up;
    if (!up && millis() - attemptStartMs_ >= WIFI_ATTEMPT_MS) {
      // Not connected within the window: move on to the next configured
      // network (or retry the only one).
      startAttempt((netIdx_ + 1) % kNetCount);
    }
    if (!clockLogged_ && clockEpoch() != 0) {
      clockLogged_ = true;
      Serial.printf("[time] clock set, UTC epoch %lu\n", (unsigned long)clockEpoch());
    }
  }

  bool isConnected() override { return WiFi.status() == WL_CONNECTED; }

  int postJson(const char* path, const std::string& body, std::string& response) override {
    response.clear();
    HTTPClient http;
    http.setConnectTimeout(HTTP_CONNECT_TIMEOUT_MS);
    http.setTimeout(HTTP_RESPONSE_TIMEOUT_MS);
    http.setReuse(false);
    http.setUserAgent("hollygrove-fridge/" FW_VERSION " (esp32s3; wifi)");

#if defined(DEV_HTTP_HOST)
    // Bench mode: plain HTTP to a receiver on the local network.
    WiFiClient client;
    bool ok = http.begin(client, DEV_HTTP_HOST, DEV_HTTP_PORT, path);
#else
    WiFiClientSecure client;
    client.setCACertBundle(x509_crt_bundle_start);
    client.setHandshakeTimeout(HTTP_RESPONSE_TIMEOUT_MS / 1000);
    bool ok = http.begin(client, SERVER_HOST, SERVER_PORT, path, true);
#endif
    if (!ok) return -100;

    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Key", DEVICE_KEY);
    int code = http.POST((uint8_t*)body.data(), body.size());
    if (code == 200) {
      // Only a 200 carries a body we care about (about 80 bytes of JSON).
      // Error pages from proxies can be large, so they are not downloaded.
      int len = http.getSize();  // -1 = chunked / not announced
      if (len <= 2048) response = http.getString().c_str();
    } else if (code <= 0) {
      lastError_ = code;
      Serial.printf("[wifi] POST failed: %s (%d)\n", http.errorToString(code).c_str(), code);
    }
    http.end();
    return code;
  }

  int signalDbm() override { return isConnected() ? (int)WiFi.RSSI() : 0; }

  void printStatus(Print& out) override {
    out.printf("uplink: wifi, %s, network %u of %u, RSSI %d dBm, IP %s, connects %lu\n",
               isConnected() ? "connected" : "NOT connected", (unsigned)(netIdx_ + 1),
               (unsigned)kNetCount, signalDbm(),
               isConnected() ? WiFi.localIP().toString().c_str() : "-", (unsigned long)reconnects_);
#if defined(DEV_HTTP_HOST)
    out.printf("server: DEV MODE plain http://%s:%d%s\n", DEV_HTTP_HOST, (int)DEV_HTTP_PORT,
               SERVER_PATH);
#else
    out.printf("server: https://%s:%d%s (certificate checked against built-in CA bundle)\n",
               SERVER_HOST, (int)SERVER_PORT, SERVER_PATH);
#endif
  }

 private:
  void startAttempt(size_t idx) {
    netIdx_ = idx;
    attemptStartMs_ = millis();
    // Network names and passwords are never printed, only the position of
    // the network in the list in secrets.h.
    Serial.printf("[wifi] trying network %u of %u\n", (unsigned)(idx + 1), (unsigned)kNetCount);
    WiFi.disconnect();
    WiFi.begin(kNets[idx].ssid, kNets[idx].password);
  }

  size_t netIdx_ = 0;
  uint32_t attemptStartMs_ = 0;
  bool wasUp_ = false;
  bool clockLogged_ = false;
  uint32_t reconnects_ = 0;
  int lastError_ = 0;
};

WifiUplink g_wifiUplink;

}  // namespace

Uplink& uplinkInstance() { return g_wifiUplink; }

#endif  // UPLINK_WIFI
