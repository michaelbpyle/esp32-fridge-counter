# Decisions made overnight, 2026-11-14

Michael asked for six deliverables to be designed and built without consulting him, with a
log of the decisions made for lack of information. This is that log. The first section holds
the questions that need his answer. The second lists the larger calls already made. Each
agent's full list, with reasons and alternatives, is in `docs\decisions\`:

- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\firmware.md` (23 decisions)
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\server.md` (14 decisions)
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\demo-door.md`
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\enclosure.md` (24 decisions)

## Answered on 2026-11-14 (morning)

- **1, 2, 3:** WiFi now, LTE later. WiFi is for testing at the house; the counter is not deployed
  until the Walter arrives. The generic DevKitC is the bench board; the Walter is the deployment
  board. Meshtastic is superseded in the project log's goals.
- **4:** No navbar link yet.
- **6:** Publishing lag shortened to 15 minutes on 2026-11-14, then to one minute on 2026-11-15 at the
  owner's instruction.
- **10:** No M3 inserts or screws on hand; they are on the to-buy list.
- **11:** Commit and push approved.
- **New instruction:** the charts belong at `/fridge/` itself. The page now shows the full
  dashboard with clearly marked sample data until real counts exist.

- **12:** Backups installed: a daily TrueNAS snapshot of the hollygrove VM disk (14 days) and a
  nightly clean copy of the fridge database on the VM.
- **5:** Dashboard wording is fine for now; revisit before it gets a navbar link.
- The work is merged into `main` and pushed.

Still open: 7, 8 and 9 (all about the field install, which waits for the Walter).

## Added after the overnight build (through 2026-11-21)

- The door's reed switch is the surface-mount pair; demo door rev 2 is built for it.
- `/fridge/` is a hub with `/fridge/sample/` and `/fridge/live/` (the WiFi test unit).
- A purchase request for the HNA president exists as a shared doc: $629.63 of parts and tools, $730 with
  an estimated 15% for tax and shipping.
- WiFi transmit power was lowered to 8.5 dBm to fix a join failure with the eero access points.
- A Walter carrier for the weatherproof box is designed (from the datasheet, unverified).

**Open decision (asked 2026-11-18, not answered):** to cut cost, put the electronics indoors in the
dry-goods room in a printed PLA case, power the Walter by USB-C, and use a breadboard, which brings
the whole build to about $110 to $120; or keep it outdoors at the fridge with a hardware-store sealed
box and printed fittings, about $180. The purchase request and the case design still show the
$730 outdoor version until this is decided. Either way the case lid would change to snap on,
so no brass inserts are needed.

## Questions that need your answer

1. **Is there WiFi that reaches the fridge at 9000 Oleander, and whose is it?** No email or
   project file says. The firmware works on WiFi today; without WiFi at the site the choices
   are the Walter LTE board, a WiFi bridge, or the Meshtastic plan.
2. **WiFi or Meshtastic?** The project log's goals (June) say "no WiFi, no SIM" via Meshtastic.
   Last night's request was WiFi now and LTE later, and that is what was built. The log now
   records both; say which is the direction so the goals can be rewritten.
3. **Which board goes to the fridge?** The board on the bench has 22 pins per side, 16 MB
   flash and two USB-C ports, so it is one of the generic DevKitC boards, not a Freenove. The
   firmware is the same for both; the case and the screw-terminal breakout differ.
4. **Should the dashboard get a link in the HNA site's navigation bar?** It is live at
   `https://hollygrovenola.org/fridge/` but not linked from anywhere. Adding a link re-renders
   the whole site and restarts the web server for a moment.
5. **Is the dashboard wording right for the neighborhood?** In particular the "About these
   numbers" section and the empty-state text ("The counter is being set up").
6. **Is it acceptable that the public numbers lag by up to an hour?** Counts appear only after
   each hour ends, so nobody can watch a single opening happen. The lag can be shortened with
   one setting, at a cost to privacy.
7. **Is there a free 120 V outlet in the dry-goods room for the first install,** and how far is
   it from the fridge door? The first-install power plan is a USB adapter on the inverter's
   output.
8. **Who is qualified to connect to the 48 V battery bus** for the long-term converter?
9. **Is weather data wanted on the first install?** The BMP280 has to sit outside the sealed
   box in a vented pocket to read real weather.
10. **Do you have M3 heat-set inserts and M3 screws?** The printed case uses them; none were
    found in your orders.
11. **May the firmware and docs be committed and pushed to GitHub?** Nothing was committed.
    `include\secrets.h` is ignored and stays local.
12. **Should the hollygrove VM's new database be added to a backup job?** Nothing backs up
    `/opt/hollygrove/fridge/data/fridge.db` yet.

## Check before printing (calipers)

- The Gebildet reed switch: barrel diameter, flange diameter and thickness, overall length.
  The demo door's press fit rests on one line of the Amazon listing.
- Both screw-terminal breakout boards and the bench board's USB connector positions. The case
  README has the checklist.
- The diameter of the cables you will actually use through the case's comb slots.

## Larger calls already made

1. **Dashboard address:** `hollygrovenola.org/fridge/`, a path and not a subdomain, so no
   Cloudflare change was needed and `/data` and others can follow the same pattern.
2. **Server shape:** one new container (`hollygrove-fridge`) in the existing hollygrove compose
   stack with its own SQLite file. NextCloud's Postgres was left alone.
3. **New top-level folder on the hollygrove share:** `fridge/` was created without asking,
   which that project's rules normally require. The overnight instruction was taken as the
   approval. Its `CLAUDE.md`, `SETUP-GUIDE.md` and log were updated (Session 17).
4. **Privacy:** the public API gives hourly totals or coarser, never the time of one opening.
5. **Bench versus field identity:** the bench board reports as `bench-01`, which is stored but
   left out of all public numbers. The fridge unit will be `fridge-01`; its key is in
   `/opt/hollygrove/fridge/fridge.env` on the VM.
6. **Sensors:** only the BMP280 is on hand. DS18B20, DHT, HX711 and RS485 support is written
   and dormant; those parts are on the to-buy list in the wiring document.
7. **Power:** first install from a USB adapter on the inverter output; long term an isolated
   Mean Well DDR-15L-5 on the battery bus. The LM2596 modules (40 V maximum input) must not go
   on the 48 V battery.
8. **Weatherproofing:** a Hammond 1554H2GY box with glands is the weather barrier; printed
   parts go inside it. The printed case is for the bench, demos and sheltered use.
9. **Demo door hinge:** Nick Johnson's Clamshell Parts Box hinge (MakerWorld 786443, CC BY-SA),
   scaled up, credit carried in the README.
10. **Agents and models:** the work was split across agents. After your message about token
    use the four running agents handed off to leaner models (Opus for firmware and the door,
    Sonnet for the server and the case) without reducing scope.

## Changes to machines

- **This PC:** a second PlatformIO folder, `C:\Users\micha\.platformio-walter`, holds the Walter
  toolchain. The first Walter build damaged the shared PlatformIO install; the firmware agent
  repaired it, which installed a few Python helper packages (intelhex, cryptography and
  similar) into PlatformIO's own Python environment. Walter must always be built with
  `PLATFORMIO_CORE_DIR` pointing at the second folder (see `docs\firmware.md`). Python virtual
  environments and a headless-browser helper were created in the temp folder only.
- **The ESP32 board:** now runs the new firmware as `bench-01`. A copy of what it held before
  is at `\\TRUENAS\Pyle-TNAS_Backups\BackUp - Projects\Microcontrollers\esp32-fridge-counter\`.
- **hollygrove VM:** new container, new `fridge/` folder, one Caddy route, one new page, and
  the `hollygrove-render` service was restarted once. Backups of the edited files are in
  `\\TRUENAS\Pyle-TNAS_Backups\BackUp - Projects\hollygrove-vm\` (stamped 20261114).
- **Git:** nothing committed or pushed.
