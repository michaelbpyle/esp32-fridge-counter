r"""Demo door FOOT: a separate base plate that the rev 1 demo door frame stands in, so the
stand does not tip over when the door is worked by its knob.

    python demo-door-foot-generator.py               writes into ..\print
    python demo-door-foot-generator.py --out DIR     writes into DIR (scratch tests)

Writes demo-door-foot-rev<FOOT_REV>.stl / .3mf and refuses to overwrite: bump FOOT_REV first.
Then run demo-door-foot-check.py (swing clearance, tipping force, overhangs, render).

The door and frame are NOT changed: their dimensions are read from demo-door-generator.py.

What it is (in-use coordinates, the same as demo-door-generator.py):
    x  up. The foot's plate is x = -FOOT_T .. 0; the frame's sill stands on it at x = 0.
    y  width; the hinge axis is the line y = 0 (hinge side is -y).
    z  depth; z = 0 is the frame's front face, the door swings out to z < 0, the tunnel
       runs back to z = DEPTH.
- A plate with rounded corners reaching FOOT_FRONT in front of the frame and past both sides.
- A low lip round the sill (LIP_CLR clearance, LIP_H tall: the door bottom is 7.8 mm up, so
  it passes over the lip). The lip only locates the frame.
- Retention: two zip ties, each down through one of the frame's two existing 4.5 mm sill
  holes, through a matching hole in the plate, along a groove in the plate's underside, up
  through a slot behind the sill and back over the sill's rear edge. Zip ties pull tight
  whatever the print tolerance is; nothing relies on a press fit.
- Optional ballast: two wells behind the frame, each for a stack of US quarters.
Printed flat, bottom down, no supports. The only downward faces are the groove ceilings
(3.2 mm bridges).
"""
import argparse
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
import numpy as np
import trimesh
from manifold3d import Manifold, OpType

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("gen", os.path.join(HERE, "demo-door-generator.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

FOOT_REV = 1

# ---- plate -----------------------------------------------------------------------------------
FOOT_T = 3.0             # plate thickness
FOOT_FRONT = 48.0        # plate reaches this far in front of the frame's front face
FOOT_HINGE_SIDE = 25.0   # ... this far beyond the sill on the hinge side (-y)
FOOT_LATCH_SIDE = 14.0   # ... and on the latch side (+y)
CORNER_R = 8.0           # rounded plate corners (plan view)
TOP_CH = 1.0             # 45 degree chamfer on the plate's top edge
BOT_CH = 0.4             # 45 degree first-layer chamfer (elephant foot)

# ---- lip round the sill ------------------------------------------------------------------------
LIP_H = 3.0              # above the plate; door bottom is gen.X_D0 = 7.8 mm above the sill bottom
LIP_W = 2.4
LIP_CLR = 0.4            # sill to lip, each side

# ---- zip-tie retention (uses the frame's existing sill holes) ----------------------------------
TIE_HOLE_D = 4.5         # same as the sill holes
TIE_W, TIE_SLOT_Z = 3.2, 2.0      # slot through the plate behind the sill (for 2.5 mm ties)
TIE_GROOVE_D = 1.2       # groove in the underside so the tie does not rock the plate
TIE_NOTCH = 6.0          # gap in the rear lip where the tie comes over the sill's back edge

# ---- ballast wells (US quarters: 24.26 mm dia, 1.75 mm thick, 5.67 g - US Mint) ------------------
COIN_D, COIN_T, COIN_G = 24.26, 1.75, 5.67
COINS_PER_WELL = 8
N_WELLS = 2
WELL_CLR = 0.8           # on the diameter
WELL_WALL = 2.4
THUMB_W = 9.0            # notch at the back of each well to get the coins out

# ---- derived (sill footprint from the door generator) ------------------------------------------
SILL_Y0 = gen.Y_PIL0 - gen.EAR - gen.CORNICE
SILL_Y1 = gen.Y_OUT1 + gen.EAR + gen.CORNICE
SILL_Z0, SILL_Z1 = 0.0, gen.DEPTH
TIE_Y = (gen.Y_PIL1 + 12.0, gen.Y_LJ - 12.0)      # the sill's screw holes (demo-door-generator.py)
TIE_HOLE_Z = 33.0
LIP_Z1 = SILL_Z1 + LIP_CLR + LIP_W               # outside of the rear lip
WELL_D = COIN_D + WELL_CLR
WELL_DEPTH = COINS_PER_WELL * COIN_T + 1.0
BLOCK_Z0 = LIP_Z1                                # ballast block sits right behind the rear lip
BLOCK_Z1 = BLOCK_Z0 + WELL_D + 2 * WELL_WALL
PLATE_Y0 = SILL_Y0 - FOOT_HINGE_SIDE
PLATE_Y1 = SILL_Y1 + FOOT_LATCH_SIDE
PLATE_Z0 = -FOOT_FRONT
PLATE_Z1 = BLOCK_Z1 + 2.0
EPS = 0.01


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.hull_points([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])


def rounded_slab(y0, y1, z0, z1, r, levels, n=24):
    """Plate with rounded corners in plan; `levels` = [(x, inset), ...] bottom to top."""
    pts = []
    for x, ins in levels:
        rr = r - ins
        for cy, cz, a0 in ((y1 - r, z1 - r, 0), (y0 + r, z1 - r, 90), (y0 + r, z0 + r, 180), (y1 - r, z0 + r, 270)):
            for t in np.radians(np.linspace(a0, a0 + 90, n)):
                pts.append((x, cy + rr * np.cos(t), cz + rr * np.sin(t)))
    return Manifold.hull_points(pts)


def cyl_x(x0, x1, y, z, r):
    return Manifold.cylinder(x1 - x0, r, r, 96).transform([[0, 0, 1, x0], [1, 0, 0, y], [0, 1, 0, z]])


def build_foot():
    """The foot in in-use coordinates (see the module docstring)."""
    t = FOOT_T
    plate = rounded_slab(PLATE_Y0, PLATE_Y1, PLATE_Z0, PLATE_Z1, CORNER_R,
                         [(-t, BOT_CH), (-t + BOT_CH, 0.0), (-TOP_CH, 0.0), (0.0, TOP_CH)])
    # lip: outer box minus the sill pocket
    c, w = LIP_CLR, LIP_W
    lip = box(-1.0, LIP_H, SILL_Y0 - c - w, SILL_Y1 + c + w, SILL_Z0 - c - w, SILL_Z1 + c + w) - \
        box(-0.5, LIP_H + 1, SILL_Y0 - c, SILL_Y1 + c, SILL_Z0 - c, SILL_Z1 + c)
    # ballast block behind the rear lip
    wy = [SILL_Y0 + (SILL_Y1 - SILL_Y0) * (2 * i + 1) / (2.0 * N_WELLS) for i in range(N_WELLS)]
    zc = (BLOCK_Z0 + BLOCK_Z1) / 2.0
    bh = WELL_DEPTH + 1.0                              # block height above the plate (1 mm floor)
    block = box(-1.0, bh, SILL_Y0, SILL_Y1, BLOCK_Z0 - EPS, BLOCK_Z1)
    body = Manifold.batch_boolean([plate, lip, block], OpType.Add)

    cuts = []
    for y in wy:
        cuts.append(cyl_x(1.0, bh + 1, y, zc, WELL_D / 2.0))                        # coin well, 1 mm floor
        cuts.append(box(1.0, bh + 1, y - THUMB_W / 2, y + THUMB_W / 2, zc, BLOCK_Z1 + 1))   # thumb notch
    for y in TIE_Y:
        cuts.append(cyl_x(-t - 1, LIP_H + 1, y, TIE_HOLE_Z, TIE_HOLE_D / 2.0))      # under the sill hole
        zs0 = SILL_Z1 + 0.6
        cuts.append(box(-t - 1, LIP_H + 1, y - TIE_W / 2, y + TIE_W / 2, zs0, zs0 + TIE_SLOT_Z))          # slot behind the sill
        cuts.append(box(-0.5, LIP_H + 1, y - TIE_NOTCH / 2, y + TIE_NOTCH / 2, SILL_Z1, LIP_Z1 + EPS))   # rear lip notch
        cuts.append(box(-t - 1, -t + TIE_GROOVE_D, y - TIE_W / 2, y + TIE_W / 2, TIE_HOLE_Z, zs0 + TIE_SLOT_Z))  # underside groove
    return body - Manifold.batch_boolean(cuts, OpType.Add)


def to_print(m):
    """In-use -> print pose: plate bottom on the bed (x -> z), front edge toward -x, min at 0."""
    p = m.transform([[0, 0, -1, 0], [0, 1, 0, 0], [1, 0, 0, FOOT_T]])
    lo = p.bounding_box()[:3]
    return p.translate([-lo[0], -lo[1], -lo[2]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "print"))
    args = ap.parse_args()
    foot = to_print(build_foot())
    mesh = gen.to_trimesh(foot)
    name = "demo-door-foot-rev%d" % FOOT_REV
    for ext in ("stl", "3mf"):
        path = os.path.join(args.out, name + "." + ext)
        if os.path.exists(path):
            sys.exit("refusing to overwrite %s - bump FOOT_REV" % path)
        mesh.export(path)
        print("wrote", path)
    print("  %s: %.1f cm3, %.1f x %.1f x %.1f mm" % (name, foot.volume() / 1000, *mesh.extents))


if __name__ == "__main__":
    main()
