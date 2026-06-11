# Hollygrove Community Fridge — Sensor Node Brief for SwampNet

**Prepared:** 2026-06-07 · **Contact:** Michael Pyle (michael.b.pyle@gmail.com)

## What this is
A solar/battery-powered **Meshtastic sensor node** at the Hollygrove Community Fridge that reports
usage and status over LoRa — no WiFi, no SIM, no recurring cost. We'd love SwampNet's help siting,
setting up, and (ideally) connecting it into the existing New Orleans mesh.

## What we're asking of SwampNet
1. **Site survey / link test** — confirm the LoRa hop below actually works (empirical RSSI/SNR).
2. **Mesh integration** — can this node join your existing mesh, or do we stand up our own
   internet-connected gateway? If yours covers Hollygrove, we'd rather not duplicate it.
3. **Firmware/architecture gut-check** — one open technical question below on custom sensor data.
4. **Setup help** — node config, antenna mounting, MQTT bridge to our self-hosted server (TrueNAS).

## The link (the main thing to validate)
| | Site | Address | Antenna height available |
|---|---|---|---|
| Gateway / relay | Apple St | **8430 Apple St** | up to **~3 stories** |
| Fridge node | Oleander | **9000 Oleander** | up to **~2 stories** |

- **Distance: ~694 m (0.43 mi)** — short urban hop, 915 MHz.
- **Line of sight:** not strictly required at this range, but the dominant factor. First Fresnel zone
  is only **~7.5 m radius at midpoint** (~4.5 m for 60% clearance). At 3 / 2 stories both antennas
  should clear most surrounding 1–2-story rooftops + tree canopy in Hollygrove.
- **Ask:** does this link close reliably at these mount heights? Worth a live walk-test before we
  commit to permanent mounts.

## Sensors we want to report
We're planning to phase this — start with what's native to Meshtastic, add the custom pieces after.

**Phase 1 — native Meshtastic modules (no custom code) on a Heltec WiFi LoRa 32 V3:**
| Data | Meshtastic module | Sensor |
|---|---|---|
| Door open count | Detection Sensor (GPIO) | reed switch |
| Weather (temp / humidity / pressure) | Environment Telemetry | BME280 (I²C) |

**Phase 2 — power-system telemetry (custom, reading real equipment):**
The fridge runs off a real off-grid system — an **EG4 LifePower4 48V LiFePO4** battery and a
**Growatt SPF 3000TL LVM** 3000W inverter/charger. We want PV power, battery V/SoC/current, and load
over the mesh. These expose their own buses, so we'd read them directly rather than add shunt sensors:
- Growatt inverter via **Modbus RTU** (RS485 expansion port or USB) — ESP32 + MAX485.
- EG4 BMS via **RS485** for cell-level detail/SoC.

**Phase 3 — per-shelf weights (custom):** 2–4 shelves for inventory/stock level — load cells + one
**HX711** amp per shelf. Not a native Meshtastic type.

A single **companion ESP32-S3** would aggregate Phases 2–3 (Modbus + load cells) and inject a combined
payload into the mesh via the Heltec's serial API, keeping the radio node on **stock Meshtastic**.

## The architecture question we'd love your read on
What's the cleanest way to get custom sensor data (power + weights) into the mesh?
- **Companion MCU + stock Meshtastic** — separate ESP32 feeds the Heltec over its **serial API**;
  radio stays stock. *Is serial injection of external data into stock Meshtastic reliable in your
  experience?*
- **Full custom RadioLib firmware** — one chip does everything; we lose native modules and you'd be
  supporting custom firmware.

## Power / deployment context
- The **sensor node sips 5V off the 48V battery** (buck converter) — its own draw is negligible, so
  no separate panel/cell needed for the electronics.
- Outdoor IP65 enclosure at the fridge; disable the Heltec OLED.
- Self-hosted backend: **MQTT + Node-RED on TrueNAS** — fully private, zero cloud, zero fees.

## Open questions for SwampNet
1. Does your existing mesh reach Hollygrove / the 9000 Oleander site? (avoids us needing a gateway)
2. Does the ~694 m Apple↔Oleander link close at 3 / 2-story mounts?
3. Companion-MCU-with-stock-Meshtastic vs full custom firmware for the power + weight data?
4. Any experience reading Growatt/EG4 over Modbus and bridging it onto a mesh?
5. Any preferred node hardware / antenna / mounting we should standardize on to fit your mesh?
