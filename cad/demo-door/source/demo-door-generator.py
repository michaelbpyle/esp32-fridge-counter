r"""Demo door: a miniature door in a door frame with a print-in-place hinge, for showing
the magnetic reed-switch door counter on a table.

Pure Python (system Python 3 with manifold3d, trimesh, numpy, matplotlib). Run from anywhere:

    python demo-door-generator.py               writes into ..\print (next to this source folder)
    python demo-door-generator.py --out DIR     writes into DIR (use a scratch folder to try things)

Writes  demo-door-rev<REV>.stl / .3mf   (frame and door on one plate, hinge assembled)
and refuses to overwrite an existing file: changed geometry means bump REV first.
Then run demo-door-check.py (numerical checks of the STL) and demo-door-render.py (previews).

Rev 2 (2026-11-14) mounts the owner's white surface-mount reed switch pair (L-shaped blocks,
measured with calipers) on locating pads: switch on the latch-side tunnel wall, magnet in a
shallow pocket on the back of the door. Rev 1 (recessed Gebildet switch, plus a plain
surface-switch variant) is kept unchanged in ..\shelved\rev1 with the script that made it.

HINGE CREDIT: the hinge is the pinless cone hinge of Nick Johnson's "Clamshell Parts Box"
(MakerWorld model 786443, licence CC BY-SA). Its working geometry is copied here - knuckles of
the two halves alternate along the axis and hold each other on 45 degree male/female cones with
a 0.25 mm axial offset (0.18 mm measured square to the cone face) - and scaled up for a larger
part. This remix is therefore CC BY-SA as well.

COORDINATES (the STL is in the print pose, millimetres)
    x  door height. In use x is UP: x = 0 is the underside of the sill (on the table).
    y  width. The hinge axis is the line y = 0, z = T/2. The frame is on the +y side; the door
       is printed swung open 180 degrees, lying on the -y side.
    z  depth. z = 0 is the bed AND the front face of the frame; the entry tunnel rises to
       z = DEPTH. The door lies on its BACK face, front face up.
Closing the door is a rotation of +180 degrees about the hinge axis: the door passes through
z < 0 (out in front of the frame) and ends flush in the opening, between z = 0 and z = T.
"""
import argparse
import os
import sys

sys.dont_write_bytecode = True          # no __pycache__ beside the scripts
import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, JoinType, Manifold, OpType, set_circular_segments

REV = 2

# ---- overall size (owner's numbers) -------------------------------------------------------
H_TOTAL = 152.4          # overall height, 6 inches
DEPTH = 50.8             # entry tunnel depth, 2 inches

# ---- frame --------------------------------------------------------------------------------
T = 12.6                 # thickness of the door and of the frame's front slab. The hinge axis
                         # is at T/2, so the door swings from flat-on-the-bed to flush-in-frame.
                         # (Set in rev 1 by a 9 mm recessed switch barrel; kept so the hinge,
                         # the frame and the rev 1 foot stay exactly as validated.)
SILL_H = 7.0             # sill (the base that stands on the table)
HEADER_H = 38.0          # sign board above the door; houses the reed switch barrel
PIL_W = 12.0             # width of the two pilasters (jamb fronts); the hinge axis is centred in one
WALL = 4.0               # tunnel wall thickness behind the front slab
EAR = 1.5                # header overhang beyond the pilasters, each side
CORNICE = 1.5            # extra overhang of the cornice strip and of the sill
CORNICE_H = 5.0
SILL_CH = 1.2            # the same on the sill (shallower, it is the threshold)
REVEAL_CH = 2.0          # 45 degree chamfer round the door opening (on the hinge side it is
                         # also the relief that lets the door's hinge edge swing past the jamb)

# ---- door ---------------------------------------------------------------------------------
DOOR_W = 50.0
GAP_HINGE = 0.6          # door edge to hinge jamb
GAP_LATCH = 0.7          # door edge to latch jamb
GAP_TOP = 0.6
GAP_BOTTOM = 0.8         # larger: in use the door drops by CONE_AXIAL_GAP onto its cones
SWEEP_CLR = 0.45         # clearance of the hollow in the door's hinge edge to the jamb corner
BED_CH = 0.6             # 45 degree first-layer chamfer (elephant foot) at every hinge gap
STOP_BEVEL = 3.0         # 45 degree bevel on the back of the door's latch edge ...
STOP_P = 3.4             # ... that lands on a 45 degree rib this far out from the latch jamb
STOP_CLR = 0.10          # bevel-to-rib distance when the door is exactly flush
PLANK_PITCH = 10.0       # vertical V grooves ("planks")
PLANK_GROOVE = 0.8
BATTEN_W = 9.0           # raised Z-brace battens
BATTEN_H = 1.0
KNOB_R = 5.0
KNOB_FROM_LATCH = 6.5

# ---- hinge (Nick Johnson's cone hinge, scaled) ---------------------------------------------
# Measured on his Standard box STL (demo-door-check.py --orig repeats the measurement):
# knuckle dia 3.0; cones at 45 degrees from r 1.25 down to r 0.25; male and female cone faces
# 0.25 apart along the axis = 0.177 square to the face, on the inner and the end joints alike;
# knuckle round to the hollow in the other half 0.196; no pin. Here the cones do all the work:
# the knuckles are plain blocks, so there is no round-in-hollow fit to get wrong.
N_DOOR_KNUCKLES = 3
KNUCKLE_L = 16.0         # length of each door knuckle; the frame's knuckles fill the rest
CONE_R_BASE = 4.0        # his 1.25 x 3.2
CONE_R_TIP = 1.0         # his 0.25 x 4
CONE_AXIAL_GAP = 0.25    # HIS VALUE, unscaled: male to female cone, measured along the axis
                         # (0.177 square to the cone face). Raise to 0.30-0.35 if a print fuses.
FLAT_GAP = 0.40          # between the flat end faces of neighbouring knuckles (never touch)
NOTCH_CLR = 0.6          # over the door's hinge arms where they pass through the hinge jamb
NOTCH_FLAT = 3.0         # flat (bridged) width at the top of each arm notch; the rest is 45 deg

# ---- surface-mount reed switch pair (rev 2) -------------------------------------------------
# The owner's white wired switch and its matching magnet: two identical L-shaped blocks, a thin
# flange (two screw holes, not used) along one long side and a taller body along the other;
# the switch's wire leaves one short end of the body, along its length.
# OWNER'S CALIPER READINGS, 2026-11-14. THEY INCLUDE THE FOAM TAPE ALREADY ON THE BOTTOM.
SW_L = 33.91             # length
SW_W = 14.27             # overall width, flange + body
SW_BODY_W = 7.88         # body width alone
SW_BODY_H = 9.21         # body height (base of the tape to the top of the body)
SW_FLANGE_T = 2.83       # flange thickness (with tape)
SW_FLANGE_W = SW_W - SW_BODY_W      # 6.39
PAD_CLR = 0.4            # clearance all round the measured footprint in the locating outlines
BODY_GAP = 3.0           # gap between the two bodies' facing faces with the door shut
SW_X1 = 104.0            # top end of both blocks (in-use height); leaves 10 mm under the roof
                         # for the switch's wire to bend toward the back
MAG_EDGE_IN = 4.2        # magnet body's outer edge this far in from the door's latch edge
                         # (keeps it on the flat, clear of the 3 mm stop bevel and the jamb)
MAG_POCKET_D = 0.6       # magnet pocket depth in the door back (that face is on the bed when
                         # printed, so the outline is a pocket; its ceiling is a short bridge)
MAG_MARK = 3.0           # notch in the pocket outline on the FLANGE side (an orientation mark)
SIDE_LIP_H = 1.5         # switch outline on the tunnel wall: low lips along both long sides ...
END_WALL_H = 7.0         # ... and taller walls at both ends; the top one has a gap for the wire
LIP_T = 1.2              # thickness of those lips and walls
TIE_SLOT_Z = (40.0, 44.5)           # zip-tie slots through the tunnel roof for the switch wire

# ---- sign ----------------------------------------------------------------------------------
SIGN_LINES = ["HOLLYGROVE", "COMMUNITY", "FRIDGE"]   # top line first; [] for no sign
SIGN_CAP_H = 5.4         # capital height
SIGN_PITCH = 8.4         # line spacing
SIGN_DEPTH = 0.4         # engraved into the bed face (two layers)
SIGN_FONT = "DejaVu Sans"    # ships with matplotlib

# ---- derived -------------------------------------------------------------------------------
AX_Z = T / 2.0
X_SILL = SILL_H                              # top of the sill
X_D0 = X_SILL + GAP_BOTTOM                   # door bottom edge
X_HEAD = H_TOTAL - HEADER_H                  # underside of the head (top of the opening)
X_D1 = X_HEAD - GAP_TOP                      # door top edge
Y_PIL0, Y_PIL1 = -PIL_W / 2.0, PIL_W / 2.0   # hinge pilaster
Y_DH = Y_PIL1 + GAP_HINGE                    # door hinge edge (closed)
Y_DL = Y_DH + DOOR_W                         # door latch edge (closed)
Y_LJ = Y_DL + GAP_LATCH                      # latch jamb inner face
Y_OUT1 = Y_LJ + PIL_W                        # latch pilaster outer face
# switch and magnet blocks (closed pose, in-use coordinates)
SW_X0 = SW_X1 - SW_L                         # bottom end of both blocks
MAG_Y1 = Y_DL - MAG_EDGE_IN                  # magnet body's outer (latch-side) edge
MAG_Z0 = T - MAG_POCKET_D                    # magnet base (pocket floor in the door back)
MAG_TOP = MAG_Z0 + SW_BODY_H                 # magnet body's top face, facing the switch
SW_Z0 = MAG_TOP + BODY_GAP                   # switch body's front face (toward the magnet)
STOP_X1 = SW_X0 - PAD_CLR - LIP_T - 2.0      # the stop rib ends below the switch and magnet
KNUCKLE_C = [X_D0 + (X_D1 - X_D0) * (2 * i + 1) / (2.0 * N_DOOR_KNUCKLES) for i in range(N_DOOR_KNUCKLES)]
# hollow in the door's hinge edge: clears the farthest point of the chamfered jamb corner
JAMB_R = max(np.hypot(Y_PIL1, AX_Z - REVEAL_CH), np.hypot(Y_PIL1 - REVEAL_CH, AX_Z))
COVE_R = JAMB_R + SWEEP_CLR
EPS = 0.01

set_circular_segments(96)


# ---- small solid helpers ---------------------------------------------------------------------
# Every solid below is built from exact corner coordinates (convex hulls), never by adding a
# size to an origin and never through a 2D clipping library. Two faces meant to lie on one
# plane then have bit-identical coordinates, and the booleans treat them as one plane. (Faces
# that differ in the 9th-15th decimal survive the booleans as zero-thickness skins and then
# collapse when STL rounds to 32-bit floats.)
def box(x0, x1, y0, y1, z0, z1):
    return Manifold.hull_points([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])


def _area(p):
    p = np.asarray(p, dtype=float)
    return 0.5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))


def _hull_prism(pts_a, pts_b, poly, length):
    m = Manifold.hull_points(pts_a + pts_b)
    assert abs(m.volume() - _area(poly) * abs(length)) < 1e-6 * max(1.0, m.volume()), "prism profile is not convex"
    return m


def prism_x(yz, x0, x1):
    """Convex polygon given in (y, z), extruded along x."""
    return _hull_prism([(x0, y, z) for y, z in yz], [(x1, y, z) for y, z in yz], yz, x1 - x0)


def prism_y(xz, y0, y1):
    """Convex polygon given in (x, z), extruded along y."""
    return _hull_prism([(x, y0, z) for x, z in xz], [(x, y1, z) for x, z in xz], xz, y1 - y0)


def prism_z(xy, z0, z1):
    """Convex polygon given in (x, y), extruded along z."""
    return _hull_prism([(x, y, z0) for x, y in xy], [(x, y, z1) for x, y in xy], xy, z1 - z0)


def text_prism_z(polys_xy, z0, z1):
    """Any polygons in (x, y) (holes by even-odd rule), extruded along z. Only for the sign,
    whose outlines share no plane with anything else."""
    cs = CrossSection([np.asarray(p, dtype=float) for p in polys_xy], FillRule.EvenOdd)
    cs = cs.offset(0.02, JoinType.Miter)       # font outlines that touch at a point become one region
    return cs.extrude(z1 - z0).translate([0, 0, z0])


def cyl_x(x0, x1, y, z, r0, r1=None):
    """Cylinder or cone along x: radius r0 at x0, r1 at x1."""
    r1 = r0 if r1 is None else r1
    return Manifold.cylinder(x1 - x0, r0, r1).transform([[0, 0, 1, x0], [1, 0, 0, y], [0, 1, 0, z]])


def cyl_y(y0, y1, x, z, r):
    return Manifold.cylinder(y1 - y0, r, r).transform([[0, 1, 0, x], [0, 0, 1, y0], [1, 0, 0, z]])


def arc(cy, cz, r, a0, a1, n=48):
    a = np.radians(np.linspace(a0, a1, n))
    return [(cy + r * np.cos(t), cz + r * np.sin(t)) for t in a]


def union(parts):
    return Manifold.batch_boolean(parts, OpType.Add)


def switch_block():
    """The reed switch at its measured size, fitted (frame coordinates): base taped to the
    latch-side tunnel wall, body toward the door, wire end at the top. For checks and renders."""
    body = box(SW_X0, SW_X1, Y_LJ - SW_BODY_H, Y_LJ, SW_Z0, SW_Z0 + SW_BODY_W)
    flange = box(SW_X0, SW_X1, Y_LJ - SW_FLANGE_T, Y_LJ, SW_Z0 + SW_BODY_W, SW_Z0 + SW_W)
    return body + flange


def magnet_block():
    """The magnet at its measured size, fitted in its pocket (door PRINT-POSE coordinates, so it
    swings with the door): base on the pocket floor, body on the latch side."""
    # closed pose (y, z) -> print pose (-y, T - z)
    zb, zt = T - MAG_Z0, T - MAG_TOP
    zf = T - (MAG_Z0 + SW_FLANGE_T)
    body = box(SW_X0, SW_X1, -MAG_Y1, -MAG_Y1 + SW_BODY_W, zt, zb)
    flange = box(SW_X0, SW_X1, -MAG_Y1 + SW_BODY_W, -MAG_Y1 + SW_W, zf, zb)
    return body + flange


def bed_v_x(yc, half_gap, x0, x1):
    """First-layer relief along a gap that runs in x at y = yc."""
    w = half_gap + BED_CH
    return prism_x([(yc - w, -EPS), (yc + w, -EPS), (yc + half_gap, BED_CH), (yc - half_gap, BED_CH)], x0, x1)


def bed_v_y(xc, half_gap, y0, y1):
    """First-layer relief along a gap that runs in y at x = xc."""
    w = half_gap + BED_CH
    return prism_y([(xc - w, -EPS), (xc + w, -EPS), (xc + half_gap, BED_CH), (xc - half_gap, BED_CH)], y0, y1)


def knuckle_gaps():
    """x of the middle of every flat gap between a frame knuckle and a door knuckle,
    with the direction (+1/-1) pointing from the frame face into the door knuckle."""
    out = []
    for c in KNUCKLE_C:
        out.append((c - KNUCKLE_L / 2.0 - FLAT_GAP / 2.0, +1))
        out.append((c + KNUCKLE_L / 2.0 + FLAT_GAP / 2.0, -1))
    return out


def sign_polys():
    """Sign text as polygons in (x, y): reads left to right along +y, up along +x, when the
    frame is seen from the front (from below the bed)."""
    if not SIGN_LINES:
        return []
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    fp = FontProperties(family=SIGN_FONT, weight="bold")
    cap = TextPath((0, 0), "H", size=10, prop=fp).get_extents().height
    y_mid = (Y_PIL0 + Y_OUT1) / 2.0
    width_max = (Y_OUT1 - Y_PIL0) - 4.0
    x_hi = H_TOTAL - CORNICE_H - 2.2 - SIGN_CAP_H          # baseline of the top line
    polys = []
    for i, line in enumerate(SIGN_LINES):
        tp = TextPath((0, 0), line, size=10, prop=fp)
        ext = tp.get_extents()
        s = min(SIGN_CAP_H / cap, width_max / ext.width)
        u0 = y_mid - s * (ext.x0 + ext.x1) / 2.0
        base = x_hi - i * SIGN_PITCH
        for p in tp.to_polygons():
            if len(p) >= 3:
                polys.append(np.c_[base + s * p[:, 1], u0 + s * p[:, 0]])
    return polys


# ---- frame -------------------------------------------------------------------------------------
def build_frame():
    y_in0 = Y_PIL1 - WALL                  # hinge-side tunnel wall, outer face
    y_in1 = Y_LJ + WALL                    # latch-side tunnel wall, outer face
    ya, yb = Y_PIL0 - EAR, Y_OUT1 + EAR    # header
    yc, yd = ya - CORNICE, yb + CORNICE    # cornice and sill
    xt = H_TOTAL - CORNICE_H
    header = union([box(X_HEAD, H_TOTAL, ya, yb, 0, T),
                    prism_z([(xt - CORNICE, ya), (xt - CORNICE, yb), (xt, yd), (H_TOTAL, yd), (H_TOTAL, yc), (xt, yc)], 0, T)])
    parts = [
        box(0, SILL_H, yc, yd, 0, DEPTH),                               # sill / base
        box(SILL_H - EPS, X_HEAD + WALL, y_in0, Y_PIL1, 0, DEPTH),      # hinge-side wall
        box(SILL_H - EPS, X_HEAD + WALL, Y_LJ, y_in1, 0, DEPTH),        # latch-side wall
        box(X_HEAD, X_HEAD + WALL, y_in0, y_in1, 0, DEPTH),             # tunnel roof
        box(SILL_H - EPS, X_HEAD + EPS, Y_PIL0, Y_PIL1, 0, T),          # hinge pilaster
        box(SILL_H - EPS, X_HEAD + EPS, Y_LJ, Y_OUT1, 0, T),            # latch pilaster
        header,
    ]
    # door stop: a 45 degree rib on the latch jamb that meets the bevel on the door's back edge.
    # Rev 2: it stops below the magnet, which passes where the rib's top used to be.
    z0 = T - STOP_BEVEL - GAP_LATCH + STOP_CLR * np.sqrt(2)
    parts.append(prism_x([(Y_LJ + 0.5, z0 - 0.5), (Y_LJ - STOP_P, z0 + STOP_P), (Y_LJ - STOP_P, z0 + STOP_P + 2.5),
                          (Y_LJ + 0.5, z0 + STOP_P + 2.5)], X_D0 + 2.0, STOP_X1))
    # switch outline on the latch-side tunnel wall: low lips along the long sides, taller walls
    # at the ends. In the print pose these are fins on a vertical wall (short ledges only).
    c, t = PAD_CLR, LIP_T
    za, zb = SW_Z0 - c, SW_Z0 + SW_W + c                 # inside of the outline
    xa, xb = SW_X0 - c, SW_X1 + c
    for z_lo, z_hi in ((za - t, za), (zb, zb + t)):
        parts.append(box(xa - t, xb + t, Y_LJ - SIDE_LIP_H, Y_LJ + EPS, z_lo, z_hi))
    # end walls: as low as the side lip at their front end, rising at 45 degrees to full height
    # (in the print pose the front end is underneath, so this keeps them self-supporting)
    rise = END_WALL_H - SIDE_LIP_H
    prof = [(Y_LJ + EPS, za - t), (Y_LJ - SIDE_LIP_H, za - t), (Y_LJ - END_WALL_H, za - t + rise),
            (Y_LJ - END_WALL_H, zb + t), (Y_LJ + EPS, zb + t)]
    # Both end walls have a wire gap on the BODY (front) half only: the switch fits with its body
    # toward the door and its wire out of whichever end the part's handedness puts it; turned
    # round (body toward the back) its wire end meets a solid wall.
    for x0, x1 in ((xa - t, xa), (xb, xb + t)):
        wall = prism_x(prof, x0, x1)
        wall -= box(x0 - 1, x1 + 1, Y_LJ - END_WALL_H - 1, Y_LJ - SIDE_LIP_H, za, SW_Z0 + SW_BODY_W + c)
        parts.append(wall)
    f = union(parts)

    cuts = []
    # reveal chamfer round the opening (front face = bed): one frustum, mitred in the corners
    c = REVEAL_CH
    k = (c + EPS) / c
    lo = [(X_SILL - SILL_CH * k, Y_PIL1 - c * k, -EPS), (X_SILL - SILL_CH * k, Y_LJ + c * k, -EPS),
          (X_HEAD + c * k, Y_PIL1 - c * k, -EPS), (X_HEAD + c * k, Y_LJ + c * k, -EPS)]
    hi = [(X_SILL, Y_PIL1, c), (X_SILL, Y_LJ, c), (X_HEAD, Y_PIL1, c), (X_HEAD, Y_LJ, c)]
    cuts.append(Manifold.hull_points(lo + hi))
    # notches through the hinge jamb for the door's hinge arms, each with a 45 degree roof
    zr = T + NOTCH_CLR
    for kc in KNUCKLE_C:
        h = KNUCKLE_L / 2.0 + FLAT_GAP
        rise = h - NOTCH_FLAT / 2.0
        cuts.append(prism_y([(kc - h, -1), (kc + h, -1), (kc + h, zr), (kc + NOTCH_FLAT / 2.0, zr + rise),
                             (kc - NOTCH_FLAT / 2.0, zr + rise), (kc - h, zr)], Y_PIL0 - 1, Y_PIL1 + 1))
    # first-layer relief at every knuckle gap and along the print-pose door edge
    for xg, _ in knuckle_gaps():
        cuts.append(bed_v_y(xg, FLAT_GAP / 2.0, Y_PIL0 - 1, Y_PIL1 + 1))
    # outer front edges of both pilasters: the same 45 degree chamfer as the reveal. On the hinge
    # side it is what lets the door's edge leave the print pose (the mirror image of the reveal).
    cuts.append(prism_x([(Y_PIL0 - 1.0, -EPS), (Y_PIL0 + c * k, -EPS), (Y_PIL0, c), (Y_PIL0 - 1.0, c)], X_SILL, X_HEAD))
    cuts.append(prism_x([(Y_OUT1 + 1.0, -EPS), (Y_OUT1 - c * k, -EPS), (Y_OUT1, c), (Y_OUT1 + 1.0, c)], X_SILL, X_HEAD))
    cuts.append(bed_v_y(X_SILL + GAP_BOTTOM / 2.0, GAP_BOTTOM / 2.0, yc - 1, Y_PIL0))
    cuts.append(bed_v_y(X_HEAD - GAP_TOP / 2.0, GAP_TOP / 2.0, yc - 1, Y_PIL0))
    # two screw holes through the sill, to fasten the stand to a board
    for y in (Y_PIL1 + 12.0, Y_LJ - 12.0):
        cuts.append(cyl_x(-1, SILL_H + 1, y, 33.0, 2.25))
    # sign
    sp = sign_polys()
    if sp:
        cuts.append(text_prism_z(sp, -EPS, SIGN_DEPTH))

    # zip-tie slots through the tunnel roof, near the latch wall, for the switch wire: it runs
    # up from the switch's top end into the roof corner and back along the roof to these
    for y in (Y_LJ - 9.5, Y_LJ - 3.5):
        cuts.append(box(X_HEAD - 1, X_HEAD + WALL + 1, y, y + 1.8, TIE_SLOT_Z[0], TIE_SLOT_Z[1]))
    # ... and a second pair low in the latch-side wall, in case the wire comes out of the
    # switch's bottom end: it then runs down the wall to these and out the back
    for x in (SW_X0 - 40.0, SW_X0 - 34.0):
        cuts.append(box(x, x + 1.8, Y_LJ - 1, y_in1 + 1, TIE_SLOT_Z[0], TIE_SLOT_Z[1]))
    f -= union(cuts)
    # male cones on the frame knuckle faces (added last: they stand in the arm notches)
    cones = []
    for xg, d in knuckle_gaps():
        xf = xg - d * FLAT_GAP / 2.0                                   # the frame's face
        a, b = xf - d * 0.3, xf + d * (CONE_R_BASE - CONE_R_TIP)
        ra, rb = CONE_R_BASE + 0.3, CONE_R_TIP
        cones.append(cyl_x(a, b, 0, AX_Z, ra, rb) if d > 0 else cyl_x(b, a, 0, AX_Z, rb, ra))
    return union([f] + cones)


# ---- door (built in the print pose: mirrored to -y, back face on the bed) ------------------------
def build_door():
    yh, yl = -Y_DH, -Y_DL                   # hinge edge, latch edge
    d = box(X_D0, X_D1, yl, yh, 0, T)
    cuts = []
    # hollow along the hinge edge so the edge can swing past the jamb (a rule joint)
    cuts.append(cyl_x(X_D0 - 1, X_D1 + 1, 0, AX_Z, COVE_R))
    # 45 degree stop bevel on the back of the latch edge, first-layer reliefs on the other edges
    cuts.append(prism_x([(yl - EPS, -EPS), (yl + STOP_BEVEL, -EPS), (yl - EPS, STOP_BEVEL + EPS)], X_D0 - 1, X_D1 + 1))
    cuts.append(prism_x([(yh + EPS, -EPS), (yh - BED_CH, -EPS), (yh + EPS, BED_CH + EPS)], X_D0 - 1, X_D1 + 1))
    cuts.append(prism_y([(X_D0 - EPS, -EPS), (X_D0 + BED_CH, -EPS), (X_D0 - EPS, BED_CH + EPS)], yl - 1, yh + 1))
    cuts.append(prism_y([(X_D1 + EPS, -EPS), (X_D1 - BED_CH, -EPS), (X_D1 + EPS, BED_CH + EPS)], yl - 1, yh + 1))
    # planks
    g = PLANK_GROOVE
    k = 1
    while k * PLANK_PITCH < DOOR_W - 1:
        y = yh - k * PLANK_PITCH
        cuts.append(prism_x([(y - g, T + EPS), (y + g, T + EPS), (y, T - g)], X_D0 - 1, X_D1 + 1))
        k += 1
    d -= union(cuts)

    adds = []
    # Z-brace battens on the front
    m = 3.0
    b0, b1 = X_D0 + 11.0, X_D1 - 11.0 - BATTEN_W          # lower edges of the two cross battens
    for b in (b0, b1):
        adds.append(box(b, b + BATTEN_W, yl + m, yh - m, T - PLANK_GROOVE - 0.1, T + BATTEN_H))
    # diagonal: from the bottom batten at the hinge side up to the top batten at the latch side
    dx = BATTEN_W * 0.75
    adds.append(prism_z([(b0 + BATTEN_W - 0.5, yh - m), (b0 + BATTEN_W - 0.5, yh - m - dx * 1.6),
                         (b1 + 0.5, yl + m), (b1 + 0.5, yl + m + dx * 1.6)], T - PLANK_GROOVE - 0.1, T + BATTEN_H))
    # knob: 45 degree flare, so it prints upright without support
    ky, kx, r = yl + KNOB_FROM_LATCH, (X_D0 + X_D1) / 2.0, KNOB_R
    prof = [(0, -0.9), (r - 2.0, -0.9), (r - 2.0, 2.0), (r, 4.0), (r, 6.5), (r - 1.5, 8.0), (0, 8.0)]
    adds.append(Manifold.revolve(CrossSection([np.asarray(prof, dtype=float)]), 96).translate([kx, ky, T]))
    # hinge arms and knuckles: a full-thickness arm from the door edge to the axis, ending in
    # a round nose whose underside is filled in at 45 degrees down to the bed
    r = AX_Z
    nose = [(yh - 2.5, 0.0), (r * np.sqrt(2) - AX_Z, 0.0)] + arc(0, AX_Z, r, -45, 90) + [(yh - 2.5, T)]
    for kc in KNUCKLE_C:
        adds.append(prism_x(nose, kc - KNUCKLE_L / 2.0, kc + KNUCKLE_L / 2.0))
    d = union([d] + adds)

    cuts = []
    # female cones: the male surface moved CONE_AXIAL_GAP along the axis
    for xg, s in knuckle_gaps():
        xf = xg + s * FLAT_GAP / 2.0                                   # the door knuckle's face
        r_face = CONE_R_BASE - (FLAT_GAP - CONE_AXIAL_GAP)
        depth = r_face - CONE_R_TIP
        a, b = xf - s * 0.2, xf + s * depth
        ra, rb = r_face + 0.2, CONE_R_TIP
        cuts.append(cyl_x(a, b, 0, AX_Z, ra, rb) if s > 0 else cyl_x(b, a, 0, AX_Z, rb, ra))
        cuts.append(bed_v_y(xg, FLAT_GAP / 2.0, yh, AX_Z + 1))
    # magnet pocket in the back face (on the bed): the measured footprint + PAD_CLR all round,
    # with a small notch on the FLANGE side (toward the hinge) as an orientation mark: the
    # magnet's body goes on the other side, toward the latch edge
    c = PAD_CLR
    ya, yb = -MAG_Y1 - c, -MAG_Y1 + SW_W + c
    cuts.append(box(SW_X0 - c, SW_X1 + c, ya, yb, -1.0, MAG_POCKET_D))
    xm = (SW_X0 + SW_X1) / 2.0
    cuts.append(box(xm - MAG_MARK / 2, xm + MAG_MARK / 2, yb - EPS, yb + MAG_MARK / 2, -1.0, MAG_POCKET_D))
    return d - union(cuts)


# ---- output ----------------------------------------------------------------------------------------
def to_trimesh(m):
    """Manifold -> trimesh, cleaned for STL. STL stores 32-bit floats, so faces that differ
    only in the 14th decimal (two cutters meeting on the same plane) collapse onto each other
    when the file is written. Snap to 32-bit here, drop what collapsed, and insist that what
    is left is still one closed solid of the same volume."""
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32).astype(np.float64)
    f = np.asarray(mesh.tri_verts).astype(np.int64)
    v, inv = np.unique(v, axis=0, return_inverse=True)
    f = inv.reshape(-1)[f]
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    t = trimesh.Trimesh(vertices=v, faces=f, process=False)
    parts = [p for p in t.split(only_watertight=False) if abs(p.volume) > 1.0]
    assert len(parts) == 1, "expected one solid, got %d" % len(parts)
    t = parts[0]
    t = trimesh.Trimesh(vertices=t.vertices, faces=t.faces, process=False)
    t.remove_unreferenced_vertices()
    assert t.is_watertight and t.is_winding_consistent, "mesh is not closed after 32-bit snapping"
    assert abs(t.volume - m.volume()) < 0.5, "volume changed in clean-up: %.3f vs %.3f" % (t.volume, m.volume())
    return t


def build():
    """Frame and door as manifolds, in generator coordinates (hinge axis on y = 0)."""
    return build_frame(), build_door()


PRINT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "print")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=PRINT_DIR)
    args = ap.parse_args()
    for tag in ("",):
        frame, door = build()
        lo = np.minimum(frame.bounding_box()[:3], door.bounding_box()[:3])
        meshes = [to_trimesh(p.translate([-lo[0], -lo[1], -lo[2]])) for p in (frame, door)]
        plate = trimesh.util.concatenate(meshes)
        name = "demo-door-rev%d%s" % (REV, tag)
        for ext in ("stl", "3mf"):
            path = os.path.join(args.out, name + "." + ext)
            if os.path.exists(path):
                sys.exit("refusing to overwrite %s - bump REV" % path)
            plate.export(path)
            print("wrote", path)
        print("  %s: frame %.1f cm3, door %.1f cm3, plate %.1f x %.1f x %.1f mm, hinge axis at y %.2f z %.2f"
              % (name, frame.volume() / 1000, door.volume() / 1000, *plate.extents, -lo[1], AX_Z))


if __name__ == "__main__":
    main()
