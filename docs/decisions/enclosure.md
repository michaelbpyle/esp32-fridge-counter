# Decisions made without owner input — enclosure, power and weatherproofing

Date: 2026-11-14. The owner was asleep and could not be asked. Each item says what was
chosen, why, what the alternative was, and what the owner should confirm. Nothing was printed,
measured, bought or installed. No file outside these was touched:

- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\enclosure\`
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\power-and-enclosure.md`
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\enclosure.md`

## Power

### 1. First field install is powered from a USB wall adapter on the inverter's AC output

- **Chose:** a listed 5 V USB adapter indoors, with a 5 V cable out to the node.
- **Why:** nobody has to work on a 48 V lithium battery bus, and the inverter runs all day for
  the fridge anyway.
- **Alternative:** go straight to the 48 V converter, which was the project's stated plan.
- **Confirm:** there is a free 120 V outlet in the dry-goods room, the cable distance to the
  fridge (the plan assumes 10 m or less), and that the inverter's power saving mode (setting
  04) is disabled.

### 2. Long-term power is an isolated Mean Well DDR-15L-5, fused at the bus

- **Chose:** DDR-15L-5 (18 to 75 V in, 5 V 3 A, 4000 VDC isolation), 2 A DC-rated fuse within
  18 cm of the busbar, 18 AWG wire, converter mounted in the battery room.
- **Why:** the bus can reach the inverter's 60.8 V cut-off, so the part needs real margin, and
  isolation keeps battery voltage off every sensor lead if the converter fails.
- **Alternative:** a cheap non-isolated "48 V to 5 V" buck module.
- **Confirm:** who is qualified to make the battery-side connection, and where a tap can
  be made (busbar stud size was not documented).

### 3. The LM2596 modules are excluded from the 48 V design

- **Chose:** not to use them on the battery under any arrangement.
- **Why:** 40 V maximum operating input, 45 V absolute maximum (TI datasheet); the listing for
  the modules on hand says "3.0-40V". The bus runs 48 to 61 V.
- **Alternative:** none that is safe. They remain useful below 35 V.
- **Confirm:** nothing; this one is not a judgement call.

### 4. Fuse type recommendation rests on general practice, not a short-circuit study

- **Chose:** a touch-safe DIN holder for 10 x 38 mm DC fuses, or a Littelfuse FKS 80 V blade
  fuse in an FKH holder.
- **Why:** both are rated above the bus voltage; ordinary 32 V automotive fuses are not.
- **Not done:** the available fault current at the tap point was not calculated, and no fuse's
  interrupting rating was checked against it.
- **Confirm:** the installer should pick the exact fuse.

## Field enclosure

### 5. A Hammond 1554H2GY replaces the generic "$17.99 IP65 junction box"

- **Chose:** Hammond 1554H2GY, 180 x 120 x 60 mm, polycarbonate, solid grey lid, about $25
  to $35.
- **Why:** it has a manufacturer drawing (inside size, M3 insert pattern), so the sled could
  be designed to fit before buying; polycarbonate is UV-stabilised; UL listed Type 4X.
- **Alternative:** the cheaper generic ABS box, with the sled's constants edited to match once
  it is in hand and measured.
- **Confirm:** the extra $10 to $15 is acceptable. If a different box is bought, measure it and
  edit the `BOX` block in the generator.

### 6. Solid lid, not clear

- **Chose:** the grey lid.
- **Why:** less heat build-up and nothing on show at a public site.
- **Alternative:** the clear lid (1554H2GYCL) lets a volunteer see the status light without
  opening the box.
- **Confirm:** preference.

### 7. A printed sled replaces Hammond's steel inner panel

- **Chose:** a printed plate with the same outline and hole pattern as the 1554HPL panel.
- **Why:** steel behind the board's antenna hurts the radio; the sled also carries the corner
  supports, clamps, tie anchors and accessory pads.
- **Confirm:** nothing until the box arrives; then check the four M3 inserts are on a
  132 x 84 mm pattern as drawn.

### 8. The sled must be printed in PETG or ASA, which has to be bought

- **Chose:** PETG as the minimum, ASA preferred.
- **Why:** only PLA is on hand and PLA softens at 55 to 60 C, which a closed box in New
  Orleans can reach.
- **Confirm:** buy one spool before the field install.

### 9. The weather sensor does not go in the box

- **Chose:** BMP280 in a separate louvered shield in shaded outside air.
- **Why:** inside a sealed box it reports the box.
- **Confirm:** whether weather data is wanted on the first install at all. Note that the
  BMP280 modules on hand do not measure humidity.

## Printable case

### 10. The dev board always sits on a Freenove screw-terminal breakout; no "bare board" case was made

- **Chose:** board-on-breakout as the only stack.
- **Why:** screw terminals are far more reliable than Dupont jumpers for field wiring, the
  breakout's outline and four mounting holes are easier to hold than a bare dev board with
  pins underneath, and the breakouts are already owned.
- **Alternative:** a smaller case for a bare board. It would need wires soldered to the pins.
- **Confirm:** that the larger footprint (about 120 x 124 x 36 mm) is acceptable.

### 11. Two variants, because the board for the field is not decided

- **Chose:** variant A = Freenove ESP32-S3 WROOM Lite on the FNK0091 breakout; variant B =
  DevKitC-1 style clone (AYWHP) on the FNK0101 universal breakout.
- **Why:** the FNK0091 has 2 x 20 sockets and Freenove's pin order; Freenove states it is not
  compatible with other brands. The AYWHP boards have 2 x 22 pins, so they only fit the
  universal FNK0101 (0.6 to 1.0 inch wide, up to 24 pins). Walter is expected to need the
  FNK0101 as well; its pin count and row spacing were not checked against its datasheet.
- **Observation:** the board connected to the PC reports 16 MB flash, which matches the AYWHP
  "N16R8" boards rather than the Freenove 2-pack (sold as N8R8). The project docs call it a
  Freenove N8R8. Only one FNK0101 is on hand, so there is no spare carrier for variant B.
- **Confirm:** which physical board is on the bench (look for "FREENOVE" on the silkscreen
  and count the pins: 20 or 22 per side), and which one goes to the field.

### 12. Clamps and fences hold the breakout, not pegs through its mounting holes

- **Chose:** corner pads with fences (0.75 mm clearance all round) and four screw-down toe
  clamps that can be rotated to a clear spot on the board edge. Pilot holes under the
  breakout's own mounting holes are provided as an option.
- **Why:** the hole positions were scaled from a vendor drawing (FNK0091) or assumed
  (FNK0101), not measured. Clamps tolerate 1 to 2 mm of error; pegs do not.
- **Confirm:** measure both breakouts with calipers before printing (see the README's
  checklist).

### 13. One "service window" in the lid instead of a light pipe and button plungers

- **Chose:** a rounded opening above the BOOT and RESET buttons and the status LEDs; the
  buttons are pressed with a pen.
- **Why:** button and LED positions on the clone board are not documented. A window tolerates
  several millimetres of error; a light pipe and plungers do not.
- **Alternative:** printed light pipe and flexure buttons once positions are measured.
- **Confirm:** acceptable for a bench and demo case.

### 14. USB access is a single wide opening, closed at the top by a tongue on the lid

- **Chose:** a 30 x 10.8 mm opening that passes a whole USB-C plug body.
- **Why:** on the breakout the dev board's USB sockets sit 27 to 32 mm inside the case wall,
  so the plug has to pass through the wall. Making the opening open-topped avoids a 30 mm
  unsupported bridge in the print.
- **Known limit:** on the Freenove board the two USB-C sockets are about 10 mm apart, so two
  ordinary plugs cannot be inserted side by side. That is a property of the board.
- **Confirm:** try the owner's actual cable in the printed opening.

### 15. Cable exits are comb slots with labels, sized for assumed cable diameters

- **Chose:** DOOR 4.0 mm, I2C 5.0 mm, 1W 4.2 mm, PWR 5.3 mm, two LOAD slots each for two
  4.0 mm cables. Slots are 0.4 mm shallower than the cable so the lid pinches the jacket;
  four zip-tie anchors inside take the pull.
- **Why:** no cable has been bought yet.
- **Confirm:** measure the real cables and edit `EXITS_LEFT` and `EXITS_RIGHT`.

### 16. M3 brass heat-set inserts by default

- **Chose:** inserts in 4.0 mm holes (lid bosses and clamp bosses).
- **Why:** the lid will be opened repeatedly; threads cut directly in plastic wear out.
- **Alternative:** set `FASTENER = "selftap"` for 2.5 mm holes that M3 screws thread into
  directly. No inserts needed.
- **Confirm:** whether inserts and a soldering iron tip are on hand; none were found in the
  order history.

### 17. Lettering

- **Chose:** three debossed lines, "Hollygrove", "Community Fridge", "door counter", 0.6 mm
  deep, capital height 7 mm and 5.5 mm; exit labels 4.5 mm. The requested single line with a
  dash would have needed letters under 4 mm to fit the lid width.
- **Why:** bold strokes of 1.1 mm or more are reliably legible from a 0.4 mm nozzle.
- **Confirm:** wording.

### 18. The printed case's BMP280 pocket is demo-grade

- **Chose:** a vented pocket on the outside of one wall, covered by a tab on the lid, sized
  loosely (18 x 12 mm inside) rather than to a specific module.
- **Why:** module sizes vary and it shares a wall with warm electronics.
- **Confirm:** nothing.

### 19. Keyholes are oriented for hanging with the cables pointing down

- **Chose:** two ears with keyhole slots; the narrow end is toward the antenna end.
- **Why:** water should drip off the cables, not run into the slots.
- **Confirm:** nothing.

### 20. One accessory pad with a grid of small pilot holes

- **Chose:** a raised pad with 2.0 mm holes on a 5.08 mm grid (9 x 2 in the case; two 5 x 11
  pads on the sled) instead of posts for a particular sensor board.
- **Why:** the HX711, MAX485 and other modules have no common hole pattern.
- **Confirm:** nothing.

## Process

### 21. Dimensions rest on documents, not on a ruler

- **Chose:** to scale vendor drawings using the 2.54 mm pin pitch as the ruler, and to
  build in clearance wherever a number was scaled or assumed. The README lists every number
  and where it came from.
- **Confirm:** the caliper checklist in the README before the first print.

### 22. Pure Python generator; nothing installed

- **Chose:** `manifold3d` and `trimesh`, which were already installed for Python 3.13.
  FreeCAD and OpenSCAD were looked for and not found; neither was installed.
- **Confirm:** nothing.

### 23. Revision policy

- **Chose:** every output carries `rev1` in its name and the script refuses to overwrite an
  existing file. Change the geometry, bump `REV`.
- **Confirm:** nothing.

### 24. The project log was not updated

- **Chose:** not to edit `project-log.md`, because the instruction for this task was to touch
  nothing outside the three locations above.
- **Why it is listed:** the projects tree's standing rule is that the log is updated every
  session. Whoever closes out this session should add the entry.
- **Confirm:** nothing; it is a hand-off note.
