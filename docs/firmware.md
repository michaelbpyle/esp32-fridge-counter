# Firmware - Hollygrove Community Fridge door counter

Project folder: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter` (mapped as `I:\Projects\Microcontrollers\esp32-fridge-counter` on the Windows PC). Wiring is in `docs\wiring\wiring.md`; the reasons behind the design choices are in `docs\decisions\firmware.md`.

## What the firmware does

- Counts fridge-door openings with a reed switch on GPIO4. Each opening becomes an event with the time it opened and how long it stayed open. A door held open longer than 10 minutes is reported once with a duration of -1 and is not counted again until it has closed.
- Keeps a lifetime count of openings that survives power cuts.
- Stores every event in flash before trying to send it, so nothing is lost when the internet or the power goes out. Up to 500 events wait on the device; beyond that the oldest is dropped and a drop counter goes up.
- Sends events to `https://hollygrovenola.org/fridge/api/v1/ingest` in batches of up to 20, plus a heartbeat every 15 minutes, over HTTPS with the server certificate checked.
- Reads optional sensors (BMP280/BME280, DS18B20, DHT11/DHT22, HX711 scales) every 5 minutes if they are plugged in, and sends the readings with the next POST. Absent sensors are silent.
- Shows its state on the board's RGB LED and prints diagnostics on the USB serial port at 115200 baud.

## Device identity

Each device has a `DEVICE_ID` and a `DEVICE_KEY` in `include\secrets.h` (never committed to git; `include\secrets.h.example` is the template).

- The **bench** board (the one on the desk) is `bench-01`. The server stores its data but keeps it out of every public number, so testing never pollutes the fridge statistics.
- The **field** unit at the fridge is `fridge-01`. Its key is on the hollygrove server VM in `/opt/hollygrove/fridge/fridge.env`. Put it in `include\secrets.h` only on the PC that builds the field unit, and never use `fridge-01` on the bench.
- `SERVER_HOST` is `hollygrovenola.org` for both.

## How it is built

```text
 reed switch (GPIO4)
        |
        v
 +----------------------+   FreeRTOS queue   +-------------------------------+
 | door task (core 1,   | -----------------> | main loop (Arduino loop task) |
 | priority 10, 2 ms)   |   notices: opened, | - event queue in flash        |
 | debounce, timing,    |   closed, event    | - sensors every 5 min         |
 | held-open detection  |                    | - POST to server, retries     |
 +----------------------+                    | - serial console              |
                                             +-------------------------------+
 LED task (core 1, low priority): animates the RGB LED from a mode flag.
 WiFi, TCP/IP and TLS run in the system's own tasks on core 0.
```

### Door sampling keeps running during network I/O

The door is not read in the main loop. A separate FreeRTOS task, pinned to core 1 at priority 10 (higher than the main loop's priority 1), wakes every 2 ms with `vTaskDelayUntil`, reads GPIO4 and feeds the reading to a debouncer and a door state machine (`lib\fridge_core\src\fc_door.h`). When something happens it puts a small notice into a 64-entry FreeRTOS queue and goes back to sleep. A slow HTTPS POST, a flash write or a 5-second sensor read in the main loop therefore cannot delay or hide a door edge: the door task simply pre-empts the main loop. The main loop picks the notices up when it is free. Even a stall of more than a minute would fit in the 64-entry queue; a counter (`door notices lost` in `status`) proves it never overflowed.

This was seen working on the board: with the test receiver switched off, the main loop sat for 8 seconds in a POST that failed, and a simulated door opening that started during that POST was counted and timed correctly.

Debounce: the input must stay in its new state for 50 ms without interruption before it counts. Any bounce restarts the 50 ms. The reported opening time is the moment the input first changed, so durations are not shortened by the debounce.

### The event queue in flash

`lib\fridge_core\src\fc_queue.cpp` keeps the queue in RAM and mirrors it to a journal file (`/queue.jnl`) on the LittleFS partition:

- Each new event appends one 24-byte record with a checksum. Each successful POST appends one "acknowledged N events" record. A record is either fully written or ignored, so a power cut mid-write loses at most the record being written, never the file.
- At start-up the journal is replayed to rebuild the queue. A damaged record stops the replay at that point and the file is rewritten clean.
- The journal is rewritten from scratch (compacted) when it reaches 1000 records or when the queue empties after 32 or more records, so it never grows without limit.
- Flash wear: about 150 openings a day cost roughly 150 small appends plus one acknowledgement per POST. LittleFS spreads writes over its whole 1.5 MB partition. The lifetime counter is one small NVS write per opening; NVS also spreads its writes. Both are thousands of times below the flash's endurance over a 10-year life.

### Sending and retries

- A POST goes out 3 seconds after the last door event (so a quick open-shut-open burst is one POST), or at once when 20 events are waiting, or as a heartbeat every 15 minutes (immediately after start-up too).
- The server's answer decides what happens:

| Answer | What the device does |
| --- | --- |
| 200 with `"ok":true` | Removes the sent events; sets the clock from `server_time` if it has none yet. |
| 400 | The server says the batch is malformed. Discards that batch (otherwise it would block everything behind it) and logs it loudly. |
| 401 or 403 | Wrong device key. Keeps everything; retries every 15 minutes; LED blinks magenta. |
| 404, 5xx, timeouts, no network | Keeps everything; retries after about 5 s, 10 s, 20 s, 40 s... up to 15 minutes, with random jitter. |

- Timestamps: each event carries `t` (UTC time of opening, or 0 if the clock was not set) and `age_s` (seconds since the opening). An event from before a restart has no `age_s` if its time was unknown.

### Uplinks (WiFi or cellular)

All network code is behind one interface (`src\uplink\Uplink.h`: begin, loop, isConnected, postJson, epochNow, signalDbm, name). Which one is compiled is decided by the PlatformIO environment:

- `esp32s3` uses `src\uplink\WifiUplink.cpp`: up to three WiFi networks from `secrets.h` tried in turn, automatic reconnect, time from NTP, HTTPS checked against the Mozilla root-certificate bundle built into the ESP32 core.
- `walter` uses `src\uplink\WalterUplink.cpp`: the Walter board's LTE-M modem through the official WalterModem library. The modem does the TLS itself and checks the server against the ISRG Root X1 certificate in `src\uplink\walter_ca.h`. Time comes from the cellular network. See "Switching to Walter" below for its limits.

### Reliability

- Task watchdog: if the main loop or the door task stops for 120 seconds, the chip restarts itself. The reason for every restart (`poweron`, `task_wdt`, `brownout`, `panic`...) is printed at start-up and sent to the server as `status.reset_reason`. Note: pressing RST, or the reset done by an upload, is also reported as `poweron` on the ESP32-S3.
- WiFi drops are handled by the WiFi driver's own reconnect plus a fallback that moves to the next configured network after 15 seconds.
- A random `boot_id` per start-up lets the server tell restarts apart; every event is unique on (device, boot, n).

## Folder layout

| Path | Contents |
| --- | --- |
| `include\config.h` | Every setting (pins, timings, sensors on/off). |
| `include\secrets.h` | WiFi, device id and key, APN. Never committed. Template: `secrets.h.example`. |
| `src\main.cpp` | Start-up, main loop, sending, serial console. |
| `src\door_task.*` | The door sampling task. |
| `src\status_led.*` | RGB LED patterns. |
| `src\journal_fs.h` | Queue journal on LittleFS. |
| `src\uplink\` | WiFi and Walter transports. |
| `src\sensors\` | Sensor drivers and the registry. |
| `lib\fridge_core\` | Hardware-independent logic (debounce, door state, queue, JSON payload, response handling, backoff, sensor maths). No Arduino headers. |
| `test\test_core\` | 39 unit tests of `lib\fridge_core`. |
| `tools\` | Test receiver, fake device, wiring-diagram generator. |
| `legacy\` | The old single-file sketch for the Raspberry Pi Pico 2W and its wiring notes (not built any more). |

## Build, flash and monitor (step by step)

You need: the PC with PlatformIO installed (it is: `C:\Users\micha\.platformio\penv\Scripts\pio.exe`), a USB-C data cable, and the board.

1. Plug the cable into the board's USB-C port marked **UART** or **COM** (not the one marked USB).
2. Open PowerShell and go to the project:

   ```powershell
   cd I:\Projects\Microcontrollers\esp32-fridge-counter
   ```

   (`I:` is the TrueNAS share `\\TRUENAS\Pyle-TNAS_Individual` on this PC. Builds have only been tested from the `I:` path.)

3. Check which COM port the board has (look for the CH343 / "USB-Enhanced-SERIAL" line):

   ```powershell
   C:\Users\micha\.platformio\penv\Scripts\pio.exe device list
   ```

   If it is not `COM8`, change `upload_port`, `monitor_port` and `test_port` in `platformio.ini`.
4. Make sure `include\secrets.h` exists and holds your WiFi name and password, `SERVER_HOST`, `DEVICE_ID` and `DEVICE_KEY`. (Copy `include\secrets.h.example` if it is missing.)
5. Build and upload (takes 2 to 4 minutes the first time):

   ```powershell
   C:\Users\micha\.platformio\penv\Scripts\pio.exe run -e esp32s3 -t upload
   ```

6. Watch what it says:

   ```powershell
   C:\Users\micha\.platformio\penv\Scripts\pio.exe device monitor -p COM8 -b 115200
   ```

   Press the board's RST button to see the start-up messages. Type `status` and Enter at any time. Leave the monitor with Ctrl+C.

A healthy start looks like this (bench board, 2026-11-14):

```text
 Hollygrove Community Fridge door counter
 firmware 1.0.0, uplink: wifi
 device_id bench-01, boot_id ..., reset reason: poweron
[door] GPIO4 raw level HIGH -> door is OPEN at start-up; lifetime count ...
[queue] 0 event(s) restored from flash, 0 dropped lifetime
[wifi] trying network 1 of 1
[sensor] BMP280/BME280 (I2C): not connected (dormant)
...
[wifi] connected to network 1 of 1, IP 10.0.0.170, RSSI -60 dBm
[post] OK in ... ms: 0 event(s), 0 reading(s) sent; server accepted 0, duplicates 0; 0 still queued
```

Uploading replaces the program only. The lifetime count, the waiting events and the scale calibration are kept.

### Unit tests

The pure logic is tested on the board itself (this PC has no C++ compiler for PC-side tests; see the decisions file):

```powershell
C:\Users\micha\.platformio\penv\Scripts\pio.exe test -e esp32s3
```

This uploads a test program, so upload the real firmware again afterwards (step 5). Expected: 39 tests, all PASSED.

### Bench test without the real server

`tools\dev_receiver.py` is a small local stand-in for the server. The `esp32s3_dev` build sends plain, unencrypted HTTP to it instead of HTTPS to the real server. It is for the desk only.

```powershell
python tools\dev_receiver.py -v
$env:FRIDGE_DEV_HOST = "10.0.1.1"     # this PC's address on the board's network
C:\Users\micha\.platformio\penv\Scripts\pio.exe run -e esp32s3_dev -t upload
```

`python tools\dev_receiver.py --help` lists options for faking errors (`--always-status 404`, `--key` to force 401...). Always finish by uploading the normal `esp32s3` build again.

`tools\fake_device.py` pretends to be a device (standard-library Python, no board needed): `python tools\fake_device.py --base-url https://hollygrovenola.org --device-id bench-01 --key <bench-01 key> --count 5`. Use only the `bench-01` identity against the real server. `--backfill-days N` uploads N days of made-up history, for testing the server's charts on a test server.

## Serial commands

Type these in the serial monitor and press Enter.

| Command | What it does |
| --- | --- |
| `status` (or `s`) | Everything: door pin level, queue, link, clock, sensors, memory. |
| `sim [ms]` | Simulates one door opening of `ms` milliseconds (default 3000). Works with or without a reed switch connected. |
| `send` | Sends a heartbeat now. |
| `resend` | Test: sends the last delivered events again; the server must answer with "duplicates". |
| `sensors` | Reads all connected sensors now and prints the values. |
| `probe` | Looks again for sensors plugged in since start-up. |
| `scale` | Shows the HX711 scale channels. |
| `tare <1-4>` | Zeroes a scale with its shelf empty. |
| `cal <1-4> <grams>` | Calibrates a scale with a known weight on it. |
| `led` | Shows red, green, blue, white on the LED. |
| `pins` | Reads the spare pins (helps tell the board types apart). |
| `clearqueue` | Deletes all waiting events (asks for `clearqueue yes`). |
| `reboot` | Restarts. |

About `sim`: it plays "shut, open for ms, shut" through the real debounce and counting code while ignoring the real pin, then goes back to reading the pin as if the board had just started. If the pin then says "open" (for example because no reed switch is connected, which leaves GPIO4 HIGH), that is not counted. Openings shorter than 50 ms are ignored, exactly as for the real switch.

## LED codes

| LED | Meaning |
| --- | --- |
| White, steady | Starting up. |
| Amber, steady | Door open. Also shown when no reed switch is connected (the pin then reads "open"). |
| Green, short flash every 5 s | All well: connected and the last POST worked. |
| Cyan, steady | Sending to the server right now. |
| Blue, blinking | No network (WiFi not connected). |
| Red, blinking | Network up but the last POST failed (server down, 404, timeout). Events are kept and retried. |
| Magenta, blinking | The server refused the device key (401/403). Check `DEVICE_ID` and `DEVICE_KEY`. |

Amber wins over the other codes while the door is open.

## Door switch polarity

With the switch between GPIO4 and GND and the internal pull-up, the bench test of January 2026 showed: magnet near (door shut) = switch closed = pin LOW. That is the default (`DOOR_OPEN_WHEN_HIGH 1` in `include\config.h`). If your switch is the opposite kind (closed when the magnet is away), set it to 0. To check: type `status` with the door shut and again with it open; the line `door: GPIO4 raw level = ...` must say LOW when shut.

## Enabling a sensor

All four sensor types are switched on in `include\config.h` by default and stay dormant until they are plugged in, so normally there is nothing to change:

1. Wire the sensor as in `docs\wiring\wiring.md` (power off).
2. Power on, or type `probe`. The serial monitor prints `[sensor] ...: FOUND (...)`.
3. Type `sensors` to see a reading.

To stop the firmware even looking for a sensor, set its flag in `include\config.h` to 0 (for example `#define SENSOR_DHT_ENABLED 0`) and upload again. `SENSOR_DHT_TYPE` forces DHT11 (11) or DHT22 (22) if auto-detection guesses wrong. `SENSOR_SAMPLE_INTERVAL_MS` sets how often sensors are read (default 5 minutes).

HX711 scales are experimental: after wiring, type `tare 1` with shelf 1 empty, then put a known weight on it and type `cal 1 1000` (for 1000 g). The values are saved in flash. A channel that has not been calibrated sends nothing.

Readings sent: `bmp280`/`bme280` `temp_c`, `pressure_hpa` (and `humidity_pct` for BME280); `ds18b20` `fridge_temp_c`; `dht11`/`dht22` `temp_c`, `humidity_pct`; `hx711_1` to `hx711_4` `weight_g`.

## Switching to Walter (LTE-M)

1. In `include\secrets.h`, set `CELL_APN` to the SIM's APN (or leave it empty to let the network choose).
2. Plug the Walter in by its USB-C port and find its COM port with `pio device list`.
3. Build and upload the `walter` environment instead of `esp32s3`, in a PowerShell window where the first line has been run (it matters, see below):

   ```powershell
   $env:PLATFORMIO_CORE_DIR = "C:\Users\micha\.platformio-walter"
   C:\Users\micha\.platformio\penv\Scripts\pio.exe run -e walter -t upload --upload-port COMx
   C:\Users\micha\.platformio\penv\Scripts\pio.exe device monitor -p COMx -b 115200
   ```

That is the only change: everything else (door, queue, sensors, payload) is the same code. The `walter` environment uses a different ESP32 software platform (the community "pioarduino" platform with Arduino core 3.x), because the WalterModem library needs it.

Why the `PLATFORMIO_CORE_DIR` line: pioarduino and PlatformIO's own ESP32 platform install packages with the same names. Installed into the normal folder (`C:\Users\micha\.platformio`), pioarduino replaced the uploader and framework the `esp32s3` build needs, and the `esp32s3` build broke. With that line, Walter's packages live in `C:\Users\micha\.platformio-walter` and the two never meet. Close that PowerShell window (or run `Remove-Item Env:PLATFORMIO_CORE_DIR`) before building `esp32s3` again.

Known limits of the Walter uplink, because the modem does HTTP itself:

- It can send only one extra header, so the device key is sent but the `User-Agent: hollygrove-fridge/<fw>` header is not.
- The modem holds one root certificate (ISRG Root X1, Let's Encrypt). If the server's certificate ever comes from a different authority, Walter will fail TLS until `walter_ca.h` is updated.
- The code compiles (`pio run -e walter` succeeded on 2026-11-14) but has never run on a real Walter (none was available).
- The first `walter` build downloads about 1 GB of tools and takes 10 minutes or more.

## What has been tested (2026-11-14)

On the bench board (DevKitC-1 style N16R8, no reed switch or sensors attached):

- Unit tests: 39 of 39 passed on the board.
- `esp32s3` build: start-up, reset reason, WiFi, NTP, all four sensors reported dormant without errors.
- Live server, `bench-01`: HTTPS with certificate checking through Cloudflare; boot heartbeat accepted (HTTP 200) and clock set; two simulated openings (1800 ms and 700 ms) accepted; `resend` answered with `duplicates 1`.
- With the local test receiver (`esp32s3_dev`): events kept while the receiver was down and through a reset (2 events restored from flash, sent afterwards with their original boot id and age); 401 kept the events and backed off 15 minutes; 400 discarded the batch; 404 kept the event and retried at about 4, 11 and 16 s; a 30 ms simulated opening was ignored by the debounce; a 605-second simulated opening produced one `dur_ms -1` event at 600 s and nothing more at closing.
- `walter` build compiles; not run (no Walter board).

Not tested: a real reed switch (only `sim`; the switch itself was bench-tested in January 2026), any real sensor, the LED colours (nobody was there to look), a WiFi outage, a power cut during a flash write, a certificate the device should reject.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Upload fails, "port busy" or "access denied" | Close any open serial monitor (Ctrl+C) and try again. |
| Upload fails part-way or "MD5 mismatch" | Keep `upload_speed = 230400` in `platformio.ini`; faster speeds corrupt data on this board's USB chip. Try another cable. |
| No COM port appears | Use the port marked UART/COM, and a data cable (some cables only charge). The CH343 driver is in `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\Freenove\Freenove_ESP32_S3_WROOM_Board-main\Freenove_ESP32_S3_WROOM_Board-main\CH343`. |
| Nothing printed in the monitor | Speed must be 115200. Press RST. |
| `[wifi] trying network 1 of 1` repeats | Wrong WiFi name or password in `secrets.h`, or a 5 GHz-only network (the ESP32 needs 2.4 GHz). |
| LED blinks red, `[post] failed: HTTP 404` | The server is not answering at that path. Events are kept; nothing to do on the device. |
| `[post] failed: no HTTP response (error -1)` | No internet, DNS or TLS problem. Events are kept. |
| LED blinks magenta, `HTTP 401` | `DEVICE_KEY` does not match the server for this `DEVICE_ID`. |
| Door count goes up with nobody near the fridge | Long or loose reed wires: see the cautions in `docs\wiring\wiring.md`. |
| Door always shows OPEN | No reed switch connected, the magnet is too far (more than about 15 mm), or the polarity setting is wrong (see "Door switch polarity"). |
| A sensor says "not connected" | Check its wiring and 3V3 power, then type `probe`. DS18B20 needs its 4.7 k pull-up. |
| `reset reason: brownout` | The power supply sags; use a better 5 V supply or cable. |
| `reset reason: task_wdt` | The firmware hung for 2 minutes and restarted itself. Report it with the serial output. |
