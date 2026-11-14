# Project Log - Community Fridge Counter

<!--
INSTRUCTIONS FOR CLAUDE:
========================
This is a PROJECT LOG - a living record of work sessions and task tracking.

PURPOSE: Track what has been done, what needs to be done, and session history.

STRUCTURE:
1. Todo Checklist - Active tasks and their status
2. Session Log - Reverse chronological (newest first)

WHEN UPDATING:
- Add new sessions at the TOP of the Session Log section
- Update todo items as they are completed or added
- Keep entries concise but informative
- Include date in YYYY-MM-DD format

DO NOT:
- Add implementation details here (that goes in build-out-tutorial.md)
- Duplicate the tutorial content
- Add wiring diagrams or code explanations

THIS IS DISTINCT FROM build-out-tutorial.md:
- project-log.md = WHAT we did and WHEN (history + tasks)
- build-out-tutorial.md = HOW to build it (instructions + plan)
-->

---

## Goals

*(added 2026-09-24 per spec v1.1 rule 10 — DRAFT, reconstructed by Claude from this log, `build-out-tutorial.md` and `SWAMPNET-BRIEF.md`; unreviewed by Michael)*

- Count how many times the Hollygrove Community Fridge door is opened — to see usage patterns, demonstrate impact to funders, and plan restocking. (Owner, 2026-11-14: "WiFi now, LTE later." The counter is built and tested on WiFi at the house on a generic ESP32-S3 DevKitC; it will not be deployed to the fridge until the Walter LTE board arrives, and the Walter is the deployment board.)
- SUPERSEDED 2026-11-14 by the goal above: report it with **no WiFi, no SIM, and no recurring cost** via the Meshtastic/LoRa pivot (Heltec fridge node → gateway → self-hosted MQTT + Node-RED on TrueNAS).
- Grow the node into full fridge-site telemetry, in phases: door count + weather on native Meshtastic modules; power-system health read from the site's real off-grid gear (Growatt inverter + EG4 BMS over Modbus/RS485), never hobby shunts; per-shelf weights (HX711) for stock level.
- Partner with SwampNet (the New Orleans mutual-aid mesh) for the site survey and mesh integration rather than duplicating community infrastructure.
- (Owner, 2026-11-14) Finish the job as a working system now: an ESP32 program that counts openings and reports over WiFi, able to switch to 4G LTE on a Walter board; dormant support for weather, pressure and shelf-weight sensors; a wiring diagram; a server and database on the hollygrove VM; an interactive dashboard at `hollygrovenola.org/fridge`; a printable demo door with a print-in-place hinge; and a case with a power and weatherproofing plan. The dashboard shows its charts directly at `/fridge/` (sample data, clearly marked, until real counts exist).

---

## Shopping List

**Objective**: Track the number of times the Hollygrove Community Fridge is opened.

| # | Item | Price | Link/Notes |
|---|------|-------|------------|
| 1 | Magnetic Door Switch Set (x2) | $3.95 | Reed switch + magnet |
| 2 | Raspberry Pi Pico 2W | $7.00 | [PiShop](https://www.pishop.us/product/raspberry-pi-pico-2-w/) |
| 3 | Freenove ESP32-S3 WROOM | $15.00 | [Amazon](https://www.amazon.com/FREENOVE-ESP32-S3-WROOM-Compatible-Wireless-Detailed/dp/B0BMQ8F7FN) (alternative to Pico) |
| 4 | Wireless Outdoor WiFi Bridge | $109.99 | If fridge lacks WiFi coverage |
| 5 | Wireless Bridge Bracket Mount | $19.99 | For WiFi bridge |
| 6 | Waterproof Junction Box (IP65) | $17.99 | Enclosure for electronics |
| 7 | PoE Ethernet Hat for Pi Zero | $27.95 | Optional: power over ethernet |
| 8 | 2.8" Capacitive Touch Display | $28.95 | Optional: local display |
| 9 | Micro SD Card | $13.95 | For Pi (if needed) |
| 10 | Cable budget | $30.00 | USB cables, jumper wires |
| 11 | Programming and labor (40hrs) | $0.00 | Volunteer/in-kind |
| 12 | Heltec WiFi LoRa 32 V3 — fridge node | ~$25.00 | ESP32-S3 + LoRa. Serves as the fridge counter MCU **and** LoRa radio (replaces separate Pico/ESP32 #2-3 for the fridge unit). |
| 13 | B&Q Station G2 — base-station gateway | ~$109.00 | High-power backbone node (35 dBm PA, ESP32-S3, rugged SMA, USB-C PD / 9-19V DC). Permanent base station that bridges the LoRa mesh to the internet/MQTT. Far more range/reliability than a dev board. |
| 14 | High-gain outdoor antenna + mount + coax | ~$60.00 | 915MHz 5.8+ dBi external antenna mounted at elevation (rooftop) for the Station G2. Antenna placement is the single biggest range factor. |
| 15 | LoRa antenna (915MHz) — fridge node | ~$10.00 | Upgrade over stock antenna on the Heltec V3 fridge node, as needed. |
| **Total** | | **~$267.77** | |

> **Notes**:
> - The ~$267.77 total is a ceiling that bundles optional and either/or items. For the
>   **Meshtastic build path** (leading direction), the two LoRa nodes (#12-13) replace both a
>   separate microcontroller (#2-3) and the WiFi bridge (#4-5). Estimated real build: reed switch
>   (#1) + Heltec V3 fridge node (#12) + Station G2 base station (#13) + outdoor antenna (#14) +
>   IP65 enclosure (#6) + cables (#10) + fridge antenna (#15) ≈ **~$255**, with **$0 recurring** cost.
> - **License note**: running the Station G2 at its full 35 dBm power in the US requires an Amateur
>   Radio (ham) license. It can be run at lower power without one; high power + elevated antenna is
>   what gives the backbone its reach.

### Connectivity Options (choose one)
| Option | Price | Notes |
|--------|-------|-------|
| **LoRa Mesh / Meshtastic** ⭐ | ~$205 (nodes+antenna) | **LEADING DIRECTION.** No WiFi/SIM/fees. Heltec V3 fridge node + **Station G2 base station** (high-power backbone) w/ elevated outdoor antenna. Self-host MQTT+Node-RED on TrueNAS. See tutorial Option 8. |
| WiFi (built-in) | $0 | Requires nearby WiFi network |
| WiFi Bridge (#4-5 above) | $130 | Extends WiFi to fridge location |
| ESP32 + SIM7080G cellular (Cat-M/NB-IoT) | ~$25-40 board + ~$14 SIM | Fallback if no gateway in LoRa range. ESP32 does cellular directly via TinyGSM (NOT a Pi). 1NCE SIM = 500MB/10yr, no monthly fee. See tutorial Option 7. |
| **Walter** (ESP32-S3 + Sequans GM02SP LTE-M/NB-IoT, certified module) | €59 module / €250 DevKit (Mouser US DevKit $310) + SIM | POSSIBILITY (researched 2026-11-05). Pre-integrated alternative to the SIM7080G fallback; 9.5 µA deep sleep; Verizon-approved, no AT&T approval found; no LoRa. See tutorial Option 9. |

### Data Logging Options (choose one)
See `build-out-tutorial.md` Section 6 for full details on each option.

---

## Todo Checklist

### Hardware
- [x] Set up dual-platform support (Pico 2W + ESP32-S3)
- [x] Configure Freenove ESP32-S3 WROOM board in PlatformIO
- [x] Both firmwares compile and upload successfully
- [x] Pico 2W detected and running (COM8)
- [x] ESP32-S3 detected and running (COM9)
- [x] Reed switches arrived and tested
- [x] ESP32-S3 wiring verified and counting works
- [ ] Pico 2W reed switch wiring and testing

### Data Solution
- [x] Choose data logging backend: own service + SQLite on the hollygrove VM (2026-11-14)
- [x] Set up server on the hollygrove VM: container `hollygrove-fridge`, API at `https://hollygrovenola.org/fridge/api/v1/` (2026-11-14)
- [x] Configure WiFi credentials (secrets.h - gitignored)
- [x] Test end-to-end data flow: bench board to live server over HTTPS, as test device `bench-01` (2026-11-14, on USB power)
- [ ] Test with a real reed switch wired in, and off USB on a standalone 5 V supply

### Open after the 2026-11-14 build
- [ ] Owner: remaining questions in `DECISIONS-FOR-MICHAEL.md` (dashboard wording, power outlet and battery connection for the field install, weather sensor on the first install, database backup)
- [ ] Get a Walter board; run the `walter` build on it for the first time (it has only been compiled)
- [ ] Caliper checks, then first prints: demo door (`cad\demo-door\`), case (`cad\enclosure\`)
- [ ] Buy: PETG or ASA, Hammond 1554H2GY box and glands, M3 brass heat-set inserts and M3 screws (owner confirmed none on hand), DS18B20, HX711 and load cells if wanted (lists in `docs\wiring\wiring.md` and `docs\power-and-enclosure.md`)
- [ ] Build the field unit as `fridge-01` (key in `/opt/hollygrove/fridge/fridge.env` on the VM)
- [ ] Commit and push the new work (nothing was committed)

### Core Functionality
- [x] Basic door counting with reed switch
- [x] WiFi connectivity (LEGACY - being replaced by Meshtastic)
- [x] Data transmission to server endpoint (LEGACY - HTTP, being replaced by LoRa)
- [x] LED feedback for events

### Mesh / Connectivity (pivot 2026-06-07)
- [ ] Engage SwampNet (swampnet.info) for site survey + node setup
- [ ] Confirm 8430 Apple ↔ 9000 Oleander link with empirical RSSI/SNR test (~694m hop)
- [ ] Decide: join existing community mesh vs stand up own gateway
- [ ] Decide: stock Meshtastic firmware vs custom RadioLib firmware
- [ ] Replace WiFi/HTTP path in main.cpp with LoRa transmit
- [ ] Walter (cellular) as fallback/companion: verify LTE-M coverage at 9000 Oleander and which carrier the IoT SIM uses; ask QuickSpot about AT&T/T-Mobile and the integrated SIM (tutorial Option 9)

### Sensors / Telemetry (all reported over Meshtastic)
Native Meshtastic telemetry covers 3 of 4 sensors with NO custom code (Environment, Power,
Detection Sensor modules). Shelf weights (HX711) are the only non-native piece.

**Phase 1 — stock Meshtastic for the simple sensors (no custom code):**
- [ ] Door open count — Meshtastic **Detection Sensor** module on reed-switch GPIO
- [ ] Weather — Meshtastic **Environment Telemetry** module + BME280 (I2C)
- [ ] Validate full path end-to-end with SwampNet (Heltec V3 stock firmware → mesh → MQTT)

**Phase 2 — power-system telemetry (read real equipment, NOT hobby shunts):**
The fridge runs off a real off-grid power system (see 2026-06-11 entry). Pull telemetry from the
equipment's own buses rather than adding INA-series sensors:
- [ ] Read **Growatt SPF 3000TL LVM** inverter via **Modbus RTU** (RS485 expansion port or USB) —
      PV input V/power, battery V/current, load, AC out, daily kWh. ESP32 + MAX485 transceiver.
      Reference open-source register maps: grott / growatt2mqtt / ESPHome growatt component.
- [ ] Read **EG4 LifePower4 48V BMS** via **RS485** — SoC, pack V, current, per-cell V, temps.
      (Inverter already gets battery V/SoC over closed-loop CAN/RS485; BMS direct read = cell detail.)
- [ ] Forward selected fields over Meshtastic (custom payload — not a native telemetry type)
- [ ] OPEN: which port for monitoring (USB vs RS485 expansion) without colliding with ShineWiFi /
      the inverter↔battery BMS link; confirm Growatt protocol # for the EG4 (LCD Program 36)

**Phase 3 — shelf weights (custom subsystem):**
- [ ] Per-shelf weights, **2–4 scales** (decided 2026-06-07) — load cells + one HX711 per shelf
- [ ] Companion MCU (existing ESP32-S3) reads HX711s + RS485 Modbus, injects into mesh via Heltec

**Architecture (TBD, discuss w/ SwampNet)**: a **companion ESP32-S3 sensor aggregator** is the
natural hub — it reads load cells (HX711), weather (BME280), and the power system (MAX485/Modbus),
then injects a combined payload into the mesh via the Heltec V3's serial API, keeping the radio on
stock Meshtastic. Door + weather stay native Meshtastic modules (Phase 1). Firmware fork
(stock+companion vs full custom RadioLib) still undecided — needs SwampNet input + a serial-injection
spike. The sensor node draws 5V off the 48V battery via a buck converter (power budget now a
non-issue — it sips from the big system).

### Improvements
- [x] Persistent count storage (survives power loss) (2026-11-14)
- [x] Web dashboard for viewing count: `https://hollygrovenola.org/fridge/` (2026-11-14)
- [ ] Battery power option with deep sleep

### Deployment
- [ ] Weather-proof enclosure
- [ ] Field testing at community fridge
- [ ] Final installation

---

## Session Log

### 2026-11-14 - Overnight Build: Firmware, Wiring, Server, Dashboard, Demo Door, Case

**Summary**:
- Michael asked for six deliverables to be designed and built overnight without consulting him,
  with a log of decisions to review in the morning. That log is `DECISIONS-FOR-MICHAEL.md`; each
  agent's detailed list is in `docs\decisions\`. The work was split across agents and checked by
  the lead session. Partway through, at Michael's request, the agents were moved to leaner models
  without reducing scope.
- **Firmware** (`src\`, `include\`, `docs\firmware.md`): rewritten. Door sampling runs in its own
  task with a 50 ms debounce; each opening is an event with time and duration; events are kept in
  a flash journal through outages and resent; a heartbeat goes every 15 minutes. The sending
  method sits behind one interface: WiFi (`esp32s3` build) and Walter LTE-M (`walter` build, which
  compiles but has never run on a Walter). BMP280, DS18B20, DHT and HX711 support is built in and
  stays dormant when nothing is attached. The Pico 2W code moved to `legacy\`.
- **Tested on the real board** (a DevKitC-style ESP32-S3, 16 MB flash, on COM8): 39 of 39 unit
  tests passed on the board; against the live server over HTTPS it posted heartbeats and simulated
  openings (HTTP 200), and a deliberate resend came back as a duplicate. Against a local stand-in:
  events survived a reset and server outages. Not tested: a real reed switch, real sensors, the
  LED colours, a Walter board.
- **Wiring** (`docs\wiring\wiring-diagram.svg`, `wiring.md`): one pin map for all boards: reed
  switch GPIO4, DS18B20 GPIO5, DHT GPIO6, I2C GPIO8/9, RS485 reserved GPIO16-18, HX711 clock
  GPIO42 and data GPIO41/40/39/38.
- **Server** (`server\`): FastAPI + SQLite service, 47 tests passing locally, deployed to the
  hollygrove VM as container `hollygrove-fridge`. The public API gives hourly totals or coarser.
  The deployment is recorded in the hollygrove log, Session 17
  (`\\10.0.10.13\hollygrove\project-log.md`).
- **Dashboard**: live at `https://hollygrovenola.org/fridge/`, empty until a field unit reports;
  `?demo=1` shows sample data. Not linked from the site's navigation.
- **Demo door** (`cad\demo-door\`): 152.4 mm tall, 50.8 mm deep entry, print-in-place cone hinge
  (Nick Johnson's, CC BY-SA), press-fit mounts for the Gebildet recessed switch, and a second
  variant for a surface-mount pair. Checked numerically only. The bare frame tips at a pull of
  about 0.3 N at the knob, so a separate base plate (`demo-door-foot-rev1.stl`, held by two zip
  ties, with wells for 16 quarters) was added; with it the computed tip-over force is about 1.7 N,
  or 2.1 N with the coins. It slides at about 0.55 N, so it needs rubber feet.
- **Case and power** (`cad\enclosure\`, `docs\power-and-enclosure.md`): a printable case in two
  variants (Freenove on its breakout; DevKitC on the Universal breakout), a sled for a Hammond
  1554H2GY weatherproof box, and a power plan (USB adapter on the inverter output first; an
  isolated Mean Well DDR-15L-5 on the 48 V bus later). The LM2596 modules must not go on the
  48 V battery. Nothing printed; several dimensions need a caliper check.
- **Parts confirmed from order emails**: Gebildet recessed reed switches (5), BMP280 modules (5),
  three generic ESP32-S3 DevKitC N16R8 boards, two Freenove ESP32-S3 boards, three Freenove
  screw-terminal breakouts. Not owned: DS18B20, HX711, load cells, junction box, glands.

**Changes outside this folder**:
- hollygrove VM: new container, `fridge/` folder, Caddy route, page `site/fridge/index.qmd`.
- This PC: a second PlatformIO folder `C:\Users\micha\.platformio-walter` for the Walter build,
  and a few Python helper packages added to PlatformIO's own environment during a repair.
- The board's original flash contents are saved at
  `\\TRUENAS\Pyle-TNAS_Backups\BackUp - Projects\Microcontrollers\esp32-fridge-counter\`.
- Nothing was committed or pushed.

**Open Questions**: see `DECISIONS-FOR-MICHAEL.md`.

**Owner's answers, same day (morning)**:
- Direction: WiFi now, LTE later. WiFi is for testing at the house; nothing is deployed to the
  fridge until the Walter arrives. Bench board: the generic DevKitC. Deployment board: Walter.
- Dashboard: the charts belong at `/fridge/` itself, not one click further in. The page now shows
  the full dashboard with clearly marked sample data until real counts exist, then switches by
  itself. A first attempt at this change broke the page for a few minutes (the sample-data
  generator was only built when the page was opened with `?demo=1`); fixed and checked on the live
  site at desktop width.
- Publishing lag shortened from one hour to 15 minutes (`FRIDGE_PUBLISH_GRANULARITY_S=900` in the
  VM's `fridge.env`).
- No navbar link yet. No M3 inserts or screws on hand: added to the to-buy list.
- Commit and push approved; merged into `main` and pushed.
- Backups: the owner chose "snapshot the whole VM". TrueNAS now snapshots the hollygrove VM disk
  daily (kept 14 days) and the VM makes a nightly clean copy of the fridge database. Details in
  the hollygrove log, Session 17. Both are on the same storage pool as the VM.

---

### 2026-11-05 - Walter Cellular Module Researched (documented as a possibility)

**Summary**:
- Michael found the **Walter** board (QuickSpot/DPTechnics) and asked for it to be researched and
  documented as a communication option. It is an ESP32-S3 plus Sequans GM02SP LTE-M/NB-IoT modem
  and GNSS on one certified board. It has no LoRa, so it does not replace the Meshtastic plan.
- Added **Option 9** to `build-out-tutorial.md` with specs, roles, cautions, software support, cost
  and sources, and a pointer in the Recommendation. Added a row to the connectivity table and a
  to-do below.
- Findings that matter: 9.5 µA deep sleep; VIN is 3.0-5.5 V with no overvoltage protection (the
  48 V battery needs a clean buck to 5 V); Verizon-approved, but **no AT&T approval found**; the
  optional Walter Feels carrier has RS485 (useful for the Growatt/EG4 Modbus plan) but cannot
  sit directly on the 48 V pack; LTE-M coverage in Hollygrove and the 1NCE US carrier are unverified;
  bare-module USD price not confirmed (EUR 59 list; Mouser DevKit $310).
- Datasheet rev 1.2 (2026-11-04) was read in full. Nothing was purchased or changed on hardware.

**Open Questions**:
- Does LTE-M reach 9000 Oleander on a 1NCE or Soracom SIM, and on which US network?
- Is Walter worth a DevKit purchase as a fallback, or does the mesh path make it unnecessary?
- Could Walter replace the companion ESP32-S3 aggregator in the Phase 2-3 design?

**Files Changed**:
- `build-out-tutorial.md` - Added Option 9 (Walter); updated Recommendation
- `project-log.md` - This entry, connectivity table row, to-do

---

### 2026-06-11 - Real Power System Identified; Telemetry Architecture Revised

**Summary**:
- Two equipment manuals added to `research/`, defining the actual off-grid power system at the
  fridge site (this powers the **fridge appliance**, not just the sensor node):
  - **EG4 LifePower4 48V** — server-rack **LiFePO4** battery w/ high-precision BMS (per-cell V,
    current, temp, SoC). Comms over **RS485**; up to 16 modules parallel; "Host" battery (DIP ID 0)
    bridges to inverter via RS485/CAT5 or closed-loop CAN.
  - **Growatt SPF 3000TL LVM** — 3000W off-grid solar **inverter/charger**. Ports: **USB**,
    **RS485 expansion**, **BMS CAN/RS485**, optional WiFi/GPRS (ShineWiFi). Speaks Growatt
    **Modbus** — already aggregates PV power, battery V/current, load, AC output, daily kWh.
- **Architecture impact**: "solar + converter data" is no longer hobby INA3221 shunts. We read the
  equipment's own telemetry buses:
  - Growatt inverter via **Modbus RTU** (ESP32 + MAX485 on RS485 expansion port, or USB) — richest
    single source. Open-source register maps exist (grott, growatt2mqtt, ESPHome growatt).
  - EG4 BMS via **RS485** for cell-level detail/SoC.
- **Power budget for the sensor node is now moot** — it taps 5V off the 48V battery via a buck
  converter instead of needing its own panel/18650.
- Reorganized sensor plan into Phase 1 (native Meshtastic: door + weather), Phase 2 (power-system
  Modbus/RS485 telemetry), Phase 3 (per-shelf weights). A **companion ESP32-S3 aggregator** reads
  HX711 + BME280 + MAX485/Modbus and injects into the mesh via the Heltec serial API.

**Open Questions**:
- Which Growatt port to tap for monitoring (USB vs RS485 expansion) without colliding with the
  inverter↔battery BMS link or a ShineWiFi dongle?
- Which Growatt protocol # matches the EG4 BMS (inverter LCD Program 36)?
- Is the AC fridge load itself in scope for monitoring, or just PV/battery health?

**Files Changed**:
- `research/` - Added EG4 LifePower4 + Growatt SPF 3000TL manuals
- `project-log.md` - This entry + revised Sensors/Telemetry phases
- `build-out-tutorial.md` - Noted power-system telemetry path
- `SWAMPNET-BRIEF.md` / `SWAMPNET-EMAIL.md` - Updated power telemetry, prepared outreach email

---

### 2026-06-07 - Pivot to Mesh-Only; SwampNet Partnership; Sensor Scope Expansion

**Summary**:
- **DECISION: Pivoting to Meshtastic/LoRa entirely.** Dropping the WiFi connectivity path. The
  existing `src/main.cpp` (WiFi always-on + HTTP POST, no sleep) is now legacy — it idles at
  ~80–120 mA, which is incompatible with the solar/battery budget at the fridge site. Mesh deletes
  that draw (LoRa idle ~8–12 mA always-listening, ~0.13 mA deep-sleep).
- **Partner: SwampNet ([swampnet.info](https://swampnet.info))** — New Orleans mutual-aid Meshtastic
  network with local RF expertise. They'll handle site survey + node setup, and may let us join an
  existing community mesh (possibly removing the need for our own gateway). Engage early.
- **Site link analysis**: 8430 Apple St (gateway, ~3 stories) ↔ 9000 Oleander (fridge, ~2 stories)
  = **~694 m / 0.43 mi**. Short urban hop. LOS not strictly required at this range but is the
  dominant factor; 1st Fresnel radius ~7.5 m at midpoint. Antennas at 2–3 stories should clear most
  Hollygrove 1–2-story rooftops. SwampNet to confirm with an empirical RSSI/SNR test.
- **Scope expansion — fridge node now a multi-sensor telemetry node**, all reported over Meshtastic:
  1. **Door open count** (reed switch) — original goal
  2. **Shelf weights** — load cells (HX711 amps) under shelves → inventory/stock level
  3. **Solar/power telemetry** — panel voltage, battery voltage/SoC, charge current from the
     solar charge controller / INA-series sensor
  4. **Weather** — ambient temp/humidity (+ optionally pressure) at the fridge site

**Power note**: Power budget figures (WiFi vs LoRa-always-on vs LoRa-deep-sleep) gathered. Adding
always-on sensors (load cells, weather, power monitor) pushes toward the always-listening profile
(~10–15 mA) rather than pure deep-sleep; size solar/battery accordingly (~5 W panel + 18650(s)).

**Open Questions**:
- Stock Meshtastic firmware (telemetry modules + serial sensor) vs custom RadioLib firmware for the
  multi-sensor payload? Stock is simpler but rigid; custom gives full control of the payload.
- How many shelves / load cells, and required weight resolution?
- Which solar charge controller? (determines whether power telemetry comes from the controller
  directly or a separate INA226/INA3221 sensor)

**Files Changed**:
- `build-out-tutorial.md` - Added SwampNet partner + Hollygrove site-link/LOS analysis to Option 8
- `project-log.md` - This entry

---

### 2026-05-26 - Cellular/eSIM Research (doc correction)

**Summary**:
- Corrected the "cellular requires a Raspberry Pi" error in the tutorial. ESP32 talks to a
  cellular modem over UART directly via the TinyGSM library — no Pi needed.
- Researched modem options: SIM7080G (Cat-M1/NB-IoT) is the right fit for low-data/low-power
  door counting. LILYGO T-SIM7000G is an easy all-in-one ESP32+modem board.
- Documented eSIM/eUICC vs physical SIM tradeoffs; soldered eSIM preferred for the sealed
  outdoor enclosure (no corrodible slot, remote carrier reprovisioning).
- Recommended 1NCE IoT Lifetime Flat (~$14 / 500MB / 10yr, no monthly fee) as the data plan.
- Reframed cost: cellular path (~$25-40 board + ~$14 SIM) is likely cheaper over device
  lifetime than the $130 WiFi-bridge option.

- **DECISION: LoRa Mesh / Meshtastic is the leading direction for connectivity.** Added as
  tutorial Option 8. Fridge node = Heltec V3 (~$25); gateway = **B&Q Station G2 (~$109)**, a
  high-power backbone base station with an elevated outdoor antenna (not a dev board). Self-host
  MQTT + Node-RED on TrueNAS for a fully private, zero-fee pipeline. Cellular (Option 7) demoted to
  the fallback if no base station is reachable in LoRa range.
- Note: Station G2 at full 35 dBm power in the US requires a ham license (can run lower without).

**Files Changed**:
- `build-out-tutorial.md` - Rewrote Option 7 (cellular), added Option 8 (Meshtastic), updated recommendation
- `project-log.md` - Updated connectivity options table (Meshtastic now top option)

**Open Questions** (for connectivity decision):
- Meshtastic: is there an internet-connected gateway node reachable within ~1-3km of the fridge,
  or an existing community mesh covering the site? (verify before buying)
- Is there WiFi at the fridge site? (would simplify everything if yes)

---

### 2026-01-21 - ESP32-S3 Reed Switch Working

**Summary**:
- Reed switches arrived and wired to ESP32-S3 (GPIO4 + GND)
- Fixed serial monitor configuration (removed incorrect USB CDC flags)
- ESP32-S3 successfully counting door opens via WiFi

**Device Status**:
| Device | Port | Status |
|--------|------|--------|
| ESP32-S3 | COM9 | ✓ Counting door opens, WiFi connected |
| Pico 2W | COM8 | Pending - needs reed switch wiring/testing |

**Config Fix**:
- Removed `-DARDUINO_USB_MODE=1` and `-DARDUINO_USB_CDC_ON_BOOT=1` from platformio.ini
- Added explicit `monitor_port = COM9` and `upload_port = COM9`
- Serial output now works reliably on UART port

**Next Session**:
- Get Pico 2W working with reed switch
- Test both devices running standalone (off USB, powered separately)
- Set up data logging server (explore TrueNAS options via SSH)

---

### 2026-01-19 - Devices Ready for Testing

**Summary**:
- Configured WiFi credentials via `secrets.h` (gitignored)
- Rebuilt and uploaded firmware to both devices
- Both devices running and ready for reed switches tomorrow
- Set up git repo with secrets pattern
- Documented 7 data logging options in tutorial

**Device Status**:
| Device | Port | WiFi | Status |
|--------|------|------|--------|
| Pico 2W | COM8 | Hermes | Ready for reed switch |
| ESP32-S3 | COM9 | Hermes | Ready for reed switch |

**Files Added**:
- `include/secrets.h` - WiFi credentials (gitignored)
- `include/secrets.h.example` - Template for others

**Git**:
- Repo: https://github.com/michaelbpyle/esp32-fridge-counter
- Initial commit + secrets pattern pushed
- secrets.h excluded from repo

**Tomorrow**:
- Reed switches arrive
- Wire to GPIO4 (ESP32) or GP15 (Pico) + GND
- Test door counting

---

### 2026-01-19 - Firmware Upload and Data Planning

**Summary**:
- Uploaded firmware to both devices successfully
- Pico 2W: COM8 (copied .uf2 to bootloader drive E:)
- ESP32-S3: COM9 (uploaded via PlatformIO)
- Added shopping list from original project doc
- Documented 7 data logging backend options

**Data Logging Options Evaluated**:
1. Google Sheets (recommended for simplicity)
2. Supabase/Firebase
3. InfluxDB + Grafana
4. Home Assistant
5. MQTT Broker
6. VPS + REST API
7. Cellular + Cloud (no WiFi needed)

---

### 2026-01-19 - Build Environment Complete

**Summary**:
- Fixed Windows path-length build issue (changed build dir to `.b`)
- Configured Freenove ESP32-S3 WROOM as the ESP32 target board
- Researched and documented ESP32-S3 safe GPIO pins
- Both firmwares now compile successfully

**Build Results**:
| Platform | Flash | RAM | Output |
|----------|-------|-----|--------|
| Pico 2W | 8.6% | 13.8% | `.b/pico2w/firmware.uf2` |
| ESP32-S3 | 20.3% | 13.2% | `.b/esp32s3/firmware.bin` |

**Files Changed**:
- `platformio.ini` - Added `build_dir = .b`, changed ESP32 board to `freenove_esp32_s3_wroom`
- `esp32s3-WIRING.txt` - Updated for Freenove board with GPIO reference

**Next Steps**:
- Edit `include/config.h` with WiFi credentials
- Wire reed switch to hardware
- Upload and test

---

### 2026-01-19 - Dual Platform Setup (continued)

**Summary**:
- Installed PlatformIO extension in VS Code
- Set up dual-platform support (Pico 2W + ESP32-S3)
- Single codebase with conditional compilation
- Updated all documentation for both platforms

**Files Changed**:
- `platformio.ini` - Added both `pico2w` and `esp32s3` environments
- `include/config.h` - Platform-specific pin definitions
- `src/main.cpp` - Conditional compilation for both platforms
- `pico2w-WIRING.txt` - New wiring reference for Pico 2W
- `esp32s3-WIRING.txt` - Restored wiring reference for ESP32-S3
- Removed old `TUTORIAL.md` (superseded by `build-out-tutorial.md`)

**Build Commands**:
- `pio run -e pico2w` - Build for Pico 2W
- `pio run -e esp32s3` - Build for ESP32-S3

---

### 2026-01-19 - Project Review and Organization

**Participants**: User + Claude

**Summary**:
- Reviewed all existing documentation (TUTORIAL.md, wiring reference, code)
- Discussed switching from ESP32-S3 to RPi Pico 2W for standardized pinouts
- Created project management structure:
  - `project-log.md` (this file) - task tracking and session history
  - `build-out-tutorial.md` - implementation plan and build instructions

**Current State**:
- Existing code targets ESP32-S3-DevKitM-1
- PlatformIO project structure in place
- Basic functionality implemented: reed switch reading, debounce, WiFi, HTTP POST

**Decisions Made**:
- Considering RPi Pico 2W as alternative to ESP32-S3
- Both platforms viable for this simple use case

**Next Steps**:
- Decide on final microcontroller
- Update build tutorial with chosen platform
- Test hardware

---
