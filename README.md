# Hollygrove Community Fridge door counter

A small device that counts how many times the Hollygrove Community Fridge door is opened and
shows the totals on a public page. It uses a magnetic switch on the door. There is no camera
and it records nothing about people.

- Dashboard: <https://hollygrovenola.org/fridge/> has two cards: sample data, and live data
  from the WiFi test unit at the house.
- Status (2026-11-21): the counter program runs on a test board at the house over WiFi, with
  a real reed switch wired to it. The fridge unit will use a Walter LTE board, which has not
  been bought yet. Nothing has been 3D-printed.
- Open decision: whether the fridge unit goes indoors in the dry-goods room (about $110 to
  $120 to build) or outdoors at the fridge (about $180). See `DECISIONS-FOR-MICHAEL.md`.

## Where things are

| Folder or file | What is in it |
|---|---|
| `project-log.md` | The history of the project and the to-do list. Start here to see where things stand. |
| `DECISIONS-FOR-MICHAEL.md` | Choices made during the overnight build, and which questions are still open. |
| `docs\shopping-list.md` | Every part, where to buy it and what it costs. |
| `docs\wiring\` | The wiring diagram and pin table. |
| `docs\firmware.md` | How to build the program and load it onto a board. |
| `docs\power-and-enclosure.md` | How the fridge unit is powered and kept dry. |
| `docs\decisions\` | The detailed decision lists for each part of the build. |
| `docs\archive\` | Older plans that no longer apply (the Meshtastic plan and the first tutorial). |
| `cad\demo-door\` | The printable demo door. Its README says what to print. |
| `cad\enclosure\` | The printable case and the carrier for the weatherproof box. Its README says what to print. |
| `src\`, `include\`, `lib\`, `test\`, `platformio.ini` | The counter program (PlatformIO project). |
| `tools\` | Helper scripts: a pretend device for testing the server, and the wiring-diagram generator. |
| `server\` | The service that receives the counts, and the dashboard page. It runs on the hollygrove VM. |
| `research\` | Background reading and the manuals for the fridge's battery and inverter. |
| `legacy\` | The first version of the program (Pico 2W and ESP32) and its wiring notes. |

`include\secrets.h` holds the WiFi password and the device key. It stays on this computer and
is never uploaded.
