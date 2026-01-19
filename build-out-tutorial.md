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

**How it works**: Use [4G/LTE HAT](https://www.pishop.us/product/4g-3g-2g-gsm-gprs-gnss-hat-for-raspberry-pi-lte-cat4-the-global-version/) for connectivity. Send to any cloud backend.

**Pros**:
- No WiFi required at fridge location
- Works anywhere with cell coverage
- GPS tracking possible (HAT includes GNSS)

**Cons**:
- Requires SIM card + data plan
- More expensive hardware (~$90)
- Monthly data cost
- More power consumption
- Requires Raspberry Pi (not Pico/ESP32 directly)

**Setup**:
1. Attach LTE HAT to Raspberry Pi
2. Insert SIM card with data plan
3. Configure PPP or NetworkManager
4. Send data to any cloud endpoint

**Complexity**: Medium-Hard | **Cost**: $90 + data plan

---

### Recommendation

For the Hollygrove Community Fridge:

**If WiFi is available**: Google Sheets (Option 1)
- Easiest to set up
- Easy to share usage reports with community/funders
- Zero ongoing cost

**If no WiFi**: Cellular HAT (Option 7) + Google Sheets
- Higher upfront cost but no WiFi infrastructure needed
- Same easy reporting

---
