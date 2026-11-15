# Demo door: technical notes (door rev 2, base plate rev 1)

Folder: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\demo-door\`  
Decisions made without the owner: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\demo-door.md`

Nothing here has been test-printed. Every number comes from the reports in `checks\`.

## Sizes

- Overall 152.4 mm tall, 81.3 mm wide at the sill and cornice (75.3 mm across the jambs),
  entry tunnel 50.8 mm deep. Door opening 51.3 x 107.4 mm.
- Door 106 x 50 x 12.6 mm, planks, Z-brace, knob 8 mm proud; sign "HOLLYGROVE COMMUNITY
  FRIDGE" engraved 0.4 mm into the header.
- Print plate 152.4 x 128.9 x 50.8 mm (fits the 256 mm bed). Base plate 133.5 x 120.3 x
  19.0 mm.

## Files

- `print\demo-door-rev2.stl` / `.3mf`: frame and door, one plate, two separate bodies.
- `print\demo-door-foot-rev1.stl` / `.3mf`: base plate. Rev 1 still fits door rev 2
  because the sill did not change; regenerating it gives a byte-identical STL.
- `source\demo-door-generator.py`: door and frame. Every dimension is a named constant at
  the top, including the switch sizes. `REV` is stamped into the file names.
- `source\demo-door-foot-generator.py`: base plate (`FOOT_REV`). Reads the sill size from
  the door generator.
- `source\demo-door-check.py`, `source\demo-door-foot-check.py`: numerical checks; they
  write `checks\demo-door-rev2-check.txt` and `checks\demo-door-foot-rev1-check.txt`.
- `source\demo-door-render.py`: the previews in `pictures\` (`<view>-rev2.png`); the
  base-plate picture comes from the foot check.

## Regenerating

Use the system Python 3.13 (manifold3d, trimesh, numpy and matplotlib were already
installed). The scripts find the other folders on their own, so they run from any
directory.

1. Edit constants and raise `REV` (or `FOOT_REV`). Never reuse a revision number; the
   generators refuse to overwrite. Move the superseded outputs and scripts to
   `shelved\rev<N>\` first.
2. `python source\demo-door-generator.py` (add `--out <folder>` to try changes in a
   scratch folder).
3. `python source\demo-door-check.py --orig "\\TRUENAS\Pyle-TNAS_Individual\Projects\3d-prints\box-system\research\Clamshell+Parts+Box+Standard.stl"`
4. `python source\demo-door-render.py` (about a minute).
5. `python source\demo-door-foot-check.py` (swing clearance, tipping, base-plate picture).

## Print settings (Creality PLA on the Bambu Lab P1S)

- Open the `.3mf` in Bambu Studio and do not move or rotate the bodies.
- Generic PLA profile, nozzle 210 to 220 C, bed 55 to 60 C, part fan 100 %.
- 0.20 mm Standard, 0.4 mm nozzle, 3 walls, 15 % infill, 5 top and 4 bottom layers.
- No supports, no brim (a brim would weld the hinge gaps), default elephant-foot
  compensation.
- Bridges: 3.7 mm or less everywhere, except the magnet pocket ceiling on the back of the
  door. That is a 15.1 mm bridge only 0.6 mm above the bed; default bridge settings
  handle it, and the foam tape hides any sag.
- Two colours with an AMS: "Split to objects" and give the door red. Otherwise one colour.

## Switch and magnet (rev 2)

The owner's white surface-mount pair: two identical L-shaped blocks. Measured with
calipers on 2026-11-14, including the foam tape: length 33.91, overall width 14.27, body
width 7.88, body height 9.21, flange thickness 2.83 mm (`SW_*` constants).

- The switch goes on the inside face of the latch-side (knob-side) tunnel wall, long axis
  vertical, top end 104 mm above the table, body toward the door. It sits in an outline
  with 0.4 mm clearance all round: 1.5 mm lips along the sides and 7 mm end walls. Both
  end walls have a wire gap on the body half only, so the switch fits only body-forward.
- The magnet goes in a 0.6 mm pocket in the back of the door (0.4 mm clearance), body
  outer edge 4.2 mm in from the latch edge, at the same height as the switch. The pocket
  is on the bed face, so it can only be a recess. A rectangle cannot force the magnet's
  orientation, so a 3 mm notch on the flange side marks it.
- Door shut: the body faces are 3.00 mm apart, parallel, over the full 33.91 mm length,
  facing each other across a 4.31 mm wide strip. The magnet body centre is 49.5 mm from
  the hinge axis.
- Nearest distance between the switch and magnet blocks as the door opens: 3.0 mm at 0,
  7.1 at 5, 11.1 at 10, 15.1 at 15, 19.2 at 20, 27.3 at 30 degrees. The angle at which
  the switch actually changes state depends on the part's sensing distance, which was
  not measured.
- Wire: up out of the top end into the roof corner, then a zip tie through two slots in
  the roof, 40 to 44.5 mm behind the front face. If the wire comes out of the bottom end,
  use the two slots low in the same wall.
- The stop rib on the latch jamb now ends below the switch, so the magnet can pass where
  its top used to be.

## Validation (door rev 2)

- Two separate bodies, both watertight; smallest door-to-frame distance in the print
  pose 0.177 mm (the cone joints, same as the original hinge's 0.177).
- Hinge: six cone joints, gap 0.177 mm square to the cone face (0.25 mm along the axis),
  flat faces 0.40 mm, first-layer relief 1.48 mm.
- Height 152.400 mm, entry depth 50.800 mm.
- Overhangs over 50 degrees: bridges of 3.7 mm or less, outline lips 1.5 mm, the sign
  letters, and the 15.1 mm magnet pocket ceiling.
- Swing from 180 to 0 degrees in 2.5 degree steps, also with the door shifted 0.2 mm
  along and 0.15 mm across the axis, with both blocks fitted: no overlap. Magnet block to
  frame or switch: never closer than 2.83 mm. The door lands on the stop rib at 0.093 mm.
- Minimum wall: frame 0.99 mm, door 1.02 mm (chamfer edges and the pocket).
- Base plate with door rev 2: door and magnet clear it by at least 4.55 mm.

## Stability and the base plate

On its own sill the stand tips at 0.26 to 0.33 N at the knob. With the base plate
zip-tied on, the worst case over door angles 0 to 180 degrees is 1.70 N opening and
1.71 N closing; 2.11 / 2.13 N with 16 quarters (91 g) in the wells. With a friction
coefficient of 0.3 it slides at about 0.55 N (0.82 N with quarters) before it tips, so
rubber feet help. The base plate reaches 48 mm in front of the frame and 25 / 14 mm past
the hinge / latch sides. The zip ties go through the frame's two existing sill holes.

## Constants to tune after the first print

- Hinge will not crack free: `CONE_AXIAL_GAP` 0.25 to 0.30 or 0.35, `FLAT_GAP` 0.40 to 0.50.
- Hinge loose: `CONE_AXIAL_GAP` to 0.20.
- Door rubs: `GAP_LATCH`, `GAP_TOP`, `GAP_BOTTOM`, `SWEEP_CLR`.
- Switch does not change state: `BODY_GAP` (3.0) smaller, or `MAG_EDGE_IN` (4.2) larger
  to align the bodies more (check the swing again).
- Outlines too tight or loose: `PAD_CLR`.
- Base plate size: `FOOT_FRONT`, `FOOT_HINGE_SIDE`, `FOOT_LATCH_SIDE`.

## Known risks

- Hinge cones are 3.2 times Nick Johnson's size with his gap kept: more area that could fuse.
- The switch's release distance is unknown; the 3 mm gap and the opening distances above
  are geometry only.
- The magnet pocket ceiling is a long, low bridge.
- No latch: the door stays shut by friction and the stop rib.
- The stand slides before it tips unless it has rubber feet.

## Credit and licence

The hinge is the pinless cone hinge from Nick Johnson's "Clamshell Parts Box" (MakerWorld
model 786443), licensed CC BY-SA. Its working geometry is reproduced here, scaled up:
alternating knuckles on 45 degree male and female cones, a 0.25 mm axial offset, printed
open at 180 degrees with the axis flat on the bed. As a derivative, this demo door
(models and scripts) is shared under CC BY-SA with credit to Nick Johnson.
