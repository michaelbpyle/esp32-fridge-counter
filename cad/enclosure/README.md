# Door-counter enclosure (rev1)

Root: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\enclosure\`

Generator: `generate_enclosure.py`. Outputs: `out\` (STL and 3MF for every part, preview PNGs,
`validation-rev1.json`). Power, weatherproofing and mounting advice:
`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\power-and-enclosure.md`.
Choices made without the owner:
`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\enclosure.md`.

## What is here

A printable case for bench, demo and sheltered indoor use, plus a "sled" that carries the same
electronics inside a bought IP66 junction box (Hammond 1554H2GY) for outdoor use. The printed
case is NOT weatherproof.

| Part | Files in `out\` | Print qty |
|---|---|---|
| Case base | `case-base-<variant>-rev1.stl` / `.3mf` | 1 |
| Case lid | `case-lid-<variant>-rev1.stl` / `.3mf` | 1 |
| Toe clamp | `toe-clamp-rev1.stl` / `.3mf` | 4 per case, 4 per sled |
| Sled for Hammond 1554H / 1554T | `sled-1554h-<variant>-rev1.stl` / `.3mf` | 1 |

Variants:

| Variant tag | Stack | Case outer (X x Y, height closed) | Over ears and pocket |
|---|---|---|---|
| `fnk0091` | Freenove ESP32-S3 WROOM / Lite on Freenove FNK0091 breakout | 119.5 x 123.5, 36.0 mm | 149.5 mm wide |
| `fnk0101` | ESP32-S3-DevKitC-1 style clone (AYWHP) on Freenove FNK0101 universal breakout | 119.3 x 131.3, 36.0 mm | 149.3 mm wide |

Which board goes to the field is undecided, so both are generated. The AYWHP board has 22 pins
per side and does not fit the FNK0091 (Freenove states it is for Freenove boards only).

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

## Assembly

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
cd cad\enclosure
set PYTHONDONTWRITEBYTECODE=1
python generate_enclosure.py                      # everything, about 8 minutes with renders
python generate_enclosure.py --variant a --no-render --outdir %TEMP%\enc   # about 1 minute
```

The script refuses to overwrite a delivered file. When geometry changes, bump `REV` at the top
of the script (outputs become `-rev2`); never delete rev1.

Another board (for example Walter, 55 x 24.8 mm): a `walter` entry already exists in `BOARDS`
and a commented example `c` variant in `VARIANTS`. Uncomment it, correct `usb_edge`, `usb_x`,
`window` and pin spacing from the datasheet, then run. Other cables: edit `EXITS_LEFT` and
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

In `out\`: `preview-case-closed-`, `-open-`, `-exploded-`, `-usb-end-`, `preview-lid-underside-`,
`preview-sled-in-box-`, `preview-sled-bare-`, each with `fnk0091-rev1.png` or `fnk0101-rev1.png`.
The green, yellow and grey blocks are placeholders for the boards, terminals and plug.
