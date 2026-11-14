# Decisions made without owner input — demo door

Date: 2026-11-14. The owner was asleep and could not be asked. Each item says what was
chosen, why, what the alternative was, and what the owner should confirm. Nothing was
printed, measured or installed. Files written:

- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\demo-door\`
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\demo-door.md`

Numbers quoted below are from `demo-door-rev1-check.txt` in the design folder.

## Tools and layout

### 1. Pure Python generator (manifold3d and trimesh), not FreeCAD

- **Chose:** one Python generator, `demo-door-generator.py`, using the libraries already
  installed. Nothing was installed.
- **Why:** exact control of 0.18 mm gaps and a repeatable numerical check of the STL.
  FreeCAD 1.1 is installed but was not needed.
- **Alternative:** a FreeCAD macro, as some parts in the 3d-prints tree use.
- **Confirm:** acceptable for a part kept in this project rather than the 3d-prints tree.

### 2. Frame printed on its front face, door flat beside it, opened 180 degrees

- **Chose:** the suggested layout. The hinge axis is at the door's mid-thickness (6.3 mm
  above the bed) so the closed door sits flush in the opening. The axis is centred in the
  12 mm hinge-side pilaster, and the door's three hinge arms pass through notches in it.
- **Why:** the tunnel rises straight off the bed with no overhangs, and the door's
  largest face is on the bed.
- **Alternative:** hinge outside the frame on its outer edge (needs a separate leaf and
  looks less like a door).
- **Confirm:** nothing; the swing check passes from 180 to 0 degrees.

### 3. Door and front slab 12.6 mm thick

- **Chose:** T = 12.6 mm.
- **Why:** the 9 mm switch barrel lies inside the door's top edge and the header, with
  skins of 1.2 to 1.4 mm round the bore.
- **Alternative:** a thinner door with the magnet glued to its face.
- **Confirm:** that the real barrel is 9 mm (see item 8).

### 4. Header 38 mm tall, door 106 x 50 mm

- **Chose:** a tall sign board over the door.
- **Why:** the switch (29 mm long) is buried vertically in the header, and the sign makes it
  look like a little shopfront. Proportions stay door-like (opening about 2.1 : 1).
- **Alternative:** switch in the latch jamb, a shorter header and a taller door.
- **Confirm:** the look.

## Hinge

### 5. Nick Johnson's cone hinge, scaled 3.2 times, his gap kept unscaled

- **Chose:** six cone joints (three door knuckles 16 mm long between frame knuckles),
  45 degree male cones from r 4.0 to r 1.0 on the frame, female cones in the door,
  0.25 mm offset along the axis, which is 0.177 mm square to the cone face.
- **Why:** measured on his Standard box STL, his offset is 0.25 along the axis and 0.177
  square to the face on both the inner and the end joints. The brief said "0.125 at the
  end joints"; the measurement did not show that, so the measured value was used on all
  six joints. The radius was scaled from his r 1.25 for a part about 3 times larger.
- **Alternative:** keep his 3 mm knuckle size (too small to carry a 36 g door on a
  152 mm stand) or scale the gap too (risks a sloppy door).
- **Confirm:** on the first print that the joints crack free by hand. If not, set
  `CONE_AXIAL_GAP` to 0.30 or 0.35.

### 6. No round-knuckle-in-hollow fit: the cones alone locate the door

- **Chose:** plain knuckle blocks with 0.40 mm between flat faces; only the cones touch.
- **Why:** his knuckle round turns in a hollow with 0.196 mm clearance. Leaving it out
  removes one more fit that could fuse, and the cones already centre the axis.
- **Alternative:** copy his round-in-hollow as well.
- **Confirm:** that the door does not wobble more than wanted; lower `CONE_AXIAL_GAP` if
  it does.

### 7. Rule joint and chamfers so the door can swing

- **Chose:** a hollow of radius `COVE_R` along the door's hinge edge and 2 mm 45 degree
  chamfers on both front edges of the hinge pilaster.
- **Why:** without either, the swing check found collisions. With them, the worst overlap
  from 180 to 0 degrees in 2.5 degree steps, including the door shifted 0.2 mm along and
  0.15 mm across the axis, is 0.00000 mm3.
- **Alternative:** a hinge axis outside the frame face.
- **Confirm:** nothing.

### 8. Door stop: 45 degree bevel on the door meeting a 45 degree rib

- **Chose:** a 3 mm bevel on the back of the door's latch edge that lands on a rib inside
  the latch jamb, 0.093 mm away when flush; 0.5 degrees past flush overlaps 82 mm3.
- **Why:** prints without support in this pose; a square stop would need a bridge.
- **Alternative:** a bridged square stop, or a magnetic catch.
- **Confirm:** that the door stops flush.

## Switch and magnet

### 9. Recessed switch dimensions taken from the listing line "29*15.5*9mm"

- **Chose:** barrel 9.0 mm, flange 15.5 mm diameter, 29 mm overall; flange thickness
  2.0 mm assumed. Bore 0.4 mm over the barrel with three 0.4 mm crush ribs.
- **Why:** the Amazon listing (B07YFBG27Y; the same product on amazon.com.be B07Z4NCWDD)
  gives only that line, wire 33 cm, sensing distance 10 to 15 mm, normally closed.
- **Alternative:** wait for a caliper measurement.
- **Confirm:** measure barrel, flange and overall length with a caliper before printing;
  correct `SW_*` and issue rev 2 if they differ.

### 10. Switch in the header, magnet in the door's top edge, end to end on one axis

- **Chose:** the switch barrel goes up into the header from the top of the doorway; the
  magnet goes down into the door's top edge, 15 mm in from the latch edge (41.6 mm from the
  hinge axis). Shut, the flanges are 2.6 mm apart. The magnet moves 10.9 mm sideways at
  15 degrees open.
- **Why:** the latch edge is too thin to hide a 9 mm barrel across its width, and the top
  edge keeps the parts out of the swing.
- **Alternative:** latch jamb mount (farther from the hinge, so earlier release, but the
  barrel would show).
- **Confirm:** that the switch changes state early enough in the swing for the counter.

### 11. Wire exit through a pocket and two zip-tie slots

- **Chose:** the bore ends in a pocket open to the back of the sign board; two slots in the
  tunnel roof take a zip tie.
- **Why:** hides the leads and gives strain relief without supports.
- **Alternative:** a channel cut in the roof (an open groove would need a bridge).
- **Confirm:** nothing.

### 12. Surface-mount pair: a plain variant, tape-mounted, no pilot holes

- **Chose:** `demo-door-rev1-surface-switch.stl`, the same parts with no bores and zip-tie
  slots in the latch-side tunnel wall. Magnet on the door back at least 5 mm in from the
  latch edge, switch flat on the latch-side tunnel wall at least 2 mm behind it.
- **Why:** PiShop SKU 170 is SparkFun COM-13247, published only as "34 x 41 x 6.5 mm",
  gap 20 +/- 5 mm, normally open; the screw-hole spacing is not published. A swing check
  with 15 x 30 x 7 mm stand-in blocks showed no collision at 4 mm or more in from the
  latch edge, and a collision with the stop rib at 3 mm.
- **Alternative:** guess a hole spacing and drill pilots (wrong holes are worse than none).
- **Confirm:** measure the parts and the hole spacing; set `SURF_PILOT_SPACING` for rev 2.

## Look and stability

### 13. Sign "HOLLYGROVE COMMUNITY FRIDGE", planks, Z-brace, knob

- **Chose:** a cottage door and a sign engraved 0.4 mm into the front face (on the bed).
- **Why:** "cute"; HOLLYGROVE is the project name in the project documents.
- **Alternative:** a blank header.
- **Confirm:** the text; change `SIGN_LINES` or set it to `[]`.

### 14. Stability from a separate printed foot, zip-tied on, with optional coin ballast

- **Chose:** `demo-door-foot-rev1.stl`, its own generator (`demo-door-foot-generator.py`,
  `FOOT_REV` 1), leaving the rev 1 door and frame unchanged. A 3 mm plate reaching 48 mm in
  front of the frame and 25 / 14 mm past the hinge / latch sides, a 3 mm locating lip, two
  zip ties through the frame's existing sill holes, and two wells for 8 US quarters each.
- **Why:** on its sill alone the stand tips at 0.25 to 0.34 N at the knob, less than a new
  hinge may need. With the foot the worst case over 0 to 180 degrees is 1.71 N opening and
  1.72 N closing (2.12 / 2.15 N with 16 quarters); the door clears the foot by 4.55 mm or
  more. A foot cannot be part of the frame in its print pose (it would hang below the bed).
  Zip ties hold the frame down whatever the print tolerance; a press fit or friction ribs
  would not.
- **Alternative:** printed snap pegs in the sill holes (their 45 degree barbs would be
  weak), or a weighted frame in a rev 2.
- **Confirm:** that 2.5 mm zip ties at least 100 mm long are on hand, and add rubber feet:
  at about 0.55 N it slides before it tips (friction coefficient 0.3 assumed).

### 15. PLA first, one filament, no brim

- **Chose:** print advice for Creality PLA at 0.20 mm, 3 walls, 15 % infill, no supports,
  no brim.
- **Why:** the owner's filament on hand; a brim would bridge the hinge gaps at the bed.
- **Alternative:** PETG (more prone to fusing print-in-place gaps).
- **Confirm:** nothing.
