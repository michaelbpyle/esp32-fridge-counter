# Build-Out Tutorial - Community Fridge Counter

<!--
INSTRUCTIONS FOR CLAUDE:
========================
This is the BUILD TUTORIAL - technical implementation details and the evolving plan.

PURPOSE: Document HOW to build this project, including architecture decisions,
wiring, code structure, and step-by-step implementation.

STRUCTURE:
1. Project Overview - What we're building and why
2. Platform Decision - Which microcontroller and rationale
3. Architecture - System design and components
4. Implementation Plan - Phases of development
5. Technical Details - Wiring, code, configuration

WHEN UPDATING:
- Update sections as decisions are made
- Add technical details as they are determined
- Keep implementation instructions clear and actionable
- Mark sections as [DECIDED], [PENDING], or [TBD] as appropriate

DO NOT:
- Add session history here (that goes in project-log.md)
- Track task completion status (use project-log.md for that)
- Duplicate the changelog/log entries

THIS IS DISTINCT FROM project-log.md:
- build-out-tutorial.md = HOW to build it (instructions + plan)
- project-log.md = WHAT we did and WHEN (history + tasks)
-->

---

## 1. Project Overview

### What We're Building
A device to count how many times a community refrigerator door is opened, transmitting the data via WiFi for usage analysis.

### Why It Matters
Community fridges serve food-insecure populations. Tracking door opens helps:
- Understand usage patterns (peak times, daily/weekly trends)
- Demonstrate impact to funders and stakeholders
- Plan restocking and maintenance schedules

### Core Requirements
1. Detect door open events reliably
2. Count events accurately (debounce handling)
3. Transmit data wirelessly
4. Survive outdoor conditions (weather-proof)
5. Low power consumption (ideally)
6. Simple, reproducible build

---

## 2. Supported Platforms

**Status**: [DECIDED] - Dual platform support

This project supports **both** platforms with a single codebase using conditional compilation.

### Option A: Raspberry Pi Pico 2W (Recommended)
| Spec | Value |
|------|-------|
| Chip | RP2350 (dual-core Arm Cortex-M33, 150MHz) |
| WiFi | 2.4GHz 802.11n (CYW43439) |
| GPIO | 26 multi-function pins |
| Cost | ~$6 |
| LED | Via WiFi chip (LED_BUILTIN) |
| Reed Pin | GP15 (physical pin 20) |

**Pros**: Standardized pinout, lower cost, simpler upload process

### Option B: Freenove ESP32-S3 WROOM
| Spec | Value |
|------|-------|
| Chip | ESP32-S3 (dual-core Xtensa LX7, 240MHz) |
| Board | Freenove ESP32-S3 WROOM N8R8 |
| Flash/PSRAM | 8MB / 8MB |
| WiFi | 2.4GHz 802.11 b/g/n |
| GPIO | 45 GPIOs (some reserved) |
| Cost | ~$10-15 |
| LED | GPIO48 (RGB) |
| Reed Pin | GPIO4 |

**Pros**: More powerful, more GPIOs, Bluetooth, onboard SD card slot

### Building for Each Platform
```bash
# Pico 2W
pio run -e pico2w

# ESP32-S3 (Freenove)
pio run -e esp32s3
```

### Build Output
| Platform | Flash Used | RAM Used | Output File |
|----------|------------|----------|-------------|
| Pico 2W | 8.6% | 13.8% | `.b/pico2w/firmware.uf2` |
| ESP32-S3 | 20.3% | 13.2% | `.b/esp32s3/firmware.bin` |

Note: Build directory is `.b` (not `.pio/build`) to avoid Windows path-length issues.

---

## 3. Architecture

### System Diagram
```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   FRIDGE DOOR   │      │  MICROCONTROLLER │      │     SERVER      │
│                 │      │                  │      │                 │
│  ┌──────────┐   │      │   ┌──────────┐   │      │  ┌───────────┐  │
│  │  Magnet  │───┼──────┼───│Reed Swtch│   │      │  │  Endpoint │  │
│  └──────────┘   │ ~2cm │   └────┬─────┘   │      │  │  /fridge  │  │
│                 │      │        │         │      │  └─────┬─────┘  │
└─────────────────┘      │   ┌────▼─────┐   │      │        │        │
                         │   │   GPIO   │   │      │   ┌────▼────┐   │
                         │   └────┬─────┘   │      │   │ Database │  │
                         │        │         │      │   └─────────┘   │
                         │   ┌────▼─────┐   │ WiFi │                 │
                         │   │  Counter │───┼──────┤                 │
                         │   │  Logic   │   │ HTTP │                 │
                         │   └──────────┘   │ POST │                 │
                         └──────────────────┘      └─────────────────┘
```

### Components
| Component | Purpose | Status |
|-----------|---------|--------|
| Pico 2W **or** ESP32-S3 | Main processor, WiFi | DECIDED |
| Reed Switch (NO) | Door sensor | DECIDED |
| Magnet | Triggers reed switch | DECIDED |
| Enclosure (IP65) | Weather protection | TBD |
| Power supply | 5V USB | DECIDED |

---

## 4. Implementation Plan

### Phase 1: Core Functionality
- [x] Set up dual-platform support (Pico 2W + ESP32-S3)
- [ ] Wire reed switch to GPIO + GND
- [x] Implement door state detection
- [x] Add debounce handling (200ms default)
- [ ] Test counting accuracy

### Phase 2: Connectivity
- [x] WiFi connection with timeout/retry
- [x] HTTP POST to server endpoint
- [x] Handle connection failures gracefully
- [x] LED feedback for status

### Phase 3: Reliability
- [ ] Store count in non-volatile memory (survives power loss)
- [ ] Reconnect WiFi if disconnected
- [ ] Watchdog timer for crash recovery

### Phase 4: Deployment
- [ ] Weather-proof enclosure assembly
- [ ] Cable management and sealing
- [ ] Mounting hardware
- [ ] Field installation

### Phase 5: Enhancements (Future)
- [ ] Battery power with deep sleep
- [ ] Track door open duration
- [ ] Local web interface for configuration
- [ ] OTA firmware updates

---

## 5. Technical Details

### Wiring

**Pico 2W:**
```
Reed Switch Wire 1  →  GND (Pin 38)
Reed Switch Wire 2  →  GP15 (Pin 20)
```
See `pico2w-WIRING.txt` for full pinout diagram.

**Freenove ESP32-S3 WROOM:**
```
Reed Switch Wire 1  →  GND (any GND pin)
Reed Switch Wire 2  →  GPIO4
```
See `esp32s3-WIRING.txt` for full pinout and safe GPIO reference.

Note: Reed switch has no polarity - wires are interchangeable.

### Logic Flow
```
1. Initialize GPIO with internal pull-up
2. Connect to WiFi
3. Main loop:
   a. Read GPIO state
   b. If state changed AND debounce time passed:
      - If door opened (LOW → HIGH): increment counter, send to server
      - If door closed (HIGH → LOW): log event
   c. Update last state
   d. Small delay (10ms)
```

### Configuration Parameters
| Parameter | Default | Purpose |
|-----------|---------|---------|
| DEBOUNCE_MS | 200 | Prevent double-counting |
| WIFI_TIMEOUT_MS | 10000 | Connection timeout |
| SEND_INTERVAL_MS | 0 | 0 = immediate, >0 = batch send |
| SERVER_URL | "" | HTTP endpoint for data |

---

## 6. Server Integration / Data Logging

**Status**: [TBD] - Choose one option below

### Data Format (current)
```json
{
  "count": 42,
  "device": "fridge-counter"
}
```

---

### Option 1: Google Sheets (Recommended for simplicity)

**How it works**: Google Apps Script creates a webhook URL. Device POSTs data, script appends row to spreadsheet.

**Pros**:
- Free
- No server to maintain
- Easy to share with stakeholders
- Built-in charts and visualization
- Accessible from anywhere

**Cons**:
- Google account required
- Rate limits (but fine for door counts)
- Data lives on Google's servers

**Setup**:
1. Create a Google Sheet
2. Go to Extensions → Apps Script
3. Paste webhook script (creates `/exec` endpoint)
4. Deploy as web app (anyone can access)
5. Copy URL to `config.h` as `SERVER_URL`

**Complexity**: Easy | **Cost**: Free

---

### Option 2: Supabase / Firebase

**How it works**: Cloud database with REST API. Device POSTs directly to database.

**Pros**:
- Free tier generous (Supabase: 500MB, Firebase: 1GB)
- Real-time subscriptions
- Built-in auth if needed
- SQL (Supabase) or NoSQL (Firebase)
- Easy dashboard building

**Cons**:
- Requires account setup
- Slightly more complex than Sheets
- Vendor lock-in

**Setup**:
1. Create Supabase/Firebase project
2. Create table/collection for events
3. Get API URL and anon key
4. POST to REST endpoint

**Complexity**: Easy-Medium | **Cost**: Free tier available

---

### Option 3: InfluxDB + Grafana

**How it works**: Time-series database optimized for metrics. Grafana provides dashboards.

**Pros**:
- Purpose-built for time-series data
- Powerful queries (downsampling, aggregation)
- Beautiful Grafana dashboards
- Self-hosted = full data control
- InfluxDB Cloud has free tier

**Cons**:
- More complex setup
- Self-hosted requires server
- Overkill for simple counting

**Setup**:
1. Install InfluxDB (local, VPS, or cloud)
2. Create bucket for fridge data
3. Get API token
4. POST to InfluxDB line protocol or HTTP API
5. Connect Grafana to InfluxDB
6. Build dashboard

**Complexity**: Medium | **Cost**: Free (self-hosted) or free tier (cloud)

---

### Option 4: Home Assistant

**How it works**: Local home automation platform. Device sends to HA REST API or MQTT.

**Pros**:
- Local/private - no cloud dependency
- Integrates with other home automation
- Good visualization built-in
- MQTT support

**Cons**:
- Requires Home Assistant server running
- More setup if you don't already have HA
- Local network only (unless you expose it)

**Setup**:
1. Install Home Assistant (Pi, VM, etc.)
2. Enable REST API or MQTT broker
3. Create sensor entity for fridge counter
4. Configure device to POST to HA

**Complexity**: Medium | **Cost**: Free (need hardware for server)

---

### Option 5: MQTT Broker (Mosquitto, HiveMQ)

**How it works**: Lightweight pub/sub messaging. Device publishes; subscribers receive.

**Pros**:
- Lightweight protocol (good for IoT)
- Real-time
- Multiple subscribers can listen
- Works well with cellular (low bandwidth)
- HiveMQ Cloud has free tier

**Cons**:
- Need separate storage for historical data
- Need subscriber to log data somewhere
- Another moving part

**Setup**:
1. Set up MQTT broker (Mosquitto local, or HiveMQ Cloud)
2. Device publishes to topic `fridge/door/count`
3. Subscriber logs to database or file
4. Or use Node-RED to bridge MQTT → database

**Complexity**: Medium | **Cost**: Free

---

### Option 6: Simple VPS + REST API

**How it works**: Run a small server (Flask, Express, etc.) on a VPS. Device POSTs; server logs to SQLite/Postgres.

**Pros**:
- Full control
- Custom logic possible
- Can build custom dashboard
- Cheap VPS ($5/mo)

**Cons**:
- Requires server maintenance
- Need to write backend code
- Security responsibility on you

**Setup**:
1. Spin up VPS (DigitalOcean, Linode, etc.)
2. Write simple REST endpoint
3. Store in SQLite or Postgres
4. Build dashboard (or use Grafana)

**Complexity**: Medium-Hard | **Cost**: ~$5/month

---

### Option 7: Cellular + Cloud (No WiFi Needed)

**How it works**: Add a cellular modem module to the ESP32 (or Pico) over UART using the
[TinyGSM](https://github.com/vshymanskyy/TinyGSM) library, then send to any cloud backend.

> **Correction**: An earlier version of this doc claimed cellular "requires a Raspberry Pi,
> not Pico/ESP32 directly." That is **not true**. The ESP32 talks to a cellular modem over
> UART and is well-supported by TinyGSM. The "needs a Pi" note only applied to one specific
> Raspberry-Pi-HAT-shaped product, not to cellular in general.

**Recommended hardware for this project**:
- **ESP32 + SIM7080G modem** (LTE **Cat-M1 / NB-IoT**). This is the right class of modem for a
  door counter: tiny payloads, ~3µA sleep current, low data cost. Avoid full LTE Cat-1 modems
  (A7670 / SIM7600) — faster but unnecessary power/cost here. Avoid 2G modules (SIM800); 2G/3G
  networks are shut down in the US.
- All-in-one boards exist (e.g. **LILYGO T-SIM7000G** = ESP32 + modem + SIM slot + GPS), which
  are the simplest path. ESP32-S3 + SIM7080G boards are also available.

**SIM choice — eSIM vs physical SIM**:
| | Physical SIM (nano) | eSIM / eUICC (MFF2 soldered chip) |
|---|---|---|
| Form | Removable card in a slot | Soldered chip on the board |
| Reprovision carrier | Swap card by hand | Remote, over the air — no device access |
| Outdoor durability | Slot is a failure point | Sealed; resists moisture/corrosion/vibration |
| Best for | Prototyping | Deployed/sealed/outdoor devices |

For an outdoor unit in a sealed IP65 enclosure, a **soldered eSIM/eUICC chip is preferable** —
no slot to corrode, and the carrier can be re-provisioned remotely without opening the box.

**Recommended data plan**: **1NCE IoT Lifetime Flat — ~$14 for 500 MB over 10 years**, with
**no monthly bill**. A door counter uses a tiny fraction of 500 MB. 1NCE offers it as a physical
nano-SIM, a eUICC eSIM, *and* a solderable chip. (In the US these IoT SIMs roam onto Cat-M
coverage via T-Mobile/AT&T — verify coverage at the fridge site first.)

**Pros**:
- No WiFi required at fridge location; works anywhere with Cat-M/NB-IoT coverage
- No WiFi-bridge hardware needed
- One-time SIM cost, no recurring monthly fee (with 1NCE lifetime plan)
- Low power — suitable for battery/solar

**Cons**:
- Requires a cellular modem module + IoT SIM
- Coverage varies by location (check Cat-M/NB-IoT availability)
- Slightly more firmware work than plain WiFi (TinyGSM vs built-in WiFi)

**Setup**:
1. Use an ESP32 + SIM7080G board (or wire a modem module to ESP32 over UART)
2. Install an IoT SIM/eSIM (1NCE recommended)
3. Use TinyGSM to bring up the cellular connection
4. POST to any cloud endpoint (same payload as the WiFi path)

**Complexity**: Medium | **Cost**: ~$25–40 board + ~$14 SIM (10 yr) — no monthly fee

---

### Option 8: LoRa Mesh / Meshtastic (No WiFi, No Cellular, No Fees) ⭐ LEADING CANDIDATE

**How it works**: [Meshtastic](https://meshtastic.org/) is an open-source LoRa mesh network on
license-free 915 MHz (US). Cheap ESP32-based radios relay messages for each other — no WiFi, no
SIM, no monthly fee. The fridge node sends its count over LoRa; a **gateway node** (one with
WiFi/internet) bridges the mesh to MQTT, which feeds a database/dashboard.

```
Fridge LoRa node  →(LoRa hops)→  Gateway node (WiFi/internet)  →  MQTT  →  database/dashboard
```

**The key requirement**: A lone LoRa node cannot reach the internet. Meshtastic only works if
**either**:
1. You place a **gateway node within ~1–3 km** (urban, line-of-sight dependent) of the fridge —
   e.g., at home / on the same network as **TrueNAS**; **or**
2. There is already a **community Meshtastic mesh** near the fridge (check the live public node
   map first).

If the fridge is isolated with no node in range, this option does not apply.

**Local partner — SwampNet**: [swampnet.info](https://swampnet.info) is a New Orleans (Bvlbancha)
mutual-aid Meshtastic network that has built LoRa links connecting mutual-aid distribution hubs
across the city since 2023 (a ~3.5-mile proof-of-concept mesh). They have the local RF expertise to
do the site survey, set up the nodes, and potentially tie this fridge counter into an existing
community mesh — which could remove the need to stand up our own dedicated gateway. **Engage SwampNet
early** for siting and setup.

**Site link (Hollygrove)**: planned hop is **8430 Apple St** (gateway/relay site, antenna up to
~3 stories) ↔ **9000 Oleander** (fridge node, antenna up to ~2 stories), measured at **~694 m
(0.43 mi)** apart. This is a short urban hop, well within Meshtastic range.
- **Is line-of-sight required?** Not strictly at this distance, but it is the dominant factor. At
  915 MHz, range is essentially LOS-limited and degraded by buildings/tree canopy; a clear path is
  worth far more than antenna gain.
- **Fresnel zone**: the first Fresnel zone is only ~7.5 m radius at the midpoint (60% clearance
  ≈ 4.5 m). Getting both antennas above the surrounding 1–2-story rooftops/tree line is what
  matters. At 3 stories (Apple St) and 2 stories (fridge), the nodes should clear most single-family
  rooftops in Hollygrove — likely a workable link even without perfect optical LOS.
- **Action**: have SwampNet do an empirical RSSI/SNR test (walk a node to each candidate mount
  height) before committing to permanent mounts. Cheaper and more reliable than modeling.

**Recommended hardware**:
- **Fridge node**: **Heltec WiFi LoRa 32 V3** (~$25) — ESP32-S3 + SX1262 LoRa + OLED. Same ESP32
  family as the rest of this project; serves as both the counter MCU and the LoRa radio.
- **Gateway / base station**: **B&Q Station G2** (~$109) — a high-power backbone node (35 dBm PA,
  ESP32-S3, rugged SMA socket, USB-C PD / 9–19V DC input). This is a permanent, substantial base
  station, not a dev board — paired with an elevated high-gain outdoor antenna, a single Station G2
  can cover a wide area, which is what gives the link the reach to reach the fridge reliably.
- **Antenna**: a 915 MHz high-gain (5.8+ dBi) outdoor antenna mounted at elevation for the gateway —
  antenna placement is the single biggest factor in range.
- **License note**: running the Station G2 at full 35 dBm power in the US requires an Amateur Radio
  (ham) license; it can run at reduced power without one.

**Data path**: Meshtastic has built-in MQTT — telemetry packets are auto-serialized to JSON and
published to an MQTT topic, commonly piped through **Node-RED** into a dashboard. The MQTT broker
can run **self-hosted on TrueNAS** → fully private, zero cloud, zero recurring cost.

**Pros**:
- **$0 recurring — free forever.** No SIM, no data plan, no WiFi infrastructure.
- Long range (1–3 km urban, more with good antenna/line-of-sight); low power (good for battery/solar)
- Tiny payloads (a count) are an ideal fit for LoRa's low bandwidth
- Resilient mesh; self-hostable end-to-end on TrueNAS
- Same ESP32 ecosystem already in use

**Cons**:
- Requires **≥2 nodes** (fridge + gateway) unless a community mesh already covers the site
- Range depends on terrain/line-of-sight — must verify a gateway is reachable
- Slightly more setup (mesh config + MQTT bridge) than plain WiFi

**Setup**:
1. Flash Meshtastic onto the Heltec V3 fridge node and the Station G2 base station
2. Install the Station G2 with its elevated outdoor antenna where it has WiFi/internet, within
   LoRa range of the fridge
3. Enable MQTT on the gateway; point it at an MQTT broker (self-hosted on TrueNAS)
4. Fridge node sends count as telemetry → mesh → gateway → MQTT → Node-RED → dashboard

**Complexity**: Medium | **Cost**: ~$205 (Heltec V3 fridge node + Station G2 + outdoor antenna),
$0 recurring

**Beyond door count — multi-sensor telemetry over the mesh** (see project-log.md for phased plan):
- **Door + weather** ride on **native Meshtastic modules** (Detection Sensor + Environment
  Telemetry / BME280) — no custom code.
- **Power-system health** comes from the fridge's real off-grid gear, read over their own buses, not
  hobby shunts: the **Growatt SPF 3000TL** inverter via **Modbus RTU** (ESP32 + MAX485 on the RS485
  expansion port; PV power, battery V/SoC/current, load, daily kWh) and the **EG4 LifePower4 48V**
  BMS via **RS485** (cell detail). Open-source register maps exist (grott, growatt2mqtt, ESPHome).
- **Per-shelf weights** (inventory) via load cells + HX711, the one non-native piece.
- A **companion ESP32-S3** aggregates the custom sensors and injects a combined payload into the mesh
  via the Heltec's serial API, keeping the radio node on stock Meshtastic. The node powers itself
  from 5V bucked off the 48V battery.

---

### Option 9: Walter (ESP32-S3 + LTE-M/NB-IoT/GNSS in one certified module) — [POSSIBILITY, researched 2026-11-05]

**What it is**: [Walter](https://www.quickspot.io/) (QuickSpot, a brand of DPTechnics BV, Belgium) is a
55 × 24.8 mm system-on-module that puts an **ESP32-S3** and a **Sequans GM02SP** cellular modem on one
board. It is the "ESP32 + cellular modem" idea from Option 7, but pre-integrated and pre-certified, so
there is no modem wiring, no TinyGSM, and no FCC testing to do. Datasheet checked: **rev 1.2, 2026-11-04**.

**Where it fits**: this is a **cellular alternative/fallback**, not a replacement for the Meshtastic
direction (Option 8). It has **no LoRa radio**. It would slot in where Option 7's SIM7080G was
the fallback (no gateway in LoRa range), or as the single-board fridge node if the mesh path fails.
Two possible roles:
1. **Standalone cellular node** — reads the reed switch (and later sensors) and uploads over LTE-M
   directly to a cloud/MQTT endpoint. No gateway, no SwampNet dependency, but a SIM fee.
2. **Companion/aggregator** — replaces the planned companion ESP32-S3 (HX711 + Modbus + BME280) and
   gives that data its own cellular uplink, independent of the mesh. Whether it could also feed the
   Heltec over serial is untested; treat as an idea only.

**Key specs (from the datasheet)**:
| Item | Value |
|---|---|
| MCU | ESP32-S3-WROOM-1-N16R2 — dual-core LX7, 16 MiB flash, 2 MiB PSRAM, WiFi 4, BLE 5 |
| Cellular | Sequans GM02SP — **LTE-M (Cat M1), NB-IoT (NB1/NB2)**. Not 5G, despite some marketing wording. No 2G/3G/Cat-1 |
| GNSS | GPS + Galileo (receive only); not needed for a fixed fridge site |
| SIM | **Nano-SIM holder** on the underside, plus an "integrated SIM" mentioned on the product page. eSIM/iSIM status unclear: a QuickSpot staff reply (2024) said eSIM/multi-IMSI SIMs work and iSIM (SGP32) is supported in hardware but no provider offers it yet. Not SIM-locked |
| Deep sleep | **9.5 µA** (ESP32-S3 in deep sleep, modem in PSM, measured at 5.0 V) |
| Active current | ~10 mA (modem PSM, CPU 10 MHz), ~60 mA (CPU 240 MHz), ~450 mA typical LTE transmit peak. Size the supply for **1.0 A at 5 V / 1.5 A at 3 V** worst case |
| Power input | USB-C 5 V, or VIN pin **3.0–5.5 V**. Absolute max 5.5 V |
| I/O | 24 usable GPIO at 3.3 V (not 5 V tolerant); UART/SPI/I2C/CAN/I2S/SD mappable to most pins; switchable 3V3 OUT (max 250 mA) |
| Antennas | Two u.FL connectors (LTE, GNSS); WiFi/BLE on a PCB antenna. **Antennas are not included in the bare module** |
| Temperature | -40 to +85 °C operating. Condensation not allowed, so it still needs the IP65 enclosure |
| Certification | FCC ID **2BDGUWALTER**, ISED, CE, UKCA, RCM. **Verizon approved** (Open Development, LTE-M bands 4/12/13) as a modem. **No AT&T or T-Mobile approval found** in the datasheet or product pages |

**Cautions specific to this project**:
- **No overvoltage or reverse-polarity protection on VIN.** The 48 V battery must go through a good
  buck converter to a clean regulated 5 V, with margin for transients. Never plug USB in while a carrier
  board powers VIN, unless the carrier has an OR-ing diode (datasheet section 5.1.1).
- **FCC conditions**: fixed installation, antenna at least 20 cm from people, per-band antenna gain
  caps (for example 5.0 dBi on band 4, 8.6 dBi on band 12). Use an approved antenna such as the
  Taoglas FXUB63.07.0150C (LTE) and FXP611.07.0092C (GNSS) listed in the datasheet.
- **Library licence**: the WalterModem Arduino library is under DPTechnics's "5 clause" licence
  (BSD-3-Clause plus a condition that closed-source binaries run only on a Walter board). Fine for
  this open project; note it if firmware is ever redistributed commercially.
- **Carrier coverage is unverified.** Walter is a modem, not a SIM. LTE-M coverage in Hollygrove on
  whichever IoT SIM we pick (1NCE, Soracom) has not been checked. Which US network 1NCE uses for
  LTE-M was not confirmed in research (one third-party guide lists AT&T roaming for 1NCE; treat as
  anecdotal). Ask the SIM vendor and check their coverage map before buying.

**Software**: Arduino (library `WalterModem` v1.6.1, ESP32 core already lists a "DPTechnics Walter"
board), ESP-IDF, MicroPython, Zephyr; Toit is listed as future support on one page. Library examples
cover **MQTT, MQTTS, HTTP/HTTPS, CoAP, UDP/TCP, AWS MQTT, ThingSpeak, positioning, modem firmware
update, and BlueCherry** (QuickSpot's own cloud, optional). A plain MQTT publish to our
self-hosted broker on TrueNAS would work the same as the WiFi path. A PlatformIO board definition for
Walter was **not** found in the standard espressif32 platform; expect to use the Arduino-ESP32 board
settings or a custom board JSON (this project already builds with PlatformIO). Every board ships
pre-flashed with a demo that uploads to a public QuickSpot portal. Reflash before deploying.

**Optional carrier board — Walter Feels (P000000105)**: open-source (KiCad) gateway board with
a 2.5–26 V **MPPT solar input**, an LTC4015 charger/battery manager with coulomb counter (LiFePO4, Li-ion
or lead-acid), **RS485, RS232, SDI-12 and CAN**, temperature/humidity/pressure/IMU sensors, microSD, and
3.3/5/12 V outputs. The RS485 port matches the Phase 2 Growatt/EG4 Modbus plan. **Fit problem**: the
board charges batteries of up to 9 LiFePO4 cells and takes at most 26 V in, so it cannot sit directly
on the 48 V (16-cell) EG4 pack. It would need a separate 12–24 V feed, or be used only for its RS485 and
sensors, or be skipped in favour of bare Walter + MAX485 + buck converter. Open question.

**Cost** (list prices as found; USD for the bare module not confirmed):
| Item | Price |
|---|---|
| Walter module (P000000100) | €59 excl. VAT (QuickSpot MSRP) |
| Walter DevKit (module + Taoglas LTE/GNSS antennas + 2 USB-C cables + 250 MB/1-yr Soracom SIM) | €250 excl. VAT; Mouser US listing showed **$310** |
| Walter Feels carrier board | €125 excl. VAT (QuickSpot MSRP) |
| IoT SIM | 1NCE ~$14 / 500 MB / 10 yr (per Option 7) or Soracom |

**Pros**: one certified board, no modem integration; very low sleep current; reads our sensors and
phones home with no gateway; Verizon-approved; open-source hardware and libraries; RS485/CAN available
through Walter Feels.

**Cons**: costs more than a Heltec V3 fridge node; **recurring SIM cost** (small but not $0);
depends on LTE-M coverage and a carrier staying up, whereas the mesh depends on neither; no AT&T
approval found; newer product with a small community (the Arduino library repo had about 41 stars);
no LoRa, so it cannot join SwampNet.

**Complexity**: Medium | **Cost**: roughly the DevKit price for a first unit, then module + antennas +
SIM; plus Walter Feels if used.

**Next steps if pursued**: (1) ask the SIM vendor for LTE-M coverage at 9000 Oleander; (2) ask
QuickSpot about AT&T/T-Mobile operation and the integrated SIM; (3) buy one DevKit and run the `mqtt`
example against the TrueNAS broker; (4) measure real average current on the fridge's 5 V rail.

**Sources**: [Walter datasheet rev 1.2](https://www.quickspot.io/datasheet/walter_datasheet.pdf) ·
[Walter Feels datasheet rev 1.0](https://www.quickspot.io/datasheet/walter_feels_datasheet.pdf) ·
[QuickSpot product page](https://www.quickspot.io/) ·
[walter-arduino library and examples](https://github.com/QuickSpot/walter-arduino) ·
[Soracom Walter store page](https://store.soracom.io/walter) ·
[Mouser Walter DevKit P000000101](https://www.mouser.in/en/new/dptechnics/dptechnics-walter-devkit/) ·
[CNX Software launch article](https://www.cnx-software.com/2023/01/02/walter-esp32-s3-board-supports-nb-iot-lte-m-and-gps/)

---

### Recommendation

For the Hollygrove Community Fridge:

**If WiFi is available**: Google Sheets (Option 1)
- Easiest to set up
- Easy to share usage reports with community/funders
- Zero ongoing cost

**If no WiFi — LEADING DIRECTION**: LoRa Mesh / Meshtastic (Option 8)
- Free forever — no SIM, no data plan, no WiFi infrastructure
- Heltec V3 fridge node + **Station G2 base station** with elevated outdoor antenna (~$205);
  the high-power gateway is a permanent backbone, not a dev board
- Fully self-hostable on TrueNAS (MQTT + Node-RED), zero cloud dependency
- **Requires**: the base station to have internet and be within LoRa range of the fridge.
  Verify reachability before committing.

**If no WiFi and no gateway in LoRa range**: ESP32 + SIM7080G cellular (Option 7)
- Works anywhere with Cat-M coverage; no dependency on a nearby node
- ~$25–40 board + ~$14 1NCE SIM (500 MB / 10 years, no monthly fee)
- Soldered eSIM preferred for the outdoor enclosure
- A pre-certified alternative to the DIY modem is **Walter** (Option 9): ESP32-S3 + LTE-M/NB-IoT in one
  board. Researched, not yet bought. Verify LTE-M coverage and SIM carrier first.

---
