# Door-counter enclosure (rev1): design notes

Technical material moved out of the folder README so the README stays short. Start with the
README if you only want to print and build the bench case.

Root: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\enclosure\`

Generator: `source\generate_enclosure.py`. Checks: `checks\validation-rev1.json`. Power,
weatherproofing and mounting advice:
`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\power-and-enclosure.md`.
Choices made without the owner:
`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\enclosure.md`.

## What is here

A printable case for bench, demo and sheltered indoor use, plus a "sled" that carries the same
electronics inside a bought IP66 junction box (Hammond 1554H2GY) for outdoor use. The printed
case is NOT weatherproof.

| Part | Files | Print qty |
|---|---|---|
| Case base | `case-base-<variant>-rev1.stl` / `.3mf` | 1 |
| Case lid | `case-lid-<variant>-rev1.stl` / `.3mf` | 1 |
| Toe clamp | `toe-clamp-rev1.stl` / `.3mf` (identical copy in each bench-case folder) | 4 per case, 4 per sled |
| Sled for Hammond 1554H / 1554T | `sled-1554h-<variant>-rev1.stl` / `.3mf` | 1 |
| Sled for the Walter (field unit) | `sled-1554h-walter-rev1.stl` / `.3mf` | 1, with 4 toe clamps |

Variants:

| Variant tag | Folder name | Stack | Case outer (X x Y, height closed) | Over ears and pocket |
|---|---|---|---|---|
| `fnk0091` | `bench-case-freenove` | Freenove ESP32-S3 WROOM / Lite on Freenove FNK0091 breakout | 119.5 x 123.5, 36.0 mm | 149.5 mm wide |
| `fnk0101` | `bench-case-devkitc` | ESP32-S3-DevKitC-1 style clone (AYWHP) on Freenove FNK0101 universal breakout | 119.3 x 131.3, 36.0 mm | 149.3 mm wide |

The owner's bench board is the generic DevKitC (`fnk0101`), so that variant is printed first.
The field unit uses a Walter board; its sled is a separate part with its own revision count
(`sled-1554h-walter-rev1`, see "Walter sled" below). The two dev-board sleds are kept as they
are. The AYWHP board has 22 pins per side and does not fit the FNK0091 (Freenove states it is
for Freenove boards only).

Features: board held by corner fences with 0.75 mm clearance and four rotating screw-down toe
clamps (adjustable, no pegs through unmeasured holes); one wide USB-C opening (30 mm) reaching
both sockets, closed at the top by a lid tongue; a lid window over BOOT, RESET and the LEDs;
labelled comb-slot cable exits with strain relief (DOOR, I2C, 1W on one side; LOAD, LOAD, PWR on
the other); zip-tie anchors; one accessory pad with 2.0 mm pilot holes on a 5.08 mm grid for a
small sensor breakout; a vented outside pocket for a BMP280 (lid tab covers it); two keyhole
mounting ears. No supports needed.

## Print settings (Bambu Lab P1S, 0.4 mm nozzle)

- Material: PLA is fine for bench and demo. For anything outdoors or in a hot room use ASA, or
  PETG as a minimum (PLA softens at 55 to 60 C). Not on hand: buy a spool.
- Layer 0.2 mm, 4 to 6 walls (2.4 mm walls are 6 perimeters), 15 to 20 percent infill, no supports.
- Orientation: base floor down. Lid with the text face DOWN on the bed (its lip points up);
  the lid's 0.6 mm text is cut into the underside of the print and bridges at most 1.53 mm.
- Sled: flat. Clamps: flat. All parts fit the 256 mm bed.

## Hardware

- Case lid: 4 x M3 x 10 screws, into 4 x M3 x 5.7 mm brass heat-set inserts (default,
  `FASTENER = "insert"`). Without inserts set `FASTENER = "selftap"` (2.5 mm holes) and bump REV.
- Toe clamps: 4 x M3 x 8 screws and 4 inserts (or self-tap) per mounting.
- Sled: 4 x M3 x 8 screws into the box's own M3 inserts (132 x 84 mm pattern).
- Zip ties 2.5 mm wide, a few. Optional: wall screws for the ears (M4 or #8).
- Heat-set inserts need a soldering iron with a tip that fits.

## Assembly (all variants)

1. Press the inserts into the lid bosses and clamp bosses with the iron.
2. Plug the dev board into the breakout, lay the breakout in the base inside the four fences.
3. Rotate each clamp to a clear stretch of board edge and screw it down until its finger rests
   on the board.
4. Lay cables into the labelled slots, tie to the anchors, lower the lid, fit four screws.
5. Sled in a Hammond box: same steps on the sled, then screw it to the box's four inserts. Cable
   glands go in the bottom face (see the power document).

## Regenerating

Python 3.13 with `manifold3d`, `trimesh`, `numpy`, `scipy`, `Pillow`, `matplotlib` (all already
installed; nothing was installed for this work).

```text
cd cad\enclosure\source
set PYTHONDONTWRITEBYTECODE=1
python generate_enclosure.py                      # everything, about 8 minutes with renders
python generate_enclosure.py --variant a --no-render --outdir %TEMP%\enc   # about 1 minute
python generate_enclosure.py --part walter --outdir %TEMP%\enc-walter      # Walter sled only
```

`--part` picks what is built: `legacy` (case, lid, clamp and the two dev-board sleds, governed by
`REV`), `walter` (the Walter sled, governed by its own `REV_WALTER`) or `all` (default).

`--outdir` is the output ROOT. The script creates `print\bench-case-<folder>\`,
`print\weatherproof-box-sled\`, `pictures\...` and `checks\` under it. The default root is the
folder that holds `source\`, which is the delivered layout, so a plain run into the default
refuses to overwrite the delivered rev1 files. Test runs belong in a scratch folder.

The script refuses to overwrite a delivered file. When geometry changes, bump `REV` (case and
dev-board sleds) or `REV_WALTER` (Walter sled) at the top of the script (outputs become
`-rev2`); never delete rev1. The Walter sled was added without changing any code path, geometry
or revision of the existing parts; its files were the only ones written.

Another dev board in a printed case: the `BOARDS` table has an unused `walter` entry and
`VARIANTS` has a commented example `c` variant (a bare-Walter case on the FNK0101 carrier, not
used: the field unit uses the Walter sled below). Other cables: edit `EXITS_LEFT` and
`EXITS_RIGHT`. Other junction box: edit the `BOX` block.

## Validation numbers (rev1, both variants: `problems: []`)

- All 8 solids watertight in memory and after STL reload (0 bad edges), 1 body each.
- Lid-to-base overlap 0 mm3; lip-to-wall gap 0.25 mm; tongue-to-opening gap 0.25 mm.
- Board and carrier keep-out volumes against base, lid and clamps: 0 mm3 everywhere; board
  top to lid 8.0 mm; PCB to fence 0.75 mm.
- USB opening 30 mm wide, z 17.7 to 28.5, socket centre z 23.2. Plug-body margins: variant
  `fnk0091` 3.7 side, 2.2 below, 2.0 above; `fnk0101` 2.55 side, 2.2 below, 2.0 above.
- Overhangs over 50 degrees: base, five slit tops bridging 0.8 mm at z 27; lid, text ceilings
  up to 1.53 mm; sled and clamp none.
- Minimum wall: base 0.9 mm (floor over blind pilot holes), lid about 0.6 mm (islands inside
  letters), sled 1.39 mm, clamp 2.8 mm. Walls 2.4 mm.
- Sled 166.13 x 105.68 x 9.59 mm in a 172.91 x 108.91 mm box interior; headroom under the box
  lid 22.9 mm.
- Bed fit: largest part 149.5 x 123.5 mm.

## Unverified, and what needs calipers

Nothing has been printed or test-fitted.

- FNK0091 outline and hole pattern were scaled from a vendor drawing (+/-0.5 mm). FNK0101 hole
  positions are ASSUMED (3.0 mm inset); its 87 x 83 outline is from a product image. Measure
  both boards before relying on the pilot holes. The clamps tolerate 1 to 2 mm.
- Freenove S3 board: 28.1 x 50.9 mm, USB centres +/-5.1, scaled from a pinout image.
- DevKitC clone: 57.15 x 27.94 mm and 25.4 mm row spacing are from an online report; USB
  centres (+/-6.25 mm) and its position on the FNK0101 are ASSUMED. Measure the actual board
  (which one is on the bench is itself unconfirmed: the connected one reports 16 MB flash,
  consistent with the AYWHP clone).
- Freenove USB-C sockets are 10.2 mm apart: two plugs side by side will not fit. Try the real
  cable in the opening.
- Cable diameters in the exit slots (DOOR 4.0, I2C 5.0, 1W 4.2, PWR 5.3, LOAD 4.0 mm) are
  assumed.
- Hammond 1554H2GY dimensions are from the maker's drawings; check the four inserts on the
  132 x 84 mm pattern when the box arrives.
- Lid window and LEDs: button positions on the clone are not documented; the window is large
  for that reason.
- The BMP280 pocket is demo-grade (it reads warm).

Caliper checklist: carrier outline and hole centres, dev board outline, USB socket centres
and plug size, cable diameters, box inside size and insert spacing.

## Previews

In `pictures\bench-case-devkitc\` and `pictures\bench-case-freenove\`:
`preview-case-closed-`, `-open-`, `-exploded-`, `-usb-end-` and `preview-lid-underside-`,
each ending `fnk0101-rev1.png` or `fnk0091-rev1.png`. In `pictures\weatherproof-box-sled\`:
`preview-sled-in-box-` and `preview-sled-bare-`, for both variants. The green, yellow and grey
blocks are placeholders for the boards, terminals and plug.
`preview-sled-in-box-walter-rev1.png` and `preview-sled-bare-walter-rev1.png` show the Walter
sled (the magenta slab is the antenna, the white bar the USB-C plug).

## Walter sled (`sled-1554h-walter-rev1`)

The field unit's carrier for the Hammond 1554H2GY box. It reuses the existing sled's plate
outline, the four M3 holes on the 132 x 84 mm pattern, the corner-pad and fence idea, the toe
clamp and the zip-tie anchor; the dev-board sleds themselves are untouched. Its own revision
constant is `REV_WALTER` in `source\generate_enclosure.py`.

### Why a proto board carries the Walter

The Walter has no screw terminals. Its datasheet (section 6.2) says it plugs into two 14-pin
2.54 mm sockets 17.78 mm apart (recommended Wuerth 61301411821, 8.5 mm tall), or is soldered
in. Nothing off the shelf carries both the sockets and the field terminals, so the choice is a
prototyping board: **Adafruit Perma-Proto Full-sized Breadboard PCB (product 1606)**, 157 x 51 mm
x 1.6 mm, which has breadboard-style five-hole strips. The Walter's rows (0.7 in apart) fit the
board's strips exactly when its long axis runs along the board's long axis. The half-sized
Perma-Proto (1609, 81 x 51 mm) was out of stock on 2026-11-14, as were the quarter, mint-tin
and 3-pack versions; only the full-sized board was in stock (35 units), so the layout is built
around 157 x 51 mm.

### Walter dimensions and where each comes from

Source: `https://www.quickspot.io/datasheet/walter_datasheet.pdf`, revision 1.3 (2026-11-11),
section 6 and tables 4 and 5, read from the PDF text. Confidence "datasheet" means a drawn or
tabulated vendor value with the vendor's general tolerance of 0.2 mm; nothing was measured.

| Item | Value | Source | Confidence |
|---|---|---|---|
| PCB outline | 55.00 x 24.80 mm | datasheet fig. 5 | datasheet |
| PCB thickness | 1.6 mm (10 percent) | datasheet 6 | datasheet |
| Pin headers | two rows of 14, 2.54 mm pitch, 17.78 mm apart, pin 1 and pin 28 at 9.72 mm from the USB-C end; pins 0.64 mm square, 6.0 mm long | fig. 5, 6.2 | datasheet |
| Mounting holes | none | fig. 5 | datasheet (none drawn) |
| USB-C | centre line 4.31 mm from the board centre line (towards pins 1 to 14), at the board edge, 3.4 mm tall | table 4, 6.2 | datasheet |
| LTE u.FL | X +3.00, Y 4.30 (from the USB-C end), top side | table 4 | datasheet |
| GNSS u.FL | X +7.30, Y 4.30 | table 4 | datasheet |
| Nano-SIM holder | bottom side, centre X +0.50, Y 40.20, push-pull, card enters from the antenna end, 1.35 mm tall | table 4, 6.2 | datasheet; footprint 12 x 14 mm ASSUMED |
| PCB antenna area | X +/-9.00, Y 49.00 to 55.00; keep copper off 24.8 x 6 mm there, metal 15 mm away | table 4, 6.5 | datasheet |
| Component heights | 8.3 mm above the carrier soldered (3.3 + 1.6 + 3.4), 16.8 mm in an 8.5 mm socket; bottom of the PCB 11.8 mm above the socket's carrier | table 5 | datasheet |
| Female header body | 8.5 mm | datasheet names an 8.5 mm socket; the Adafruit page (598) does not state a height | ASSUMED |

The project notes (55 x 24.8 mm outline, nano-SIM, LTE modem on GPIO 14, 21, 45, 47, 48) agree
with the datasheet.

### Layout (sled coordinates, mm)

Origin at the sled plate centre; +X along the box's long side; the cable glands are at -Y.

- Plate: the same outline as the dev-board sleds, 166.13 x 105.68 x 3.0, with the four 3.4 mm
  holes at (+/-66, +/-42).
- Proto board: x -75 to +82, y -23 to +28, underside 8.0 mm above the sled bottom (5 mm over the
  plate), top face 9.6 mm. Four corner pads and fences (no fence at the +X end where the board
  is flush with the plate), four toe-clamp bosses at x -55 and +45 on both long edges, and a
  4.5 mm support rib in the board's centre channel under the Walter's header rows.
- Walter: long axis along X, USB-C end at x -28 (towards the middle of the box), antenna end at
  x -83 (8 mm beyond the board's end, as the datasheet prefers), centred on the board's centre
  channel (y +2.5), PCB underside 21.4 mm above the sled bottom, top of the USB-C 26.4 mm.
- Terminal row: x -66 to +76 along the -Y edge (room for 40 blocks at 3.5 mm), placeholder
  9.5 mm tall.
- Cable strain relief: six zip-tie anchors in a row at y -43, x -50 to +50 every 20 mm. A
  seventh anchor at (-40, +41.5) holds the antenna's coax lead.
- Antenna pad: an upright wall (4 mm thick, 100 mm long, top at z 40) on the +Y edge, x -32 to
  +68, with a 0.5 mm pocket for the antenna (96 x 21 mm, z 16 to 37) and a 45 degree shelf under
  it. The antenna's adhesive does the holding; the shelf stops it sliding. The wall is the
  part furthest from the board, 22 mm from the proto board's edge and 34 mm from the Walter.
- Power wiring: the PWR terminal pair goes at the Walter end of the terminal row, next to the
  diode and capacitors the datasheet requires at VIN (pin 28).

### Validation numbers (rev1, `checks\validation-walter-rev1.json`, `problems: []`)

- Watertight in memory and after STL reload (0 bad edges), 1 body, 69.72 cm3, 3888 triangles.
- Size 166.13 x 105.68 x 40.0 mm; fits the 256 mm bed.
- Overhangs over 50 degrees: none, so no supports (the pocket roof and the shelf underside are
  45 degrees). Minimum wall 1.5 mm; 1st percentile 2.33 mm; median 3.0 mm.
- Keep-out volumes (proto board, terminal row, solder tails under the board, headers, Walter
  PCB and top parts, SIM holder, USB plug, antenna) against the sled and the four clamps: 0 mm3
  everywhere; clamps against the sled 0 mm3.
- In the Hammond box (inside 172.91 x 108.91 x 54.5, sled on 6 mm bosses): whole assembly
  166.13 x 105.68 mm, clearance to the box walls 3.39 mm in X and 1.61 mm in Y per side; the
  Walter's top is 32.4 mm above the box floor (22.1 mm under the lid); the highest point, the
  antenna wall, is 46.0 mm above the floor, 8.5 mm under the lid.
- Antenna distance to metal: 22.1 mm to the proto board, 34.2 mm to the Walter, 37 mm to the
  headers, 11.2 mm to the box screws and inserts (vendor minimum 10 mm, ideal 20 mm).
- USB-C plug (drawn 45 mm long, z 21.4 to 28.0) intersects nothing; the tallest thing below it
  is the terminal row at 19.1 mm.
- SIM: 10.45 mm free under the holder; the Walter's antenna end is 3.45 mm from the box wall.

### What is not known until the Walter and the board are on the bench

See the README's list. In short: Walter and Perma-Proto dimensions are vendor values, not
measurements; the SIM holder footprint, header height and terminal height are assumed; the
firmware does not yet pull GPIO0 low to switch on 3V3 OUT; and SIM change in place is marginal
(3.45 mm to the box wall), so plan on lifting the Walter out.
