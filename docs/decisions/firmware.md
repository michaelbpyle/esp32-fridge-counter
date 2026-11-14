# Firmware decisions

Decisions taken while writing the door-counter firmware and wiring (November 2026), mostly while the owner was not available. Each one says what was chosen, why, the main alternative, and what the owner should confirm. Folder: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter`.

## 1. The bench board is a DevKitC-1 style board, not a Freenove

- Choice: treat the connected board (MAC 30:ed:a0:b8:9e:68, 16 MB flash, 8 MB PSRAM, CH343 USB chip) as one of the "AYWHP ESP32-S3-DevKitC-1 N16R8" boards, 22 pins per side.
- Why: its factory MicroPython demo drove an RGB LED on GPIO48, and GPIO38 to 40 float (a Freenove WROOM has SD-card pull-ups there).
- Alternative: Freenove ESP32-S3 WROOM / Board Lite (20 pins per side).
- Confirm: count the pins on one side (22 = DevKitC, 20 = Freenove). The firmware is the same either way; only the breakout choice (decision 4) depends on it.

## 2. One pin map for every board

- Choice: reed 4, DS18B20 5, DHT 6, I2C 8/9, RS485 reserved 16/17/18, HX711 clock 42 and data 41/40/39/38, LED 48 (none on Walter).
- Why: these GPIO numbers exist and are free on the DevKitC-1 style board, the Freenove ESP32-S3 WROOM and Walter, and avoid the strapping pins (0, 3, 45, 46), the PSRAM pins (35 to 37), USB (19, 20), the serial console (43, 44) and Walter's modem pins (14, 21, 45, 47, 48). So one firmware and one wiring diagram serve all three. GPIO7 and 10 to 14 stay free for later (7 and 10 can read analogue values while WiFi runs).
- Alternative: HX711 on GPIO7 and 10 to 13 (an earlier draft), which would have used up the spare analogue-capable pins.
- Cost: on the Freenove board GPIO38 to 40 also go to its microSD slot, so the slot must stay empty if HX711 scales #2 to #4 are fitted; on a genuine Espressif DevKitC-1 v1.1, GPIO38 is the LED.
- Confirm: nothing unless a Freenove with SD card or a genuine Espressif board is used.

## 3. The Freenove "Board Lite" is assumed to have the Freenove ESP32-S3 WROOM pinout

- Choice: the only Freenove documentation on hand (`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\Freenove\Freenove_ESP32_S3_WROOM_Board-main`) is for the "Freenove ESP32-S3 WROOM" board; its pinout was used for the "Freenove ESP32-S3 Board Lite".
- Why: no Lite-specific documents were available and nobody could look at the board.
- Confirm: that the Lite's pin labels match `ESP32S3_Pinout.png` in that folder (left column 3V3, RST, 4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 46, 9 ... 14, 5V). If the Lite has no microSD slot, the SD caution simply does not apply.

## 4. Which screw-terminal breakout goes with which board

- Choice: Freenove Breakout Board for ESP32/ESP32-S3 (FNK0091) with the Freenove boards; Freenove Universal Breakout Board (FNK0101) with the DevKitC-1 style board.
- Why: FNK0091 has 20 labelled sockets per side matching the Freenove WROOM pinout; the 22-pin DevKitC does not fit it. Freenove's FNK0101 documentation says it accepts any board whose rows are 600 to 1000 mil apart, in any position.
- Confirm: measure the DevKitC's row spacing (must be 25.4 mm or less) before pressing it into the Universal board.

## 5. One 8 MB flash layout for both module sizes; PSRAM unused

- Choice: the `esp32s3` build uses the `default_8MB.csv` partition table even on the 16 MB board.
- Why: the same file then runs on N8R8 and N16R8 modules; the firmware needs about 1 MB of the 3.3 MB program slot. PSRAM is not needed (about 240 KB of internal RAM stays free).
- Alternative: a 16 MB layout (more space for a future over-the-air update scheme).
- Confirm: nothing now.

## 6. Arduino core 2.0.17 for the WiFi build, a different platform for Walter

- Choice: `esp32s3` is pinned to PlatformIO `espressif32@6.12.0` (Arduino core 2.0.17). `walter` uses the community "pioarduino" platform release 54.03.21 (Arduino core 3.2.1).
- Why: 6.12.0 is the mature, PlatformIO-supported platform and the WiFi build was proven on it. WalterModem 1.6.1 includes headers that exist only in core 3.x, which PlatformIO's own platform does not offer. Release 55.x of pioarduino needs PlatformIO Core 6.2 or newer; the PC has 6.1.19, and upgrading the shared PlatformIO install overnight could have broken the proven WiFi build, so the older 54.03.21 release was used.
- Isolation: the first `walter` build installed pioarduino into the shared folder `C:\Users\micha\.platformio`, where it replaced packages of the same name and broke the `esp32s3` build (its uploader then lacked the `intelhex` module). Repaired the same morning: the pioarduino platform and its four packages were moved to `C:\Users\micha\.platformio-walter`, the original platform folder name was restored, and the uploader's own set-up script was re-run, which installed its Python helpers (intelhex, cryptography, ecdsa, bitstring, reedsolo) into that package's `_contrib` folder. The `esp32s3` build was then rebuilt, uploaded and tested. The `walter` build must always be run with `PLATFORMIO_CORE_DIR` set to the separate folder (see `docs\firmware.md`).
- Side effects that could not be kept out of the shared folder: pioarduino also wrote `C:\Users\micha\.platformio\tools\` (its compiler), `C:\Users\micha\.platformio\idf-env.json`, and installed its "Arduino Python dependencies" (for example `rich-click`) into PlatformIO's Python environment `C:\Users\micha\.platformio\penv`. The `esp32s3` build was rebuilt from scratch afterwards and still succeeds with the same size.
- The platform's own uploader package (esptool 5.0.0-dev1) crashes with the Click 8.3 library in that Python environment, so the `walter` environment pins pioarduino esptool 5.1.0 instead (`platform_packages` in `platformio.ini`), which supports it. With that, `pio run -e walter` succeeds: 118420 bytes RAM (36.1 %), 1071886 bytes flash (16.4 % of a 6.25 MB app slot).
- Confirm: nothing. When PlatformIO is upgraded some day, the `walter` platform line can move to a newer release.

## 7. Door sampling in its own high-priority task, 50 ms stable-time debounce

- Choice: a FreeRTOS task on core 1 at priority 10 samples GPIO4 every 2 ms; a change counts only after the input has held the new level for 50 ms without interruption. The opening time is the first edge.
- Why: the main loop can be busy for many seconds in HTTPS or retries; the task pre-empts it, so no opening is missed (seen on the board: an opening during an 8 s failed POST was timed correctly). A stable-time debounce never swallows a genuine edge and rejects contact bounce and short electrical spikes.
- Alternative: GPIO interrupts. Rejected: a bouncing reed switch fires bursts of interrupts and still needs a timer to debounce.
- Confirm: 50 ms suits the real switch. If short real openings are being missed (very unlikely for a fridge door) lower `DOOR_DEBOUNCE_MS`.

## 8. A door open at start-up is not counted

- Choice: if the door reads open at power-up, counting starts only after it first closes.
- Why: the device did not see the opening start, so it cannot time it, and counting it would add a phantom opening after every power cut that happened with the door open.
- Confirm: nothing.

## 9. Held-open doors

- Choice: an opening is added to `door_total` when it starts. If the door stays open longer than 10 minutes, one event with `dur_ms: -1` is sent at the 10-minute mark; when it finally closes, nothing more is sent.
- Why: matches the server contract; the server learns promptly that the door is stuck open.
- Confirm: 10 minutes (`DOOR_HELD_OPEN_LIMIT_MS`) is the right threshold for the fridge.

## 10. The `sim` test command plays a whole shut-open-shut sequence

- Choice: `sim [ms]` feeds "shut, open for ms, shut" into the real debounce and counting code while ignoring the pin, then re-reads the pin as if just started (so an "open" pin afterwards is not counted).
- Why: with no reed switch attached, GPIO4 floats HIGH (the pull-up), which reads as "door open"; the earlier version only forced "open" and therefore produced no event at all. The new version works with or without a switch.
- Cost: a real opening that happens during a simulation is not seen. It is a bench command only.

## 11. Store-and-forward queue in a LittleFS journal

- Choice: up to 500 events, kept in RAM and in an append-only, checksummed journal file; acknowledgements are appended; the file is compacted at 1000 records or when emptied. When full, the oldest event is dropped and a lifetime drop counter (kept in NVS, sent as `status.dropped`) goes up.
- Why: one small append per event and per POST is gentle on flash; a power cut can lose at most the record being written. Keeping the newest data is more useful than keeping the oldest if an outage lasts beyond 500 openings (about three days of typical use).
- Alternative: NVS blobs (whole-queue rewrites on every event: much more flash wear).
- Confirm: 500 events is enough for the longest outage you expect.

## 12. Sensor readings are not stored in flash

- Choice: readings wait in a RAM buffer of 96 (oldest dropped) and are lost on a restart.
- Why: they are not the core data, and writing them would multiply flash writes. At one sample every 5 minutes, 96 slots hold several hours of readings for one or two sensors.
- Confirm: acceptable.

## 13. How server answers are handled

- Choice: 200 with `"ok":true` removes the batch; 400 discards the batch (events and readings) and logs it loudly; 401 and 403 keep everything and retry every 15 minutes; everything else (404, 5xx, a 200 with an unreadable body, timeouts) keeps everything and retries with exponential backoff from about 5 s up to 15 minutes, with plus or minus 25 % random jitter.
- Why: as the contract says; treating 403 like 401 because both mean "not allowed"; jitter stops several devices retrying in lockstep. Discarding on 400 is the contract's rule and stops one bad batch blocking the queue forever; the count of discarded events is shown in `status`.
- Confirm: nothing.

## 14. Clock

- Choice: WiFi build: NTP (pool.ntp.org, time.cloudflare.com, time.google.com), UTC only. Walter: the cellular network's time. In both, the server's `server_time` sets the clock only if it has not been set yet. Events whose clock was unknown are sent with `t: 0` and `age_s`; if the clock becomes known before they are sent in the same boot, the real time is filled in.
- Why: NTP is more accurate than a single HTTP round trip; `server_time` is a fallback for networks that block NTP.
- Confirm: nothing.

## 15. HTTPS checked against the built-in root-certificate bundle

- Choice: the WiFi build checks the server against the Mozilla CA bundle compiled into the Arduino core, not a single pinned certificate.
- Why: the site sits behind Cloudflare, which can change certificate authority at any time; the bundle keeps working through such changes while still rejecting impostors. Insecure mode is not used anywhere.
- Alternative: pinning one root (what Walter has to do, decision 16).
- Confirm: nothing.

## 16. Walter limitations accepted

- Choice: Walter's modem does HTTP and TLS itself. Its HTTP command takes one extra header, so `X-Device-Key` is sent and `User-Agent` is not; it holds one root certificate, ISRG Root X1 (Let's Encrypt), stored once in the modem. The uplink name sent is `lte-m`.
- Why: the alternative (raw TCP sockets on the modem and TLS on the ESP32) is far more code and untestable without hardware.
- Confirm: the server accepts requests without the `User-Agent` header and the `uplink` value `lte-m`. If Cloudflare serves a non-Let's Encrypt certificate to Walter, its TLS will fail; update `src\uplink\walter_ca.h`.
- Not verified: the Walter code has never run on a Walter; its header layout and power pins were not checked against a Walter pinout card (none on hand).

## 17. Bench mode with plain HTTP is a separate build, off by default

- Choice: the `esp32s3_dev` environment, and only when the `FRIDGE_DEV_HOST` environment variable is set, sends plain HTTP to a receiver on the local network. The default `esp32s3` build has no such path compiled in.
- Why: the requirement that plain HTTP is never on by default, and that the device never talks to any other public endpoint.

## 18. Unit tests run on the board, not on the PC

- Choice: the 39 tests of `lib\fridge_core` run on the ESP32 (`pio test -e esp32s3`); the `native` (PC) test environment is kept but cannot run.
- Why: this PC has no C++ compiler (no gcc, clang or MSVC). Installing one (for example MSYS2 with MinGW, several hundred MB) was not needed, because the logic is free of Arduino headers and the tests pass on the real chip. Nothing was installed for this.
- Confirm: if PC-side tests are wanted, install MinGW-w64 and run `pio test -e native`.

## 19. Status LED on the board's addressable RGB LED

- Choice: drive the WS2812-type LED on GPIO48 with the core's RMT-based `neopixelWrite`, at brightness 24 of 255, from its own low-priority task. Disabled on Walter.
- Why: an addressable LED needs a timed data stream, not on/off levels; the dedicated task keeps blinking even while the main loop waits on the network.
- Confirm: that the LED is visible enough through the enclosure (raise `STATUS_LED_BRIGHTNESS` if not).

## 20. Watchdog of 120 seconds

- Choice: task watchdog on the main loop and the door task, 120 s, restart on expiry.
- Why: the slowest normal operation (a TLS handshake plus a response timeout, or a Walter POST) takes well under a minute; 120 s leaves margin while still recovering from a hang in two minutes.

## 21. Bench and field identities

- Choice: the board on the bench reports as `bench-01` (the server keeps its data out of public numbers); the field unit will be `fridge-01`, whose key lives on the hollygrove VM in `/opt/hollygrove/fridge/fridge.env`.
- Why: requested by the project lead once the server went live.
- Confirm: when the field unit is built, `include\secrets.h` on that PC gets `fridge-01` and its key.

## 22. Test commands `sim` and `resend` stay in the field firmware

- Choice: both commands are always compiled in.
- Why: they only work from the USB serial port, which needs physical access, and they make on-site checks possible. `resend` re-queues the last delivered batch so the server's duplicate detection can be checked from the real device.
- Confirm: nothing.

## 23. Pico 2W path retired to `legacy\`

- Choice: the first sketch (Pico 2W and ESP32-S3, single file) and the two old `*-WIRING.txt` notes moved to `legacy\`; there is no Pico build any more.
- Why: keeping a second chip family building would have doubled the work for every feature, and the project has standardised on the ESP32-S3.
