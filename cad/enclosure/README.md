# Door-counter enclosure

Folder: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\enclosure\`

## What this is

Two things live here.

- A 3D-printable bench case for the ESP32-S3 dev board on a screw-terminal breakout board (demos
  and sheltered indoor use, NOT weatherproof). Revision 1.
- A carrier plate ("sled") for the field unit: the DPTechnics / QuickSpot **Walter** board inside
  a bought Hammond 1554H2GY waterproof box. Revision 1 of the Walter sled.

Nothing has been printed, soldered or test-fitted yet. Every file name carries its revision
(`-rev1`); a revision's files are never overwritten or deleted.

## WHAT TO PRINT FIRST (bench case)

The bench board is the generic ESP32-S3 DevKitC on the Freenove Universal breakout (FNK0101).
Print these from `print\bench-case-devkitc\` (STL or 3MF, same shape):

| Part | File | How many |
|---|---|---|
| Case base | `case-base-fnk0101-rev1.stl` (or `.3mf`) | 1 |
| Case lid | `case-lid-fnk0101-rev1.stl` (or `.3mf`) | 1 |
| Toe clamp | `toe-clamp-rev1.stl` (or `.3mf`) | 4 |

Settings: Bambu Lab P1S, 0.4 mm nozzle, PLA is fine on the bench, 0.2 mm layers, 4 to 6 walls,
15 to 20 percent infill, no supports. Base floor down. Lid with its text face DOWN on the bed.
Clamps flat. Details: `docs\design-notes.md`.

### Hardware for the bench case

- 8 x M3 brass heat-set inserts, 5.7 mm long (4 for the lid, 4 for the toe clamps), and a
  soldering iron to press them in
- 4 x M3 x 10 screws (lid)
- 4 x M3 x 8 screws (toe clamps)
- A few 2.5 mm zip ties

### Measure with calipers before printing the bench case

- The FNK0101 breakout: outline (designed as 87 x 83 mm) and the four mounting-hole centres
  (ASSUMED 3.0 mm in from each edge).
- The DevKitC board: outline (designed as 57.15 x 27.94 mm), the centres of the two USB-C
  sockets (assumed 12.5 mm apart), and the pin row spacing (designed as 25.4 mm).
- The USB-C plug you will use: the opening is 30 mm wide and the plug body is designed as
  12.4 x 6.6 mm.
- The cables that will leave the case (designed for DOOR 4.0, I2C 5.0, 1W 4.2, PWR 5.3 and
  LOAD 4.0 mm).

Differences of 1 to 2 mm are tolerated by the clamps. Anything bigger: tell Claude before
printing.

### Assembly of the bench case

1. Press the inserts into the four lid bosses and the four clamp bosses with the soldering iron.
2. Plug the dev board into the breakout and lay the breakout in the base inside the four fences.
3. Turn each toe clamp over a clear stretch of board edge and screw it down until its finger
   rests on the board.
4. Lay the cables into the labelled slots, tie them to the anchors, lower the lid, fit four
   screws.

## FIELD UNIT: Walter sled in the weatherproof box

### What to print for the field unit

From `print\weatherproof-box-sled\`:

| Part | File | How many |
|---|---|---|
| Walter sled | `sled-1554h-walter-rev1.stl` (or `.3mf`) | 1 |
| Toe clamp | `toe-clamp-rev1.stl` from `print\bench-case-devkitc\` | 4 |

Material: PETG at the very least, ASA preferred (a closed box in New Orleans passes PLA's 55 to
60 C softening point). Lay the sled flat, 0.2 mm layers, 4 to 6 walls, 15 to 20 percent infill,
no supports. Largest dimension 166 x 106 mm, 40 mm tall; fits the P1S bed.

### The stack, bottom to top

1. Hammond 1554H2GY box (four M3 inserts on a 132 x 84 mm pattern).
2. The printed sled, held by four M3 x 8 screws into those inserts.
3. Adafruit Perma-Proto Full-sized Breadboard PCB (157 x 51 mm), held by four toe clamps.
4. Two 14-pin female header strips (8.5 mm) and a row of 3.5 mm screw-terminal blocks soldered
   to it.
5. The Walter, plugged into the two header strips (its USB-C end towards the middle of the box,
   its antenna end hanging over the left end of the proto board).
6. The Taoglas FXUB63.07.0150C flat LTE antenna, stuck on the upright pad at the back of the
   sled, with its lead plugged into the Walter's LTE u.FL connector.

### Parts to buy for it (prices in `docs\shopping-list.md`)

- Walter P000000100, antenna FXUB63.07.0150C, IoT SIM (already on the list).
- Adafruit Perma-Proto Full-sized (product 1606). The half-sized board was out of stock on
  2026-11-14 and would also be too short for this layout.
- 1 pack of Adafruit 36-pin female headers (product 598): cut two 14-pin strips from it.
- 2 packs of Adafruit 3.5 mm 2-pin terminal blocks (724) and 1 pack of 3-pin (725).
- 1 Schottky diode rated 2 A or more (for example 1N5822) and 2 x 10 uF ceramic capacitors.
- 4 M3 heat-set inserts and 4 M3 x 8 screws for the clamps, 4 M3 x 8 screws for the box (both
  already in the fasteners group). Nylon M3 screws for the four box screws would move the
  antenna further from metal (optional).
- A few 2.5 mm zip ties.

### What to solder

Walter pin numbers are the datasheet's (Table 1, pins 1 to 14 on one header, 15 to 28 on the
other, pin 28 at the USB-C end). The pins 15 to 28 row is the one nearest the terminal row.
GPIO numbers match `docs\wiring\wiring.md`.

| Signal | GPIO | Walter pin | Terminal label |
|---|---|---|---|
| 5 V in (to VIN through the diode, see below) | - | 28 (VIN) | PWR 5V, PWR GND (GND is pin 27) |
| Reed switch | 4 | 15 | DOOR, DOOR (second wire to GND, pin 27) |
| DS18B20 data (4.7 k to 3V3) | 5 | 16 | 1W: 3V3, DATA, GND |
| DHT data | 6 | 17 | DHT: 3V3, DATA, GND |
| I2C SDA, SCL | 8, 9 | 23, 24 | I2C: 3V3, GND, SDA, SCL |
| RS485 DE+RE, DI, RO (reserved) | 16, 17, 18 | 20, 21, 22 | 485: 3V3, GND, DE, DI, RO |
| HX711 SCK, DT1 to DT4 (experimental) | 42, 41, 40, 39, 38 | 12, 11, 10, 9, 8 | HX: 3V3, GND, SCK, DT1 to DT4 |
| Sensor 3.3 V (switched output) | - | 26 (3V3 OUT) | the 3V3 terminals |

Do not wire GPIO 14, 21, 45, 47, 48 (the modem uses them) or 0, 3, 46.

Place the headers in the proto board's holes so the two rows are 0.7 in (17.78 mm) apart and
each row runs along the board's long direction, so every pin has its own five-hole strip (the
centre channel of the Perma-Proto sits between the rows; the sled's support rib sits under it).
Leave the first 3 mm of both long edges clear where the toe clamps rest. The board sits 5 mm
above the sled, so trim leads flush on the underside (3 mm of joint and lead is allowed), and
solder nothing in the 4.5 mm centre-channel strip under the Walter, where the support rib touches.

Power, from the Walter datasheet (section 5.1):

- VIN has no protection and must never exceed 5.5 V. Feed it only from the 5 V adapter.
- Put the Schottky diode in series (anode to the 5 V terminal, cathode to VIN). It stops the
  5 V from flowing back out of a USB cable when you plug into the Walter's USB-C port. Without
  it, never plug a normal USB cable into the Walter while the box supply is on.
- Solder 2 x 10 uF ceramic capacitors from VIN to GND as close to pin 28 as you can.
- 3V3 OUT is switched off at start-up and powers sensors only after the firmware pulls GPIO0
  low (maximum 250 mA, maximum 1 uF load). The reed switch needs no 3.3 V.

### Assembly of the field unit

1. Press the 4 inserts into the toe-clamp bosses with the soldering iron.
2. Solder the proto board as above. Check with a meter: 5 V on VIN, no short between VIN and GND.
3. Lay the proto board in the sled between the corner fences and fit the four clamps.
4. Plug in the Walter (and fit the SIM first, see below), connect the antenna lead and tie it
   to the anchor on the sled with a zip tie.
5. Peel the antenna's backing and press it into the pocket on the upright pad.
6. Cables enter through the glands in the bottom face, run over the row of six zip-tie anchors
   (tie each cable down), and land on the terminals.
7. Screw the sled to the box's four inserts with M3 x 8 screws.

### Access without taking things apart

- USB-C: open the box lid. The Walter's USB-C faces the middle of the box and nothing taller
  than 19 mm lies in front of it, so a normal plug fits (mind the diode note above).
- SIM: the nano-SIM holder is on the underside and its card slot faces the antenna end. Only
  about 3.5 mm remain between that end and the box wall, so insert or change the SIM by lifting
  the Walter out of its sockets (pull straight up, no tools), or fit the SIM before mounting.
  The datasheet itself advises fitting the SIM before mounting.

### Unverified until the real Walter and the proto board are in hand

- Walter dimensions are from the vendor datasheet rev 1.3 (outline, headers, USB-C, u.FL, SIM
  holder centre, heights): high confidence, but not measured. Measure the Walter with calipers
  when it arrives, especially: 55.0 x 24.8 mm, header row spacing 17.78 mm, and that it sits
  11.8 mm above the proto board in 8.5 mm sockets.
- Assumed: the SIM holder footprint (12 x 14 mm), the female header body height (8.5 mm; the
  Adafruit page does not state it), the terminal block height (9.5 mm), and where the
  Perma-Proto's own mounting holes are (the sled does not use them).
- The antenna sits 11 mm from the nearest metal (the box screws), the vendor's minimum is 10 mm
  and its ideal 20 mm; it is 22 mm or more from the board. Check signal strength in the
  box and move the antenna or use nylon screws if it is poor.
- The firmware does not yet drive GPIO0 for the switched 3.3 V rail, and the `walter` build has
  never run on a real Walter.

## Sub-folders

- `print\bench-case-devkitc\`: files to print now for the bench (DevKitC on FNK0101), including
  the toe clamp.
- `print\bench-case-freenove\`: the same for the Freenove ESP32-S3 on the FNK0091 breakout.
- `print\weatherproof-box-sled\`: the Walter sled for the field unit, plus the two dev-board
  sleds (kept, not archived).
- `pictures\`: preview images, in folders matching the print folders.
- `source\`: `generate_enclosure.py`, the script that makes every file.
- `checks\`: `validation-rev1.json` (case and dev-board sleds) and `validation-walter-rev1.json`
  (Walter sled), the automatic geometry checks.
- `docs\`: `design-notes.md`, the long technical notes.
