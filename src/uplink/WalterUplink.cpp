// LTE-M uplink for the DPTechnics / QuickSpot "Walter" board (ESP32-S3 +
// Sequans GM02SP modem), using the official WalterModem library.
//
// The modem does TCP, TLS and HTTP itself; the ESP32 only hands it the body.
//
// STATUS: compiles against WalterModem 1.6.1 (pio run -e walter, 2026-11-14),
// but has never run on a real Walter (none was available). Treat it as
// untested until it has.
#include "config.h"

#if defined(UPLINK_WALTER)

#include <HardwareSerial.h>
#include <Preferences.h>
#include <WalterModem.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

#include "Uplink.h"
#include "walter_ca.h"

namespace {

WalterModem modem;

// Filled in by the modem library's event task, read by postJson().
SemaphoreHandle_t g_httpDone = nullptr;
volatile bool g_httpFailed = false;
volatile uint16_t g_httpStatus = 0;
volatile uint16_t g_httpLen = 0;
volatile uint8_t g_httpRc = 0;

void httpEventHandler(WMHTTPEventType event, const WMHTTPEventData* data, void*) {
  if (data->profile_id != WALTER_HTTP_PROFILE) return;
  switch (event) {
    case WALTER_MODEM_HTTP_EVENT_RING:
      // The server answered: status and body length are known, the body is
      // fetched by postJson() (keep this handler short).
      g_httpStatus = data->status;
      g_httpLen = data->data_len;
      g_httpFailed = false;
      xSemaphoreGive(g_httpDone);
      break;
    case WALTER_MODEM_HTTP_EVENT_CONNECTED:
      if (data->rc != 0) {
        g_httpRc = data->rc;
        g_httpFailed = true;
        xSemaphoreGive(g_httpDone);
      }
      break;
    case WALTER_MODEM_HTTP_EVENT_CONNECTION_CLOSED:
      g_httpRc = data->rc;
      g_httpFailed = true;
      xSemaphoreGive(g_httpDone);
      break;
    default:
      break;
  }
}

class WalterUplink : public Uplink {
 public:
  const char* name() const override { return "lte-m"; }

  void begin() override {
    g_httpDone = xSemaphoreCreateBinary();
    if (!WalterModem::begin(&Serial2)) {
      Serial.println("[lte] ERROR: modem did not start");
      return;
    }
    modemOk_ = true;
    modem.setHTTPEventHandler(httpEventHandler, nullptr);
    Serial.println("[lte] modem started");
    configured_ = configureProfiles();
    startRegistration();
  }

  void loop() override {
    if (!modemOk_) return;
    uint32_t now = millis();
    if (now - lastCheckMs_ < 2000) return;
    lastCheckMs_ = now;

    if (!configured_) configured_ = configureProfiles();

    bool reg = registered();
    if (reg && !wasRegistered_) {
      Serial.println("[lte] registered on the network");
      syncClockFromNetwork();
      refreshSignal();
    } else if (!reg && wasRegistered_) {
      Serial.println("[lte] registration lost");
      regStartMs_ = now;
    }
    wasRegistered_ = reg;

    if (reg) {
      if (now - lastSignalMs_ > 60000) refreshSignal();
    } else if (now - regStartMs_ > WALTER_REGISTER_TIMEOUT_MS) {
      // No network for a long time: restart the attach sequence, and every
      // third time reset the modem as well.
      Serial.println("[lte] not registered, restarting the attach sequence");
      if (++regFailures_ % 3 == 0) {
        Serial.println("[lte] resetting the modem");
        modem.reset();
        configured_ = configureProfiles();
      }
      startRegistration();
    }
  }

  bool isConnected() override { return modemOk_ && configured_ && registered(); }

  int postJson(const char* path, const std::string& body, std::string& response) override {
    response.clear();
    if (!isConnected()) return -1;
    if (body.size() > 0xFFFF) return -2;

    xSemaphoreTake(g_httpDone, 0);  // clear any stale signal
    g_httpFailed = false;
    g_httpStatus = 0;
    g_httpLen = 0;

    // The modem accepts one extra header line. The device key is the one the
    // server needs; Content-Type comes from the JSON post parameter.
    static const char kHeader[] = "X-Device-Key: " DEVICE_KEY;
    char contentType[32] = {0};
    if (!modem.httpSend(WALTER_HTTP_PROFILE, path, (uint8_t*)body.data(), (uint16_t)body.size(),
                        WALTER_MODEM_HTTP_SEND_CMD_POST, WALTER_MODEM_HTTP_POST_PARAM_JSON,
                        contentType, sizeof(contentType), kHeader)) {
      Serial.println("[lte] POST failed: modem rejected the request");
      return -3;
    }

    // Wait for the answer ("ring"), a failure, or the time-out.
    uint32_t waitMs = HTTP_CONNECT_TIMEOUT_MS + HTTP_RESPONSE_TIMEOUT_MS + 30000UL;
    if (xSemaphoreTake(g_httpDone, pdMS_TO_TICKS(waitMs)) != pdTRUE) {
      Serial.println("[lte] POST failed: no answer from the server (time-out)");
      return -4;
    }
    if (g_httpFailed) {
      Serial.printf("[lte] POST failed: connection error %u (TLS or network)\n", (unsigned)g_httpRc);
      return -5;
    }

    int status = g_httpStatus;
    size_t len = g_httpLen;
    static uint8_t buf[2049];
    if (len > 0 && len < sizeof(buf)) {
      if (modem.httpReceive(WALTER_HTTP_PROFILE, buf, len)) {
        response.assign((const char*)buf, len);
      } else {
        Serial.println("[lte] could not read the response body");
      }
    } else if (len >= sizeof(buf)) {
      // Too big to be our 80-byte JSON reply (an error page). Drain it in
      // pieces is not supported by the modem command, so just leave it; the
      // next request replaces it.
      Serial.printf("[lte] response body of %u bytes ignored\n", (unsigned)len);
    }
    return status;
  }

  int signalDbm() override { return rsrp_; }

  void printStatus(Print& out) override {
    out.printf("uplink: lte-m (Walter), modem %s, %s, RSRP %d dBm, TLS %s\n",
               modemOk_ ? "ok" : "NOT STARTED", registered() ? "registered" : "NOT registered",
               rsrp_, configured_ ? "configured" : "NOT configured");
    out.printf("server: https://%s:%d%s (certificate checked by the modem against ISRG Root X1)\n",
               SERVER_HOST, (int)SERVER_PORT, SERVER_PATH);
  }

 private:
  bool registered() {
    WalterModemNetworkRegState s = modem.getNetworkRegState();
    return s == WALTER_MODEM_NETWORK_REG_REGISTERED_HOME ||
           s == WALTER_MODEM_NETWORK_REG_REGISTERED_ROAMING;
  }

  // Store the root certificate in the modem and set up the TLS + HTTP
  // profiles. The modem keeps these in its own flash, so the certificate is
  // only written again when walter_ca.h changes (saves modem flash wear).
  bool configureProfiles() {
    Preferences p;
    p.begin("walter", false);
    bool caStored = p.getUInt("caver", 0) == WALTER_CA_VERSION;
    if (!caStored) {
      if (!modem.tlsWriteCredential(false, WALTER_CA_SLOT, WALTER_ROOT_CA_PEM)) {
        Serial.println("[lte] ERROR: could not store the root certificate in the modem");
        p.end();
        return false;
      }
      p.putUInt("caver", WALTER_CA_VERSION);
      Serial.println("[lte] root certificate stored in the modem");
    }
    p.end();

    // Check both the certificate chain and that the name matches the host.
    if (!modem.tlsConfigProfile(WALTER_TLS_PROFILE, WALTER_MODEM_TLS_VALIDATION_URL_AND_CA,
                                WALTER_MODEM_TLS_VERSION_12, WALTER_CA_SLOT)) {
      Serial.println("[lte] ERROR: TLS profile configuration failed");
      return false;
    }
    if (!modem.httpConfigProfile(WALTER_HTTP_PROFILE, SERVER_HOST, SERVER_PORT, WALTER_TLS_PROFILE)) {
      Serial.println("[lte] ERROR: HTTP profile configuration failed");
      return false;
    }
    return true;
  }

  // Same sequence as the library's HTTPS example: radio off, define the data
  // context, radio on, automatic operator selection. Registration itself then
  // happens in the background and is polled in loop().
  void startRegistration() {
    regStartMs_ = millis();
    if (!modem.setOpState(WALTER_MODEM_OPSTATE_NO_RF)) {
      Serial.println("[lte] could not switch the radio off for configuration");
      return;
    }
    const char* apn = (strlen(CELL_APN) > 0) ? CELL_APN : nullptr;
    if (!modem.definePDPContext(1, apn)) {
      Serial.println("[lte] could not define the data context (check CELL_APN)");
      return;
    }
    if (!modem.setOpState(WALTER_MODEM_OPSTATE_FULL)) {
      Serial.println("[lte] could not switch the radio on");
      return;
    }
    if (!modem.setNetworkSelectionMode(WALTER_MODEM_NETWORK_SEL_MODE_AUTOMATIC)) {
      Serial.println("[lte] could not select automatic operator mode");
      return;
    }
    Serial.println("[lte] searching for the network...");
  }

  // The cellular network provides the time, so no NTP is needed.
  void syncClockFromNetwork() {
    WalterModemRsp rsp = {};
    if (modem.getClock(&rsp) && rsp.data.clock.epochTime > 1700000000LL) {
      clockSet((uint32_t)rsp.data.clock.epochTime);
      Serial.printf("[time] clock set from the cellular network, UTC epoch %lu\n",
                    (unsigned long)rsp.data.clock.epochTime);
    } else {
      Serial.println("[time] network gave no time yet; the server's reply will set the clock");
    }
  }

  void refreshSignal() {
    lastSignalMs_ = millis();
    WalterModemRsp rsp = {};
    if (modem.getSignalQuality(&rsp)) rsrp_ = rsp.data.signalQuality.rsrp;
  }

  bool modemOk_ = false;
  bool configured_ = false;
  bool wasRegistered_ = false;
  uint32_t lastCheckMs_ = 0;
  uint32_t regStartMs_ = 0;
  uint32_t regFailures_ = 0;
  uint32_t lastSignalMs_ = 0;
  int rsrp_ = 0;
};

WalterUplink g_walterUplink;

}  // namespace

Uplink& uplinkInstance() { return g_walterUplink; }

#endif  // UPLINK_WALTER
