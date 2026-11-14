# Demo door (rev 1)

A miniature cottage door in a door frame for showing the reed-switch door counter on a
table. It prints as one plate with the hinge already assembled (print-in-place), stands
on its own, and has mounts for a reed switch on the frame and its magnet on the door.

- Overall 152.4 mm tall (6 in), 81.3 mm wide at the sill and cornice (75.3 mm across the
  jambs), entry tunnel 50.8 mm (2 in) deep. Door opening 51.3 x 107.4 mm.
- Door 106 x 50 x 12.6 mm, cottage planks, Z-brace, knob; sign "HOLLYGROVE COMMUNITY
  FRIDGE" engraved in the header.
- Nothing here has been test-printed. Every number below comes from the numerical checks
  in `demo-door-rev1-check.txt`, not from a print.

Folder: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\demo-door\`  
Decisions made without the owner: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\demo-door.md`

## Files

- `demo-door-rev1.stl` / `demo-door-rev1.3mf`: print plate for the recessed press-in
  switch pair (Gebildet, Amazon B07YFBG27Y). Already oriented; z = 0 is the bed.
- `demo-door-rev1-surface-switch.stl` / `.3mf`: the same door and frame with no switch
  bores, for the surface-mount pair (PiShop SKU 170). Zip-tie slots in the latch-side
  tunnel wall instead of the roof.
- `demo-door-foot-rev1.stl` / `.3mf`: separate base plate the frame is zip-tied into, so
  it does not tip (see Stability and the foot). Made by `demo-door-foot-generator.py`,
  checked by `demo-door-foot-check.py`.
- `demo-door-generator.py`: the generator. Every dimension is a named constant at the top.
- `demo-door-check.py`: numerical checks of the written STL files; output saved in
  `demo-door-rev1-check.txt`.
- `demo-door-render.py`: the preview images `demo-door-rev1-*.png`:
  - `print-pose-top.png`, `print-pose-iso.png`: the plate as it sits on the bed.
  - `front.png`, `standing-closed.png`, `standing-open-100.png`, `back-open-100.png`: in use.
  - `hinge-sections.png`: cross-sections of the hinge, print pose and closed, and the stop.
  - `switch-sections.png`: the switch and magnet bores.

## Print settings (Creality PLA on the Bambu Lab P1S)

- Open `demo-door-rev1.3mf` in Bambu Studio. Do not rotate or move either body: the hinge
  is assembled as it lies.
- Filament profile: Generic PLA. Nozzle 210 to 220 C, bed 55 to 60 C (textured PEI or
  smooth PEI with glue stick), part fan at 100 %.
- Process: 0.20 mm Standard, 0.4 mm nozzle, 3 walls, 15 % infill (gyroid or grid),
  5 top and 4 bottom layers.
- Supports: OFF. Brim: OFF (a brim would weld the hinge gaps at the bed). Leave Bambu
  Studio's elephant-foot compensation at its default.
- Bridges in the model are 3.7 mm or shorter (switch-bore roofs, hinge-notch tops, slots,
  the 0.4 mm deep sign letters). Default bridge settings handle them.
- Colour: one filament prints the whole plate. For a white frame and a red door with an
  AMS, use "Split to objects" in Bambu Studio and give the door red. Without an AMS,
  print it all in one colour; black or white both work for the photos.
- Weight about 125 g at these settings.

## Freeing the hinge

1. Let the bed cool fully, then flex the plate and lift the frame and door off together.
2. Check the six hinge joints (where the door's three hinge arms pass through the frame's
   hinge jamb). Clean off any stringing with a hobby knife.
3. Hold the frame up off the table. The door lies "open 180 degrees" beside it. Fold the
   door down and round toward the frame's front face (the face that was on the bed),
   firmly but slowly. The cone joints crack free with a click each.
4. Work the door through its whole travel ten or twenty times. When closed it lands on a
   45 degree stop rib inside the latch side, flush with the frame front.
5. Stand the frame up on its sill. Open the door with the knob; it swings out toward you.

## Fitting the recessed switch pair (Gebildet B07YFBG27Y)

- Measure both halves with a caliper before printing. The listing gives only "29 x 15.5
  x 9 mm". The generator assumes a 9.0 mm barrel, a 15.5 mm flange 2.0 mm thick (the
  thickness is a guess), and 29 mm overall. Correct `SW_BARREL_D`, `SW_FLANGE_D`,
  `SW_FLANGE_T`, `SW_TOTAL_L` if they differ, then regenerate as rev 2.
- Switch (the half with wires): open the door. In the top of the doorway, under the sign,
  is a round hole with a recess for the flange. Feed the leads up into it; they come out
  in a pocket on the back of the sign board. Press the barrel in until the flange sits in
  its recess. Three crush ribs hold it.
- Wire exit: from the pocket, run the leads down onto the tunnel roof and tie them with a
  small zip tie through the two slots in the roof, then off the back of the stand.
- Magnet: press it into the hole in the door's top edge, flange in the notch.
- When the door is shut the two flanges face each other on one axis, 2.6 mm apart (rated
  sensing distance 10 to 15 mm). The magnet sits 41.6 mm from the hinge axis and moves
  sideways 3.6 mm at 5 degrees open, 7.3 mm at 10, 10.9 mm at 15 and 14.4 mm at 20, so the
  switch should change state within the first 15 to 20 degrees of opening (analysis only).
- The flange (15.5 mm) is wider than the door and header are thick (12.6 mm): both flanges
  stand about 1.5 mm proud front and back. The swing check includes them.
- Too loose: a drop of glue or a wrap of tape. Too tight: ream with a 9 mm drill by hand, or
  lower `RIB_H` / raise `BORE_CLR` in a new revision.
- The listing says "Normally Closed"; check with a multimeter which state means "door
  shut" before writing firmware logic around it.

## Fitting the surface-mount pair (PiShop SKU 170, SparkFun COM-13247)

Print `demo-door-rev1-surface-switch.stl`. The hole spacing of this pair is not published,
so the variant has no pilot holes: mount both halves with double-sided foam tape.

- Magnet: on the back of the door, near the top, with its outer edge at least 5 mm in from
  the latch edge (the edge with the knob).
- Switch: flat on the inside face of the latch-side tunnel wall, beside the magnet, with
  its front edge at least 2 mm behind the magnet when the door is shut (about 22 mm behind
  the frame's front face for a 7 mm thick magnet).
- Wire exit: tie the leads through the two zip-tie slots in the same wall and run them out
  the back.
- A swing check with 15 x 30 x 7 mm stand-in blocks in those places found no collision;
  with the magnet only 3 mm in from the latch edge it hit the stop rib. The real parts were
  not measured. Swing the door slowly before the tape sets.
- Once the hole spacing is measured, set `SURF_PILOT_SPACING` (mm) and regenerate as a new
  revision to get 1.8 mm pilot holes.

## Stability and the foot

The frame (about 87 g) and door (36 g) are light. On its own sill the stand stands with the
door in any position, but a horizontal push or pull along the knob's path of only 0.25 to
0.34 N tips it (0.17 N if you pull the open door straight forward). A slightly stiff new
hinge needs more than that, so print the foot.

`demo-door-foot-rev1.stl` (and `.3mf`) is a separate base plate, 133.5 x 120.3 mm, 19 mm
tall at the ballast block, about 64 g. The door and frame files are unchanged.

- Print it flat as it comes, same PLA settings, no supports, no brim. The only bridges
  are two 3.2 mm groove ceilings on the underside.
- It reaches 48 mm in front of the frame, 25 mm past the sill on the hinge side and
  14 mm on the latch side. A 3 mm lip round the sill (0.4 mm clearance) locates the frame;
  the door's bottom edge clears the foot by at least 4.5 mm through its whole swing.
- Attaching: stand the frame in the lip. Push a zip tie (2.5 mm wide, 100 mm or longer)
  down through each of the two holes in the tunnel floor and the matching hole in the
  foot, along the groove under the foot, up through the slot just behind the sill, and
  over the sill's back edge to its own head. Pull both snug and trim. The ties do the
  holding, so print tolerance does not matter; the lip does not need to grip.
- Ballast (optional): two wells behind the frame each take a stack of 8 US quarters
  (24.26 mm, 5.67 g each): 16 quarters, 91 g. A notch at the back of each well lets you
  push the coins out.

Force at the knob (horizontal, along the knob's path) that tips the stand, worst case over
door angles 0 to 180 degrees, opening / closing direction:

- No foot: 0.32 / 0.25 N.
- Foot: 1.71 / 1.72 N.
- Foot with 16 quarters: 2.12 / 2.15 N.

Before it tips, it slides: about 0.55 N with the foot, 0.82 N with the quarters, for a
friction coefficient of 0.3. Four small stick-on rubber feet or a silicone mat under the
foot stop that. Full table: `demo-door-foot-rev1-check.txt`; picture:
`demo-door-foot-rev1-standing-open-100.png`. The foot's own files come from
`demo-door-foot-generator.py` (`FOOT_REV`, `FOOT_FRONT`, `FOOT_HINGE_SIDE`,
`FOOT_LATCH_SIDE`, `COINS_PER_WELL`) and are checked by `python demo-door-foot-check.py`.

## Regenerating

Run in the `cad\demo-door` folder with the system Python 3.13 (needs manifold3d, trimesh,
numpy, matplotlib; all were already installed):

1. Edit constants at the top of `demo-door-generator.py` and raise `REV` (never reuse a
   revision number; the generator refuses to overwrite existing files).
2. `python demo-door-generator.py` (or `--out <folder>` to try changes in a scratch folder).
3. `python demo-door-check.py --dir . --orig "\\TRUENAS\Pyle-TNAS_Individual\Projects\3d-prints\box-system\research\Clamshell+Parts+Box+Standard.stl"`
   (the check script reads the `REV` from the generator).
4. `python demo-door-render.py --out .` (about 50 s; writes the PNGs).

## Constants to tune after the first print

- Hinge fused, will not crack free: raise `CONE_AXIAL_GAP` from 0.25 to 0.30 or 0.35 and
  `FLAT_GAP` from 0.40 to 0.50.
- Hinge loose or the door sags: lower `CONE_AXIAL_GAP` to 0.20.
- Door rubs the frame: raise `GAP_LATCH`, `GAP_TOP`, `GAP_BOTTOM` or `SWEEP_CLR`.
- Door swings past flush or stops short: `STOP_CLR`.
- Switch or magnet fit: `BORE_CLR`, `RIB_H`, the `SW_*` dimensions.
- Different sign text: `SIGN_LINES` (or `[]` for none).

## Known risks on the first print

- The hinge cones are 3.2 times the size of Nick Johnson's with his gap kept, so they
  have more area that could fuse. The gap is 0.177 mm square to the cone face, the same
  as his; the flat faces have 0.40 mm and the first layer 1.48 mm of relief.
- The switch dimensions are from a one-line listing; the flange thickness is a guess.
- The switch release angle depends on the real magnet strength; it is estimated, not
  tested.
- The skin over the switch bore is 1.2 mm on top and 1.0 mm under the sign letters.
- The door has no latch; it stays shut by friction and the stop rib.
- Without the foot the stand tips easily; with it, it slides before it tips unless it has
  rubber feet (see Stability and the foot).

## Credit and licence

The hinge is the pinless cone hinge from Nick Johnson's "Clamshell Parts Box" (MakerWorld
model 786443), licensed CC BY-SA. Its working geometry (alternating knuckles held on 45
degree male and female cones, a 0.25 mm axial offset, printed open at 180 degrees with the
axis flat on the bed) is reproduced here, scaled up. As a derivative, this demo door
(models and generator) is shared under the same licence, CC BY-SA, with credit to Nick
Johnson.
