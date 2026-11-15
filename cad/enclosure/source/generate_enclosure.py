#!/usr/bin/env python3
"""
Hollygrove Community Fridge - door counter node: parametric enclosure generator.

Produces, for each electronics "variant" (carrier board + dev board):

  case-base      printable bench / sheltered-use case, lower half
  case-lid       its lid (screws into the base)
  toe-clamp      small PCB edge clamp (print 4 per case, 4 per sled)
  sled-1554h     internal carrier plate for a Hammond 1554H / 1554T IP66 box

Pure Python: manifold3d (solid modelling), trimesh (export / checks), numpy,
matplotlib (text outlines only), Pillow (preview PNGs).

Usage:
  python generate_enclosure.py                 # build every variant into the folder above source/
  python generate_enclosure.py --variant a     # one variant
  python generate_enclosure.py --outdir X      # write the whole layout under X instead
  python generate_enclosure.py --no-render     # skip the PNG previews

Output layout under the output root (default: the folder that holds source/):
  print/bench-case-<folder>/       case base, case lid, toe clamp (STL + 3MF)
  print/weatherproof-box-sled/     the junction-box sleds (both variants)
  pictures/bench-case-<folder>/    case previews
  pictures/weatherproof-box-sled/  sled previews
  checks/validation-rev<REV>.json
<folder> is the "folder" entry of the variant (devkitc, freenove).

Files are stamped with REV (for example case-base-fnk0091-rev1.stl). The script
REFUSES to overwrite an existing file: bump REV when the geometry changes.

All dimensions in millimetres. Coordinate frame of the case:
  X  across the carrier board (its screw terminals are on the -X and +X sides)
  Y  along the carrier board; -Y is the USB / cable end ("down" when wall mounted)
  Z  up from the print bed; origin XY = centre of the carrier board
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import manifold3d as m3
from manifold3d import Manifold, CrossSection

REV = 1                 # case and the two dev-board sleds (do not change)
REV_WALTER = 1          # Walter sled: a separate part with its own revision count

# --------------------------------------------------------------------------
# 1. PARAMETERS YOU ARE EXPECTED TO EDIT
# --------------------------------------------------------------------------

# Fastening: "insert" = M3 brass heat-set inserts (5.7 mm long, 4.6 mm OD,
# pressed into a 4.0 mm hole with a soldering iron). "selftap" = M3 screws cut
# their own thread in a 2.5 mm printed hole (fine for a few open/close cycles).
FASTENER = "insert"
FASTENER_HOLE_D = {"insert": 4.0, "selftap": 2.5}
SCREW_CLEAR_D = 3.4            # clearance hole for an M3 screw

# Carrier boards (the screw-terminal breakout the dev board plugs into).
#   w, l      overall outline X, Y
#   holes     mounting-hole centres relative to the board centre
#   verified  which numbers come from a vendor drawing and which are assumed
CARRIERS = {
    # Freenove "Breakout Board for ESP32 / ESP32-S3" FNK0091 (PCB CB9101).
    # Outline 87 x 75 mm is printed on the vendor's product image; the 87.2 x
    # 75.2 and the hole pattern were scaled from the vendor board drawing
    # CB9101.png using its 2.54 mm header pitch as the ruler (9.949 px/mm).
    "fnk0091": dict(
        label="Freenove FNK0091 breakout (ESP32 / ESP32-S3, 2 x 20 socket)",
        w=87.2, l=75.2, pcb_t=1.6,
        holes=[(-40.55, -34.5), (40.55, -34.5), (-40.55, 34.5), (40.55, 34.5)],
        hole_d=3.0,
        top_h=11.5,       # tallest part above the PCB (DC jack / headers)
        bottom_h=3.0,     # solder joints below the PCB
        socket_h=8.5,     # female socket height above the PCB
        holes_verified="scaled from vendor drawing, +/-0.5 mm",
    ),
    # Freenove "Universal Breakout Board" FNK0101. Outline 87 x 83 mm is from
    # the vendor's product image. Hole positions are NOT documented: assumed
    # to sit 3.0 mm in from each edge like the FNK0091.
    "fnk0101": dict(
        label="Freenove FNK0101 universal breakout (0.6-1.0 in wide, <= 24 pins)",
        w=87.0, l=83.0, pcb_t=1.6,
        holes=[(-40.5, -38.5), (40.5, -38.5), (-40.5, 38.5), (40.5, 38.5)],
        hole_d=3.0,
        top_h=11.5, bottom_h=3.0, socket_h=8.5,
        holes_verified="ASSUMED (3.0 mm inset), measure before using the pilot holes",
    ),
}

# Dev boards. Positions are relative to the board: x from the centreline,
# y measured from the USB-end edge of the PCB.
BOARDS = {
    # Freenove ESP32-S3 WROOM and "WROOM Lite" (FNK0085 / FNK0099): same outline.
    # Scaled from the vendor pinout drawing with the 2.54 mm pin pitch.
    "freenove_s3": dict(
        label="Freenove ESP32-S3 WROOM / WROOM Lite (2 x 20 pins)",
        w=28.1, l=50.9, pcb_t=1.6, pins_per_side=20, row_spacing=25.4,
        ant_overhang=6.3,
        usb_x=[-5.1, 5.1],
        window=dict(y=12.5, w=31.0, h=16.0),      # buttons + LEDs strip
        top_h=3.4,
    ),
    # Generic "wide" ESP32-S3-DevKitC-1 clone with two USB-C (AYWHP and many
    # others, VCC-GND YD-ESP32-S3 layout). 57.15 x 27.94 mm and 25.4 mm row
    # spacing are user-measured values reported online, not a vendor drawing.
    # USB and button positions are ASSUMED.
    "devkitc_clone": dict(
        label="ESP32-S3-DevKitC-1 style clone, dual USB-C (2 x 22 pins)",
        w=27.94, l=57.15, pcb_t=1.6, pins_per_side=22, row_spacing=25.4,
        ant_overhang=6.0,
        usb_x=[-6.25, 6.25],
        window=dict(y=13.0, w=30.0, h=22.0),
        top_h=3.4,
    ),
    # DPTechnics Walter (55 x 24.8 mm, one USB-C). Fits the FNK0101 carrier.
    "walter": dict(
        label="DPTechnics Walter LTE-M (55 x 24.8 mm)",
        w=24.8, l=55.0, pcb_t=1.6, pins_per_side=14, row_spacing=22.86,
        ant_overhang=0.0,
        usb_x=[0.0],
        window=dict(y=12.0, w=26.0, h=20.0),
        top_h=4.0,
    ),
}

# Variants = which board sits on which carrier.
#   usb_edge  distance from the carrier's -Y edge to the dev board's USB-end edge
VARIANTS = {
    "a": dict(tag="fnk0091", folder="freenove", carrier="fnk0091", board="freenove_s3", usb_edge=16.4,
              usb_edge_note="scaled from vendor drawings"),
    "b": dict(tag="fnk0101", folder="devkitc", carrier="fnk0101", board="devkitc_clone", usb_edge=12.0,
              usb_edge_note="ASSUMED (board can sit anywhere along the 24-pin socket)"),
    # Example for later: Walter on the universal carrier.
    # "c": dict(tag="fnk0101-walter", carrier="fnk0101", board="walter", usb_edge=12.0,
    #           usb_edge_note="ASSUMED"),
}

# --------------------------------------------------------------------------
# 2. DESIGN CONSTANTS (change with care)
# --------------------------------------------------------------------------
WALL = 2.4              # case side walls (6 perimeters of a 0.4 mm nozzle)
FLOOR = 2.4
LID_T = 3.0
R_OUT = 8.0             # outer vertical corner radius
CHAMFER_BOTTOM = 0.6
CHAMFER_LID = 1.0

PCB_CLR = 0.75          # gap between the carrier outline and its corner fences
PAD = 7.0               # corner support pad size
PAD_H = 5.0             # carrier underside above the floor / sled
FENCE_T = 1.6
SIDE_CH = 13.0          # wiring channel beside each terminal-block row
MARGIN_USB = 12.0       # floor between the carrier and the cable (-Y) wall
ACC_BAY = 30.0          # accessory bay beyond the antenna (+Y) end
CLEAR_ABOVE = 24.0      # free height above the carrier PCB top face
HEADER_SPACER = 2.5     # plastic spacer of the dev board's pin headers
USB_BODY_H = 3.2        # USB-C receptacle height

LIP_T = 1.6             # lid locating lip
LIP_H = 3.0
LIP_CLR = 0.25          # lip to wall, per side
BOSS_R = 5.0            # lid screw boss radius
BOSS_INSET = 4.2        # boss centre from the inner wall faces
BOSS_HOLE_DEPTH = 7.5

USB_BAY_W = 30.0        # width of the USB opening in the -Y wall
USB_BAY_HALF_H = 5.5    # opening extends this far below the connector centre
TONGUE_H = 4.5          # lid tongue that closes the top of the USB opening
TONGUE_CLR = 0.25

CLAMP_X = 32.0          # toe-clamp bosses at x = +/-CLAMP_X on the +/-Y edges
CLAMP_BOSS_R = 4.5
CLAMP_BOSS_OFFSET = 5.5  # boss centre outside the fence line
CLAMP_L, CLAMP_W, CLAMP_T = 13.5, 9.0, 3.0
CLAMP_HOLE_FROM_END = 4.5

ANCHOR_L = 5.0          # zip-tie anchor: length along X
ANCHOR_BASE = 13.0      # footprint along Y
ANCHOR_H = 5.0
ANCHOR_TOP = 3.0

ACC_PAD_H = 3.0         # accessory pad with a grid of pilot holes
ACC_PITCH = 5.08
ACC_HOLE_D = 2.0        # for M2 / M2.3 self-tapping screws

EAR_L, EAR_W, EAR_T = 15.0, 22.0, 3.0
EAR_Y = -15.0
ROOT = 1.5              # how far ears and the pocket are buried in the case wall. Must
                        # exceed CHAMFER_BOTTOM so no two solids meet along a bare line.
KEY_BIG_D, KEY_SLOT_D, KEY_TRAVEL = 8.5, 4.5, 6.5

PK_IN_X, PK_IN_Y = 12.0, 18.0   # BMP280 pocket inside size
PK_WALL = 1.6
PK_SLIT = 1.6
PK_NOTCH_W, PK_NOTCH_D = 4.5, 4.5

# Cable exits in the -Y wall: (label, cable diameter, how many side by side).
EXITS_LEFT = [("DOOR", 4.0, 1), ("I2C", 5.0, 1), ("1W", 4.2, 1)]
EXITS_RIGHT = [("PWR", 5.3, 1), ("LOAD", 4.0, 2), ("LOAD", 4.0, 2)]
EXIT_START_X = 46.5     # first slot edge, measured from the centreline
EXIT_TOOTH = 3.0        # plastic between slots
EXIT_SLACK = 0.2        # slot is this much wider than the cable
EXIT_SQUEEZE = 0.4      # slot is this much shallower: the lid pinches the jacket

TEXT_DEPTH = 0.6
TITLE = [("Hollygrove", 7.0), ("Community Fridge", 7.0), ("door counter", 5.5)]
LABEL_CAP = 4.5

BED = 256.0             # Bambu Lab P1S build volume, each axis

# Hammond 1554H2GY / 1554T2GY (same footprint, 60 or 90 mm deep). Numbers from
# Hammond drawings 1554H (REV 28.02.2020) and "1554H PANEL".
BOX = dict(
    name="Hammond 1554H2GY (180 x 120 x 60 mm polycarbonate, IP66/IP68, UL 508A)",
    inside_l=172.91, inside_w=108.91, inside_h=54.5,
    panel_l=167.13, panel_w=106.68, notch_x=8.33, notch_y=19.38, notch_r=8.33,
    m3_x=132.0, m3_y=84.0,         # four M3 brass inserts
    side_x=160.0,                  # two bosses for #6 self-tapping screws
    boss_h=6.0,                    # insert bosses above the box floor
)
SLED_T = 3.0
SLED_CLR = 0.5

SEG = 64
MESH_TOL = 0.002        # mm; clean-up tolerance applied to every finished solid
m3.set_circular_segments(SEG)

# --------------------------------------------------------------------------
# 3. Small solid-modelling helpers
# --------------------------------------------------------------------------


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(x, y, r, z0, z1, segs=0):
    return Manifold.cylinder(z1 - z0, r, r, segs).translate([x, y, z0])


def union(parts):
    parts = [p for p in parts if p is not None]
    return Manifold.batch_boolean(parts, m3.OpType.Add) if parts else Manifold()


def rrect(x0, x1, y0, y1, r):
    """Rounded rectangle cross-section."""
    r = min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3)
    core = CrossSection.square([x1 - x0 - 2 * r, y1 - y0 - 2 * r]).translate([x0 + r, y0 + r])
    return grow(core, r)


def grow(cs, delta, segs=SEG * 2):
    """Offset an outline (round corners) and clean up near-duplicate points."""
    return cs.offset(delta, m3.JoinType.Round, 2.0, segs).simplify(2e-4)


def extrude(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def extrude_xz(cs, y0, y1):
    """Extrude a cross-section drawn in the X-Z plane along +Y."""
    return Manifold.extrude(cs, y1 - y0).transform([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0]])


def extrude_yz(cs, x0, x1):
    """Extrude a cross-section drawn in the Y-Z plane along +X."""
    return Manifold.extrude(cs, x1 - x0).transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])


def finish(man):
    """Collapse edges shorter than 2 microns so that no two vertices land on
    the same spot when the mesh is written as 32-bit STL."""
    return man.simplify(MESH_TOL)


def poly(points):
    return CrossSection([np.asarray(points, dtype=float)])


def chamfered_slab(cs, z0, z1, c, at_top):
    """Extrusion of a CONVEX outline with a chamfer on its bottom or top edge."""
    small = Manifold.extrude(grow(cs, -c), 0.001)
    if at_top:
        body = extrude(cs, z0, z1 - c)
        cap = small.translate([0, 0, z1 - 0.001])
    else:
        body = extrude(cs, z0 + c, z1)
        cap = small.translate([0, 0, z0])
    return Manifold.batch_hull([body, cap])


_FONT = None


def text_cs(s, cap_h):
    """Outline of a text string (DejaVu Sans Bold), cap height cap_h, centred."""
    global _FONT
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    if _FONT is None:
        _FONT = FontProperties(family="DejaVu Sans", weight="bold")
    k = cap_h / 0.729                      # DejaVu cap height is 0.729 em
    tp = TextPath((0, 0), s, size=1.0, prop=_FONT)
    contours = [np.asarray(p[:-1]) * k for p in tp.to_polygons(closed_only=True) if len(p) > 3]
    cs = CrossSection(contours, m3.FillRule.EvenOdd)
    x0, y0, x1, y1 = cs.bounds()
    return cs.translate([-(x0 + x1) / 2, -(y0 + y1) / 2])


def tent_anchor(x, y, z):
    """Zip-tie anchor: a little tent with a tunnel, printable without support.
    The tie passes through the tunnel along X; the cable lies on top along Y."""
    hb, ht, h = ANCHOR_BASE / 2, ANCHOR_TOP / 2, ANCHOR_H
    outer = poly([(-hb, 0), (hb, 0), (ht, h), (-ht, h)])
    tunnel = poly([(-3.2, -0.01), (3.2, -0.01), (0.0, 3.2)])   # 45 degree roof
    body = extrude_yz(outer - tunnel, -ANCHOR_L / 2, ANCHOR_L / 2)
    return body.translate([x, y, z])


# --------------------------------------------------------------------------
# 4. Geometry shared by the case and the junction-box sled
# --------------------------------------------------------------------------


def carrier_bay(car, zb):
    """Corner pads, fences and clamp bosses for a carrier board whose centre is
    at the XY origin, standing on a surface at height zb.
    Returns (solid_to_add, solid_to_cut)."""
    hw, hl, t = car["w"] / 2, car["l"] / 2, car["pcb_t"]
    add, cut = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            xo, xi = sx * (hw + PCB_CLR + FENCE_T), sx * (hw - PAD)
            yo, yi = sy * (hl + PCB_CLR + FENCE_T), sy * (hl - PAD)
            add.append(box(min(xo, xi), max(xo, xi), min(yo, yi), max(yo, yi),
                           zb, zb + PAD_H + t))
    # pocket for the PCB itself (leaves the fences standing around each corner)
    cut.append(box(-hw - PCB_CLR, hw + PCB_CLR, -hl - PCB_CLR, hl + PCB_CLR,
                   zb + PAD_H, zb + PAD_H + t + 50))
    # optional pilot holes under the carrier's own mounting holes
    for (hx, hy) in car["holes"]:
        cut.append(cyl(hx, hy, 1.3, zb + PAD_H - 6.5, zb + PAD_H + 1))
    # toe-clamp bosses, top face level with the PCB top face
    by = hl + PCB_CLR + CLAMP_BOSS_OFFSET
    hd = FASTENER_HOLE_D[FASTENER]
    for sx in (-1, 1):
        for sy in (-1, 1):
            add.append(cyl(sx * CLAMP_X, sy * by, CLAMP_BOSS_R, zb, zb + PAD_H + t))
            cut.append(cyl(sx * CLAMP_X, sy * by, hd / 2, zb + PAD_H + t - 6.3, zb + PAD_H + t + 1))
    return union(add), union(cut)


def clamp_positions(car):
    by = car["l"] / 2 + PCB_CLR + CLAMP_BOSS_OFFSET
    return [(sx * CLAMP_X, sy * by, sy) for sx in (-1, 1) for sy in (-1, 1)]


def toe_clamp():
    """Flat stadium with one screw hole. Hole at the origin, finger along +Y."""
    r = CLAMP_W / 2
    y0, y1 = -CLAMP_HOLE_FROM_END, CLAMP_L - CLAMP_HOLE_FROM_END
    cs = rrect(-r, r, y0, y1, r)
    return finish(extrude(cs, 0, CLAMP_T) - cyl(0, 0, SCREW_CLEAR_D / 2, -1, CLAMP_T + 1))


def acc_pad(x0, x1, y0, y1, zb, hole_floor):
    """Raised pad with a grid of pilot holes for one small sensor breakout."""
    pad = extrude(rrect(x0, x1, y0, y1, 2.0), zb, zb + ACC_PAD_H)
    nx = int((x1 - x0 - 5.0) // ACC_PITCH) + 1
    ny = int((y1 - y0 - 5.0) // ACC_PITCH) + 1
    ox = (x0 + x1) / 2 - (nx - 1) * ACC_PITCH / 2
    oy = (y0 + y1) / 2 - (ny - 1) * ACC_PITCH / 2
    holes = [cyl(ox + i * ACC_PITCH, oy + j * ACC_PITCH, ACC_HOLE_D / 2,
                 zb - hole_floor, zb + ACC_PAD_H + 1, 16)
             for i in range(nx) for j in range(ny)]
    return pad, union(holes), (nx, ny)


# --------------------------------------------------------------------------
# 5. The printable case
# --------------------------------------------------------------------------


def case_dims(v):
    car, brd = CARRIERS[v["carrier"]], BOARDS[v["board"]]
    d = {}
    d["ixh"] = car["w"] / 2 + PCB_CLR + SIDE_CH                 # interior half width
    d["y0"] = -car["l"] / 2 - PCB_CLR - MARGIN_USB               # interior -Y face
    d["y1"] = car["l"] / 2 + PCB_CLR + ACC_BAY                   # interior +Y face
    d["zc"] = FLOOR + PAD_H                                      # carrier underside
    d["zct"] = d["zc"] + car["pcb_t"]                            # carrier top face
    d["zw"] = d["zct"] + CLEAR_ABOVE                             # top of the walls
    d["ztop"] = d["zw"] + LID_T
    d["brd_zb"] = d["zct"] + car["socket_h"] + HEADER_SPACER     # dev board underside
    d["usb_zc"] = d["brd_zb"] + brd["pcb_t"] + USB_BODY_H / 2    # USB connector centre
    d["usb_y"] = -car["l"] / 2 + v["usb_edge"]                   # dev board USB-end edge
    d["usb_z0"] = d["usb_zc"] - USB_BAY_HALF_H
    d["usb_z1"] = d["zw"] - TONGUE_H
    d["bosses"] = [(sx * (d["ixh"] - BOSS_INSET),
                    d["y0"] + BOSS_INSET if sy < 0 else d["y1"] - BOSS_INSET)
                   for sx in (-1, 1) for sy in (-1, 1)]
    # cable exits: list of (label, x centre, width, depth)
    exits = []
    for group, sign in ((EXITS_LEFT, -1), (EXITS_RIGHT, 1)):
        x = EXIT_START_X
        for (label, dia, n) in group:
            w = dia * n + EXIT_SLACK
            exits.append(dict(label=label, x=sign * (x - w / 2), w=w,
                              depth=dia - EXIT_SQUEEZE, dia=dia, n=n))
            x -= w + EXIT_TOOTH
    d["exits"] = exits
    # BMP280 pocket on the +X wall near the +Y end
    d["pk_y1"] = d["y1"] - 8.0
    d["pk_y0"] = d["pk_y1"] - PK_IN_Y - 2 * PK_WALL
    d["pk_x0"] = d["ixh"] + WALL
    d["pk_x1"] = d["pk_x0"] + PK_IN_X + PK_WALL
    return d


def outlines(d):
    r_in = R_OUT - WALL
    inner = rrect(-d["ixh"], d["ixh"], d["y0"], d["y1"], r_in)
    outer = grow(inner, WALL)
    return inner, outer


def exit_cutter(e, zw, y_a, y_b):
    """Slot open to the top of the wall, rounded bottom, extruded through the wall."""
    w, dep = e["w"], e["depth"]
    r = min(w / 2, e["dia"] / 2)
    zb = zw - dep
    shape = CrossSection.square([w, dep + 2 - r]).translate([e["x"] - w / 2, zb + r])
    shape += CrossSection.square([w - 2 * r + 1e-3, r + 1e-3]).translate([e["x"] - w / 2 + r, zb])
    for sx in (-1, 1):
        shape += CrossSection.circle(r, 48).translate([e["x"] + sx * (w / 2 - r), zb + r])
    return extrude_xz(shape, y_a, y_b)


def build_case(v):
    car, brd = CARRIERS[v["carrier"]], BOARDS[v["board"]]
    d = case_dims(v)
    inner, outer = outlines(d)
    ixh, y0, y1, zw = d["ixh"], d["y0"], d["y1"], d["zw"]
    hd = FASTENER_HOLE_D[FASTENER]

    # ---------------- base ----------------
    shell = chamfered_slab(outer, 0, zw, CHAMFER_BOTTOM, at_top=False)
    cavity = extrude(inner, FLOOR, zw + 1)
    add, cut = [], []

    for (bx, by) in d["bosses"]:
        add.append(cyl(bx, by, BOSS_R, FLOOR - 0.01, zw))
        cut.append(cyl(bx, by, hd / 2, zw - BOSS_HOLE_DEPTH, zw + 1))

    bay_add, bay_cut = carrier_bay(car, FLOOR - 0.01)
    add.append(bay_add)
    cut.append(bay_cut.translate([0, 0, 0.01]))

    # zip-tie anchors in both wiring channels
    ax = car["w"] / 2 + PCB_CLR + FENCE_T + (SIDE_CH - FENCE_T) / 2 + 0.6
    d["anchors"] = [(sx * ax, y0 + yy) for sx in (-1, 1) for yy in (18.0, 36.0)]
    for (x, y) in d["anchors"]:
        add.append(tent_anchor(x, y, FLOOR - 0.01))

    # accessory pad in the +Y bay, kept to the -X side, away from the antenna
    ap = (-ixh + 6.0, -2.0, car["l"] / 2 + PCB_CLR + 12.5, y1 - 2.5)
    pad, pad_holes, d["acc_grid"] = acc_pad(*ap, zb=FLOOR - 0.01, hole_floor=1.2)
    d["acc_pad"] = ap
    add.append(pad)
    cut.append(pad_holes)

    # mounting ears with keyholes (hang the case with the cables pointing down)
    ears, keys = [], []
    for sx in (-1, 1):
        xa, xb = sx * (ixh + WALL - ROOT), sx * (ixh + WALL + EAR_L)
        ear = rrect(min(xa, xb) - (3 if sx > 0 else 0), max(xa, xb) + (3 if sx < 0 else 0),
                    EAR_Y - EAR_W / 2, EAR_Y + EAR_W / 2, 5.0)
        clip = CrossSection.square([EAR_L + ROOT, EAR_W]).translate(
            [min(xa, xb), EAR_Y - EAR_W / 2])
        ears.append(extrude(ear ^ clip, 0, EAR_T))
        kx = sx * (ixh + WALL + EAR_L / 2 + 0.5)
        key = CrossSection.circle(KEY_BIG_D / 2).translate([kx, EAR_Y - KEY_TRAVEL / 2])
        key += rrect(kx - KEY_SLOT_D / 2, kx + KEY_SLOT_D / 2, EAR_Y - KEY_TRAVEL / 2,
                     EAR_Y + KEY_TRAVEL / 2 + KEY_SLOT_D / 2, KEY_SLOT_D / 2)
        keys.append(extrude(key, -1, EAR_T + 1))
        d.setdefault("keyholes", []).append((kx, EAR_Y))

    # BMP280 pocket: an open-topped box on the outside of the +X wall
    pk_cs = rrect(d["pk_x0"] - 4.0, d["pk_x1"], d["pk_y0"], d["pk_y1"], 3.0) ^ \
        CrossSection.square([d["pk_x1"] - d["pk_x0"] + ROOT, PK_IN_Y + 2 * PK_WALL]).translate(
            [d["pk_x0"] - ROOT, d["pk_y0"]])
    pocket = extrude(pk_cs, 0, zw)
    # the cavity bites 0.2 mm into the case wall so its face is not coplanar with it
    pk_cav = box(d["pk_x0"] - 0.2, d["pk_x0"] + PK_IN_X, d["pk_y0"] + PK_WALL,
                 d["pk_y1"] - PK_WALL, FLOOR, zw + 1)
    pk_cuts = [pk_cav]
    yc = (d["pk_y0"] + d["pk_y1"]) / 2
    for dy in (-5.0, 0.0, 5.0):       # vertical slits in the outer (+X) face
        pk_cuts.append(box(d["pk_x1"] - PK_WALL - 1, d["pk_x1"] + 1,
                           yc + dy - PK_SLIT / 2, yc + dy + PK_SLIT / 2, FLOOR + 3.6, zw - 6.0))
    xc = d["pk_x0"] + PK_IN_X / 2
    for dx in (-2.8, 2.8):            # and in the -Y face (downward when hung)
        pk_cuts.append(box(xc + dx - PK_SLIT / 2, xc + dx + PK_SLIT / 2,
                           d["pk_y0"] - 1, d["pk_y0"] + PK_WALL + 1, FLOOR + 3.6, zw - 6.0))
    # wire notch through the shared wall
    notch = box(ixh - 1, d["pk_x0"] + 1, yc - PK_NOTCH_W / 2, yc + PK_NOTCH_W / 2,
                zw - PK_NOTCH_D, zw + 1)
    d["pk_notch_y"] = yc

    # openings in the -Y wall: USB bay (open to the top, the lid tongue closes it)
    wall_y_a, wall_y_b = y0 - WALL - 1, y0 + 1
    usb_bay = box(-USB_BAY_W / 2, USB_BAY_W / 2, wall_y_a, wall_y_b, d["usb_z0"], zw + 1)
    exits = [exit_cutter(e, zw, wall_y_a, wall_y_b) for e in d["exits"]]

    base = shell + union(ears) + pocket
    base -= cavity
    base += union(add)
    base -= union(cut + keys + pk_cuts + [notch, usb_bay] + exits)

    # ---------------- lid ----------------
    plate = chamfered_slab(outer, zw, zw + LID_T, CHAMFER_LID, at_top=True)
    tab = chamfered_slab(rrect(d["pk_x0"] - 12.0, d["pk_x1"], d["pk_y0"], d["pk_y1"], 3.0),
                         zw, zw + LID_T, CHAMFER_LID, at_top=True)
    lip_o = grow(inner, -LIP_CLR)
    lip_i = grow(lip_o, -LIP_T)
    lip = extrude(lip_o - lip_i, zw - LIP_H, zw + 0.01)
    lip_cuts = [cyl(bx, by, BOSS_R + 0.4, zw - LIP_H - 1, zw) for (bx, by) in d["bosses"]]
    for sign in (-1, 1):          # no lip behind the cable exits
        xs = [e["x"] + s_ * e["w"] / 2 for e in d["exits"] if e["x"] * sign > 0 for s_ in (-1, 1)]
        inner_x = min(abs(x) for x in xs) - 1.5      # from here out to the corner boss
        lip_cuts.append(box(min(sign * inner_x, sign * (ixh + 1)), max(sign * inner_x, sign * (ixh + 1)),
                            y0 - 1, y0 + LIP_T + 2, zw - LIP_H - 1, zw))
    lip_cuts.append(box(ixh - LIP_T - 2, ixh + 1, yc - PK_NOTCH_W / 2 - 0.5,
                        yc + PK_NOTCH_W / 2 + 0.5, zw - LIP_H - 1, zw))
    lip -= union(lip_cuts)
    tongue = box(-USB_BAY_W / 2 + TONGUE_CLR, USB_BAY_W / 2 - TONGUE_CLR,
                 y0 - WALL + 0.3, y0 + LIP_CLR + 0.2, zw - TONGUE_H, zw + 0.01)

    lid_cuts = [cyl(bx, by, SCREW_CLEAR_D / 2, zw - 1, zw + LID_T + 1) for (bx, by) in d["bosses"]]
    # service window above the BOOT / RESET buttons and the status LEDs
    win = brd["window"]
    wy = d["usb_y"] + win["y"]
    d["window"] = (-win["w"] / 2, win["w"] / 2, wy - win["h"] / 2, wy + win["h"] / 2)
    lid_cuts.append(extrude(rrect(*d["window"], 3.0), zw - 1, zw + LID_T + 1))
    # debossed text
    zt = zw + LID_T - TEXT_DEPTH
    ty_top = y1 - 12.0
    title_min_y = d["window"][3] + 6.0
    ys = np.linspace(ty_top, max(title_min_y + 3.0, ty_top - 26.0), len(TITLE))
    d["text"] = []
    for (s, cap), ty in zip(TITLE, ys):
        cs = text_cs(s, cap).translate([0, ty])
        lid_cuts.append(extrude(cs, zt, zw + LID_T + 1))
        b = cs.bounds()
        d["text"].append((s, cap, round(b[2] - b[0], 1)))
    for e in d["exits"]:
        cs = text_cs(e["label"], LABEL_CAP).rotate(90)
        b = cs.bounds()
        cs = cs.translate([e["x"], y0 + 3.0 - b[1]])
        lid_cuts.append(extrude(cs, zt, zw + LID_T + 1))
    cs = text_cs("USB", LABEL_CAP).translate([0, y0 + 5.5])
    lid_cuts.append(extrude(cs, zt, zw + LID_T + 1))

    lid = plate + tab + lip + tongue
    lid -= union(lid_cuts)

    # copies for the clearance check, trimmed just below the plate so the
    # plate-on-wall contact face is not reported as a zero gap
    below = box(-500, 500, -500, 500, 0, zw - 0.05)
    d["lip_only"], d["tongue_only"] = lip ^ below, tongue ^ below
    return dict(base=finish(base), lid=finish(lid), dims=d)


# --------------------------------------------------------------------------
# 6. Junction-box sled (replaces Hammond's steel inner panel 1554HPL)
# --------------------------------------------------------------------------


def sled_outline():
    hl, hw = BOX["panel_l"] / 2, BOX["panel_w"] / 2
    cs = CrossSection.square([BOX["panel_l"], BOX["panel_w"]], True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            yk = sy * (hw - BOX["notch_y"] + BOX["notch_r"])
            x_in, x_out = sx * (hl - BOX["notch_x"]), sx * (hl + 1)
            cs -= CrossSection.square([abs(x_out - x_in), hw + 1 - abs(yk)]).translate(
                [min(x_in, x_out), min(yk, sy * (hw + 1))])
            cs -= CrossSection.circle(BOX["notch_r"], 96).translate([sx * hl, yk])
    return grow(cs, -SLED_CLR, 96)


def build_sled(v):
    car = CARRIERS[v["carrier"]]
    s = {}
    plate = extrude(sled_outline(), 0, SLED_T)
    add, cut = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut.append(cyl(sx * BOX["m3_x"] / 2, sy * BOX["m3_y"] / 2, SCREW_CLEAR_D / 2,
                           -1, SLED_T + 1))
        # open U-notch for the optional #6 self-tapping screw at each end
        xs = sx * BOX["side_x"] / 2
        cut.append(cyl(xs, 0, 1.9, -1, SLED_T + 1))
        cut.append(box(min(xs, sx * 90), max(xs, sx * 90), -1.9, 1.9, -1, SLED_T + 1))
    bay_add, bay_cut = carrier_bay(car, SLED_T - 0.01)
    add.append(bay_add)
    cut.append(bay_cut.translate([0, 0, 0.01]))
    s["anchors"] = [(sx * 56.0, sy * 45.5) for sx in (-1, 1) for sy in (-1, 1)]
    for (x, y) in s["anchors"]:
        add.append(tent_anchor(x, y, SLED_T - 0.01))
    s["acc_pads"] = []
    for sx in (-1, 1):
        ap = (min(sx * 49.5, sx * 75.5), max(sx * 49.5, sx * 75.5), -30.0, 30.0)
        pad, holes, grid = acc_pad(*ap, zb=SLED_T - 0.01, hole_floor=SLED_T + 1)
        add.append(pad)
        cut.append(holes)
        s["acc_pads"].append((ap, grid))
    # recess the pad around the end U-notch so a screw head can sit on the plate
    for sx in (-1, 1):
        cut.append(cyl(sx * BOX["side_x"] / 2, 0, 5.0, SLED_T, SLED_T + ACC_PAD_H + 1))
    sled = plate + union(add) - union(cut)
    s["zc"] = SLED_T + PAD_H
    return dict(sled=finish(sled), dims=s)


# --------------------------------------------------------------------------
# 7. Placeholders for the electronics (keep-out checks and previews)
# --------------------------------------------------------------------------


def electronics(v, zc):
    """Simple solids standing in for the carrier, the dev board and a USB plug.
    zc = height of the carrier's underside."""
    car, brd = CARRIERS[v["carrier"]], BOARDS[v["board"]]
    hw, hl, t = car["w"] / 2, car["l"] / 2, car["pcb_t"]
    zct = zc + t
    out = {}
    out["carrier_pcb"] = box(-hw, hw, -hl, hl, zc, zct)
    # everything soldered on top, except the four strips the toe clamps land on
    top = box(-hw, hw, -hl, hl, zct, zct + car["top_h"])
    land = [box(sx * CLAMP_X - CLAMP_W / 2 - 0.4, sx * CLAMP_X + CLAMP_W / 2 + 0.4,
                min(sy * hl, sy * (hl - 3.0)), max(sy * hl, sy * (hl - 3.0)),
                zct - 1, zct + 20) for sx in (-1, 1) for sy in (-1, 1)]
    out["carrier_top_parts"] = top - union(land)
    # solder joints underneath, except over the four corner pads
    bot = box(-hw, hw, -hl, hl, zc - car["bottom_h"], zc)
    corners = [box(min(sx * hw, sx * (hw - PAD - 0.5)), max(sx * hw, sx * (hw - PAD - 0.5)),
                   min(sy * hl, sy * (hl - PAD - 0.5)), max(sy * hl, sy * (hl - PAD - 0.5)),
                   zc - 10, zc + 1) for sx in (-1, 1) for sy in (-1, 1)]
    out["carrier_solder_side"] = bot - union(corners)
    # dev board
    bw, bl = brd["w"] / 2, brd["l"]
    y_usb = -hl + v["usb_edge"]
    zb = zct + car["socket_h"] + HEADER_SPACER
    out["board_pcb"] = box(-bw, bw, y_usb, y_usb + bl, zb, zb + brd["pcb_t"])
    out["board_parts"] = box(-bw + 2.5, bw - 2.5, y_usb, y_usb + bl + brd["ant_overhang"],
                             zb + brd["pcb_t"], zb + brd["pcb_t"] + brd["top_h"])
    rs = brd["row_spacing"] / 2
    out["board_headers"] = union([box(sx * rs - 1.27, sx * rs + 1.27, y_usb + 0.6, y_usb + bl - 0.6,
                                      zct, zb) for sx in (-1, 1)])
    zu = zb + brd["pcb_t"] + USB_BODY_H / 2
    # one USB-C cable plugged in: 12.4 x 6.6 mm overmould, drawn 45 mm long
    plugs = [box(ux - 6.2, ux + 6.2, y_usb - 45.0, y_usb + 0.5, zu - 3.3, zu + 3.3)
             for ux in brd["usb_x"]]
    out["usb_plug"] = plugs[0]
    out["usb_plug_all"] = union(plugs)
    return out


# --------------------------------------------------------------------------
# 8. Mesh utilities, validation
# --------------------------------------------------------------------------


def to_trimesh(man):
    import trimesh
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=False)


def flip_for_print(man, ztop):
    """Turn a part upside down so its top face lies on the bed."""
    return man.rotate([180, 0, 0]).translate([0, 0, ztop])


def overhangs(tm, limit_deg=50.0, bed_eps=0.05):
    """Downward faces steeper than limit_deg from vertical, not on the bed.
    Returns a list of clusters: dict(z, area, dx, dy)."""
    import trimesh
    n = tm.face_normals
    cz = tm.triangles_center[:, 2]
    bad = (n[:, 2] < -math.sin(math.radians(limit_deg))) & (cz > bed_eps)
    idx = np.nonzero(bad)[0]
    if len(idx) == 0:
        return []
    adj = tm.face_adjacency
    keep = bad[adj[:, 0]] & bad[adj[:, 1]]
    comps = trimesh.graph.connected_components(adj[keep], nodes=idx, min_len=1)
    out = []
    for c in comps:
        tri = tm.triangles[c].reshape(-1, 3)
        area = float(tm.area_faces[c].sum())
        # perimeter of the patch = edges used by exactly one of its faces
        ed = np.sort(tm.faces[c][:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
        uniq, cnt = np.unique(ed, axis=0, return_counts=True)
        rim = uniq[cnt == 1]
        per = float(np.linalg.norm(tm.vertices[rim[:, 0]] - tm.vertices[rim[:, 1]], axis=1).sum())
        out.append(dict(z=round(float(tri[:, 2].mean()), 2), area=round(area, 2),
                        dx=round(float(np.ptp(tri[:, 0])), 2),
                        dy=round(float(np.ptp(tri[:, 1])), 2),
                        mean_width=round(2 * area / per, 2) if per > 0 else 0.0))
    return out


def summarize_overhangs(items):
    """Group the overhang patches by height above the bed."""
    groups = {}
    for it in items:
        g = groups.setdefault(it["z"], dict(z=it["z"], count=0, area=0.0, max_bridge=0.0))
        g["count"] += 1
        g["area"] = round(g["area"] + it["area"], 2)
        # a bridge spans the narrow way: the smaller of the patch's box side
        # and its mean width (2 x area / perimeter, right for letter strokes)
        g["max_bridge"] = max(g["max_bridge"], min(it["dx"], it["dy"], it["mean_width"]))
    return sorted(groups.values(), key=lambda g: g["z"])


def wall_thickness(tm, n_samples=6000, seed=1):
    """Sample the solid's thickness: from random surface points shoot a ray
    into the material and measure the distance to the opposite, roughly
    parallel face. Returns (min, 1st percentile, median)."""
    import trimesh
    rng = np.random.default_rng(seed)
    pts, fid = trimesh.sample.sample_surface(tm, n_samples, seed=seed)
    nrm = tm.face_normals[fid]
    origins = pts - nrm * 1e-3
    loc, ray_i, tri_i = tm.ray.intersects_location(origins, -nrm, multiple_hits=False)
    dist = np.linalg.norm(loc - origins[ray_i], axis=1)
    opposite = (tm.face_normals[tri_i] * nrm[ray_i]).sum(axis=1) < -0.9
    dist = dist[opposite & (dist > 1e-3)]
    return (round(float(dist.min()), 2), round(float(np.percentile(dist, 1)), 2),
            round(float(np.median(dist)), 2))


def stl_roundtrip(tm):
    """Write the mesh as binary STL (32-bit floats), read it back, weld the
    vertices and count edges that are not shared by exactly two triangles."""
    import io
    import trimesh
    back = trimesh.load(io.BytesIO(tm.export(file_type="stl")), file_type="stl", force="mesh")
    back.merge_vertices()
    edges = np.sort(back.edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return dict(watertight=bool(back.is_watertight), bad_edges=int((counts != 2).sum()),
                volume_cm3=round(float(back.volume) / 1000.0, 2))


def vol(man):
    return round(float(man.volume()), 3)


def check_solid(name, man, report):
    tm = to_trimesh(man)
    ok = (man.status() == m3.Error.NoError) and tm.is_watertight and tm.is_winding_consistent \
        and tm.volume > 0
    comps = len(man.decompose())
    report[name] = dict(
        watertight=bool(tm.is_watertight), winding_consistent=bool(tm.is_winding_consistent),
        manifold_status=str(man.status()).split(".")[-1], bodies=comps,
        triangles=int(len(tm.faces)), volume_cm3=round(float(tm.volume) / 1000.0, 2),
        euler=int(tm.euler_number),
    )
    rt = stl_roundtrip(tm)
    report[name]["stl_reload"] = rt
    return ok and comps == 1 and rt["watertight"] and rt["bad_edges"] == 0, tm


def validate(v, case, sled, clamp):
    d = case["dims"]
    car, brd = CARRIERS[v["carrier"]], BOARDS[v["board"]]
    rep = dict(variant=v["tag"], carrier=car["label"], board=brd["label"], rev=REV, solids={},
               problems=[])
    base, lid = case["base"], case["lid"]
    lid_print = flip_for_print(lid, d["ztop"])
    parts_print = {"case-base": base, "case-lid": lid_print, "toe-clamp": clamp,
                   "sled-1554h": sled["sled"]}

    for name, man in parts_print.items():
        ok, tm = check_solid(name, man, rep["solids"])
        if not ok:
            rep["problems"].append(f"{name}: not a single watertight body (in memory or after STL reload)")
        b = tm.bounds
        size = (b[1] - b[0]).round(2).tolist()
        rep["solids"][name]["size_xyz"] = size
        rep["solids"][name]["fits_bed_256"] = bool(max(size[0], size[1]) <= BED and size[2] <= BED)
        rep["solids"][name]["z_min"] = round(float(b[0][2]), 3)
        oh = summarize_overhangs(overhangs(tm))
        rep["solids"][name]["overhangs_over_50deg"] = oh
        tmin, t1, tmed = wall_thickness(tm)
        rep["solids"][name]["thickness_min_p1_median"] = [tmin, t1, tmed]
        if not rep["solids"][name]["fits_bed_256"]:
            rep["problems"].append(f"{name}: does not fit the bed")

    # lid / base fit
    fit = {}
    fit["lid_base_overlap_mm3"] = vol(lid ^ base)
    fit["lip_to_wall_gap"] = round(float(d["lip_only"].min_gap(base, 5.0)), 3)
    fit["tongue_to_usb_bay_gap"] = round(float(d["tongue_only"].min_gap(base, 5.0)), 3)
    fit["design_lip_clearance"] = LIP_CLR
    fit["design_tongue_clearance"] = TONGUE_CLR
    rep["fit"] = fit
    if fit["lid_base_overlap_mm3"] > 1e-3:
        rep["problems"].append("lid intersects base")

    # keep-out volumes: case
    el = electronics(v, d["zc"])
    clamps = union([toe_clamp().rotate([0, 0, 0 if sy < 0 else 180]).translate([x, y, d["zct"]])
                    for (x, y, sy) in clamp_positions(car)])
    keep = {}
    for nm in ("carrier_pcb", "carrier_top_parts", "carrier_solder_side", "board_pcb",
               "board_parts", "board_headers", "usb_plug_all"):
        keep[nm] = dict(vs_base=vol(el[nm] ^ base), vs_lid=vol(el[nm] ^ lid),
                        vs_clamps=vol(el[nm] ^ clamps))
        if nm == "carrier_pcb":
            keep[nm]["note"] = "clamp fingers rest ON the PCB top face (contact, zero overlap)"
        if max(keep[nm]["vs_base"], keep[nm]["vs_lid"], keep[nm]["vs_clamps"]) > 1e-3:
            rep["problems"].append(f"case keep-out violated: {nm}")
    keep["clamps_vs_base_mm3"] = vol(clamps ^ base)
    keep["clamps_vs_lid_mm3"] = vol(clamps ^ lid)
    rep["keepout_case_mm3"] = keep
    probe = box(-car["w"] / 2, car["w"] / 2, -car["l"] / 2, car["l"] / 2, d["zc"] + 1.0, d["zct"])
    rep["pcb_to_fence_gap"] = round(float(probe.min_gap(base, 5.0)), 3)
    rep["board_top_to_lid_gap"] = round(float(el["board_parts"].min_gap(lid, 40.0)), 2)

    # keep-out volumes: sled inside the Hammond box
    sd = sled["dims"]
    el2 = electronics(v, sd["zc"])
    ks = {nm: vol(el2[nm] ^ sled["sled"]) for nm in
          ("carrier_pcb", "carrier_top_parts", "carrier_solder_side", "board_pcb", "board_headers")}
    if max(ks.values()) > 1e-3:
        rep["problems"].append("sled keep-out violated")
    b = to_trimesh(sled["sled"]).bounds
    stack_top = sd["zc"] + car["pcb_t"] + car["socket_h"] + HEADER_SPACER + brd["pcb_t"] + brd["top_h"]
    rep["sled"] = dict(
        box=BOX["name"], keepout_mm3=ks,
        sled_size=[round(float(b[1][0] - b[0][0]), 2), round(float(b[1][1] - b[0][1]), 2)],
        box_inside=[BOX["inside_l"], BOX["inside_w"], BOX["inside_h"]],
        side_clearance_to_box_walls=[round((BOX["inside_l"] - (b[1][0] - b[0][0])) / 2, 2),
                                     round((BOX["inside_w"] - (b[1][1] - b[0][1])) / 2, 2)],
        m3_hole_pattern=[BOX["m3_x"], BOX["m3_y"]],
        stack_top_above_box_floor=round(BOX["boss_h"] + stack_top, 1),
        headroom_under_box_lid=round(BOX["inside_h"] - BOX["boss_h"] - stack_top, 1),
        carrier_edge_to_m3_screw=round(BOX["m3_x"] / 2 - car["w"] / 2, 2),
    )

    # USB opening against the sourced connector positions (one plug = 12.4 x 6.6)
    usb = []
    for ux in brd["usb_x"]:
        usb.append(dict(
            connector_x=ux, connector_z=round(d["usb_zc"], 2),
            margin_left=round(ux - 6.2 + USB_BAY_W / 2, 2),
            margin_right=round(USB_BAY_W / 2 - (ux + 6.2), 2),
            margin_below=round(d["usb_zc"] - 3.3 - d["usb_z0"], 2),
            margin_above=round(d["usb_z1"] - (d["usb_zc"] + 3.3), 2)))
        if min(usb[-1]["margin_left"], usb[-1]["margin_right"], usb[-1]["margin_below"],
               usb[-1]["margin_above"]) < 1.0:
            rep["problems"].append("USB opening margin under 1 mm")
    rep["usb_opening"] = dict(width=USB_BAY_W, z0=round(d["usb_z0"], 2), z1=round(d["usb_z1"], 2),
                              connector_recess_from_outer_wall=round(d["usb_y"] - (d["y0"] - WALL), 2),
                              plugs=usb, position_source=v["usb_edge_note"])

    rep["case_dims"] = dict(
        outer_xy=[round(2 * (d["ixh"] + WALL), 2), round(d["y1"] - d["y0"] + 2 * WALL, 2)],
        outer_with_ears_and_pocket=rep["solids"]["case-base"]["size_xyz"],
        height_closed=round(d["ztop"], 2), interior=[round(2 * d["ixh"], 2),
                                                     round(d["y1"] - d["y0"], 2),
                                                     round(d["zw"] - FLOOR, 2)],
        wall=WALL, floor=FLOOR, lid=LID_T, lid_under_text=round(LID_T - TEXT_DEPTH, 2),
        fence=FENCE_T, pocket_wall=PK_WALL, exit_tooth=EXIT_TOOTH,
        exits=[dict(label=e["label"], x=round(e["x"], 2), width=round(e["w"], 2),
                    depth=round(e["depth"], 2)) for e in d["exits"]],
        service_window=[round(x, 2) for x in d["window"]],
        title_text=d["text"], acc_grid=d["acc_grid"],
        keyholes=[(round(x, 2), y) for (x, y) in d["keyholes"]],
    )
    return rep, parts_print


# --------------------------------------------------------------------------
# 9. Preview renderer (small z-buffer rasteriser, no GPU needed)
# --------------------------------------------------------------------------


def render(items, path, az=-35.0, el=28.0, size=(1500, 1050), ss=2, bg=(246, 244, 240)):
    """items: list of (Manifold, (r, g, b)). Orthographic, flat shaded."""
    from PIL import Image
    W, H = size[0] * ss, size[1] * ss
    a, e = math.radians(az), math.radians(el)
    rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.sin(e), math.cos(e)], [0, -math.cos(e), math.sin(e)]])
    rot = rx @ rz                              # camera: x right, y up, z toward viewer
    tris, cols = [], []
    for man, col in items:
        mesh = man.to_mesh()
        vv = np.asarray(mesh.vert_properties)[:, :3] @ rot.T
        ff = np.asarray(mesh.tri_verts)
        tris.append(vv[ff])
        cols.append(np.tile(np.asarray(col, float), (len(ff), 1)))
    tris, cols = np.concatenate(tris), np.concatenate(cols)
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    scale = min((W * 0.92) / (hi[0] - lo[0]), (H * 0.92) / (hi[1] - lo[1]))
    sx = (tris[:, :, 0] - (lo[0] + hi[0]) / 2) * scale + W / 2
    sy = H / 2 - (tris[:, :, 1] - (lo[1] + hi[1]) / 2) * scale
    sz = tris[:, :, 2]
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    front = (nrm[:, 2] > 1e-9) & (ln > 1e-12)
    nrm = nrm / np.maximum(ln, 1e-12)[:, None]
    light = np.array([-0.35, 0.55, 0.76])
    light /= np.linalg.norm(light)
    shade = 0.38 + 0.62 * np.clip(nrm @ light, 0, 1)
    zbuf = np.full((H, W), -1e18)
    img = np.empty((H, W, 3))
    img[:] = bg
    nbuf = np.zeros((H, W, 3))
    for i in np.nonzero(front)[0]:
        x, y, z = sx[i], sy[i], sz[i]
        x0, x1 = max(int(math.floor(x.min())), 0), min(int(math.ceil(x.max())), W - 1)
        y0, y1 = max(int(math.floor(y.min())), 0), min(int(math.ceil(y.max())), H - 1)
        if x1 < x0 or y1 < y0:
            continue
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
        w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (zz > sub)
        if not upd.any():
            continue
        sub[upd] = zz[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = cols[i] * shade[i]
        nbuf[y0:y1 + 1, x0:x1 + 1][upd] = nrm[i]
    # outline: darken where depth or normal jumps
    hit = zbuf > -1e17
    zf = np.where(hit, zbuf, zbuf[hit].min() - 50 if hit.any() else 0)
    edge = np.zeros((H, W), bool)
    for ax in (0, 1):
        dz = np.abs(np.diff(zf, axis=ax)) * scale
        dn = (np.diff(nbuf, axis=ax) ** 2).sum(axis=2)
        e_ = (dz > 6.0 * ss) | (dn > 0.25)
        if ax == 0:
            edge[1:, :] |= e_
            edge[:-1, :] |= e_
        else:
            edge[:, 1:] |= e_
            edge[:, :-1] |= e_
    img[edge] = img[edge] * 0.45
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    out.save(path)


COL = dict(base=(232, 150, 62), lid=(250, 224, 170), clamp=(70, 120, 170), pcb=(34, 78, 60),
           parts=(52, 60, 66), board=(26, 30, 34), metal=(190, 196, 202), plug=(225, 225, 228),
           sled=(232, 150, 62), boxc=(180, 186, 190))


def electronics_items(v, zc, with_plug=True):
    el = electronics(v, zc)
    car = CARRIERS[v["carrier"]]
    hw, hl, zct = car["w"] / 2, car["l"] / 2, zc + car["pcb_t"]
    # a slightly nicer carrier for the pictures: terminal rows + header rows
    rows = [box(sx * hw - (4.5 if sx > 0 else 0), sx * hw + (4.5 if sx < 0 else 0),
                -hl + 15, hl - 8, zct, zct + 8.5) for sx in (-1, 1)]
    hdr = [box(sx * (hw - 9.5) - 4.0, sx * (hw - 9.5) + 4.0, -hl + 15, hl - 8, zct, zct + 8.6)
           for sx in (-1, 1)]
    items = [(el["carrier_pcb"], COL["pcb"]), (union(rows), (90, 160, 90)),
             (union(hdr), (200, 170, 40)), (el["board_headers"], COL["parts"]),
             (el["board_pcb"], COL["board"]), (el["board_parts"], COL["metal"])]
    if with_plug:
        items.append((el["usb_plug"], COL["plug"]))
    return items


def make_previews(v, case, sled, clamp, outroot):
    d = case["dims"]
    car = CARRIERS[v["carrier"]]
    tag = f"{v['tag']}-rev{REV}"
    outdir = os.path.join(outroot, "pictures", f"bench-case-{v['folder']}")
    sled_dir = os.path.join(outroot, "pictures", SLED_DIR)
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(sled_dir, exist_ok=True)
    base, lid = case["base"], case["lid"]
    clamps = [toe_clamp().rotate([0, 0, 0 if sy < 0 else 180]).translate([x, y, d["zct"]])
              for (x, y, sy) in clamp_positions(car)]
    cl = union(clamps)
    paths = []

    p = os.path.join(outdir, f"preview-case-closed-{tag}.png")
    render([(base, COL["base"]), (lid, COL["lid"])] + electronics_items(v, d["zc"]), p, az=-32, el=32)
    paths.append(p)

    p = os.path.join(outdir, f"preview-case-open-{tag}.png")
    render([(base, COL["base"]), (cl, COL["clamp"])] + electronics_items(v, d["zc"]), p, az=-28, el=48)
    paths.append(p)

    p = os.path.join(outdir, f"preview-case-exploded-{tag}.png")
    lift_e, lift_c, lift_l = 38.0, 62.0, 95.0
    items = [(base, COL["base"]), (cl.translate([0, 0, lift_c]), COL["clamp"]),
             (lid.translate([0, 0, lift_l]), COL["lid"])]
    items += [(m_.translate([0, 0, lift_e]), c) for (m_, c) in electronics_items(v, d["zc"], False)]
    render(items, p, az=-32, el=22, size=(1300, 1500))
    paths.append(p)

    p = os.path.join(outdir, f"preview-case-usb-end-{tag}.png")
    render([(base, COL["base"]), (lid, COL["lid"])] + electronics_items(v, d["zc"], False),
           p, az=0, el=12)
    paths.append(p)

    p = os.path.join(outdir, f"preview-lid-underside-{tag}.png")
    render([(flip_for_print(lid, d["ztop"]), COL["lid"])], p, az=-30, el=40)
    paths.append(p)

    # sled inside a simplified open Hammond box (grey), floor bosses at 6 mm
    sd = sled["dims"]
    bl, bw = BOX["inside_l"] / 2, BOX["inside_w"] / 2
    shell = box(-bl - 3.5, bl + 3.5, -bw - 3.5, bw + 3.5, -BOX["boss_h"] - 3.0, 39.0) \
        - box(-bl, bl, -bw, bw, -BOX["boss_h"], 60.0)
    bosses = union([cyl(sx * BOX["m3_x"] / 2, sy * BOX["m3_y"] / 2, 4.0, -BOX["boss_h"], 0)
                    for sx in (-1, 1) for sy in (-1, 1)])
    cl2 = union([toe_clamp().rotate([0, 0, 0 if sy < 0 else 180]).translate(
        [x, y, sd["zc"] + car["pcb_t"]]) for (x, y, sy) in clamp_positions(car)])
    p = os.path.join(sled_dir, f"preview-sled-in-box-{tag}.png")
    render([(shell + bosses, COL["boxc"]), (sled["sled"], COL["sled"]), (cl2, COL["clamp"])]
           + electronics_items(v, sd["zc"], False), p, az=-25, el=52)
    paths.append(p)

    p = os.path.join(sled_dir, f"preview-sled-bare-{tag}.png")
    render([(sled["sled"], COL["sled"])], p, az=-25, el=50)
    paths.append(p)
    return paths


# --------------------------------------------------------------------------
# 10. Export
# --------------------------------------------------------------------------


SLED_DIR = "weatherproof-box-sled"


def export(parts_print, v, outroot):
    """Write each part into its print folder. The toe clamp is the same part
    for every variant, so each bench-case folder gets its own copy."""
    written = []
    tag = v["tag"]
    for name, man in parts_print.items():
        stem = f"{name}-rev{REV}" if name == "toe-clamp" else f"{name}-{tag}-rev{REV}"
        sub = SLED_DIR if name.startswith("sled") else f"bench-case-{v['folder']}"
        outdir = os.path.join(outroot, "print", sub)
        os.makedirs(outdir, exist_ok=True)
        tm = to_trimesh(man)
        for ext in ("stl", "3mf"):
            path = os.path.join(outdir, f"{stem}.{ext}")
            if os.path.exists(path):
                raise SystemExit(f"REFUSING to overwrite {path}\n"
                                 f"Bump REV at the top of this script (currently {REV}).")
            tm.export(path)
            written.append(path)
    return written


# --------------------------------------------------------------------------
# 11. Walter carrier sled for the Hammond box (its own revision, REV_WALTER)
#
# Stack: DPTechnics / QuickSpot Walter plugged into two 14-pin female header
# strips soldered to an Adafruit Perma-Proto full-sized board (157 x 51 mm),
# which also carries the screw terminals. The sled holds the proto board with
# the same corner pads, fences and toe clamps as the other sleds, has the same
# four M3 mounting holes, a row of zip-tie anchors for the incoming cables and
# an upright pad that carries the flat LTE antenna.
#
# Sled coordinates: origin = centre of the sled plate (as the other sleds);
# +X is the long side of the box, -Y is the side with the cable glands.
# Datasheet coordinates (X from the Walter centre line, positive towards pins
# 15 to 28 in the top view; Y from the USB-C end) map to sled coordinates with
# w_xy(): the Walter lies along X, USB-C end towards +X, antenna end towards -X.
# --------------------------------------------------------------------------

# Walter, datasheet rev 1.3 (2026-11-11), section 6 and tables 4 and 5.
WALTER = dict(
    label="DPTechnics / QuickSpot Walter P000000100 (datasheet rev 1.3)",
    w=24.8, l=55.0, pcb_t=1.6,                 # outline 55.00 x 24.80, 1.6 +/- 10 %
    row_x=8.89, pitch=2.54, pins=14, pin1_y=9.72,   # two 14-pin rows 17.78 apart
    usb_x=-4.31,                                # USB-C centre line, top side
    ufl_lte=(3.0, 4.3), ufl_gnss=(7.3, 4.3),    # u.FL connectors, top side
    sim=(0.5, 40.2), sim_w=12.0, sim_l=14.0,    # nano-SIM holder centre (sim_w, sim_l ASSUMED)
    sim_h=1.35,                                 # holder below the PCB
    top_h=3.4,                                  # USB-C receptacle, the tallest top part
    above_carrier=11.8,                         # PCB underside above carrier in an 8.5 mm socket
    socket_h=8.5,                               # female header body height (typical, not on the vendor page)
)

# Adafruit Perma-Proto Full-sized Breadboard PCB (product 1606): 157 x 51 mm,
# 1.6 mm FR4, five-hole strips across the width and a 0.3 in centre channel.
PROTO = dict(name="Adafruit Perma-Proto Full-sized Breadboard PCB (product 1606)",
             w=157.0, l=51.0, t=1.6)
PB_X0, PB_Y0 = -75.0, -23.0                    # lower-left corner of the proto board (sled XY)
PB_XC, PB_YC = PB_X0 + PROTO["w"] / 2, PB_Y0 + PROTO["l"] / 2
WALTER_X_USB = -28.0                            # sled X of the Walter's USB-C end edge
PROTO_CLAMP_XS = (-55.0, 45.0)                  # toe-clamp bosses on both long edges
TERM = dict(x0=-66.0, x1=76.0, y0=-19.5, y1=-12.5, h=9.5)   # screw-terminal row (placeholder)
RIB_W = 4.5                                     # support rib in the proto board's centre channel

ANT = dict(l=96.0, w=21.0, t=0.2, x0=-30.0, z0=16.0)   # Taoglas FXUB63.07.0150C, flat
ANT_WALL_T = 4.0
ANT_WALL_X = (-32.0, 68.0)
ANT_WALL_TOP = 40.0
ANT_RECESS = 0.5                               # shallow pocket the antenna sits in
ANT_LIP = 1.5                                  # 45 degree shelf under the antenna
CABLE_ANCHOR_XS = (-50.0, -30.0, -10.0, 10.0, 30.0, 50.0)
CABLE_ANCHOR_Y = -43.0
COAX_ANCHOR = (-40.0, 41.5)
SLED_NAME_WALTER = "sled-1554h-walter"


def w_xy(X, Y):
    """Walter datasheet coordinates (X from centre line, Y from USB-C end) to sled XY."""
    return WALTER_X_USB - Y, PB_YC - X


def wbox(X0, X1, Y0, Y1, z0, z1):
    """Box given in Walter datasheet coordinates, placed in the sled frame."""
    xa, ya = w_xy(X0, Y0)
    xb, yb = w_xy(X1, Y1)
    return box(min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb), z0, z1)


def proto_bay(zb):
    """Corner pads, fences and clamp bosses for the proto board, standing on a
    surface at height zb. Returns (add, cut, clamp_positions)."""
    t = PROTO["t"]
    x0, x1, y0, y1 = PB_X0, PB_X0 + PROTO["w"], PB_Y0, PB_Y0 + PROTO["l"]
    add, cut = [], []
    for (cx, sx) in ((x0, -1), (x1, 1)):
        for (cy, sy) in ((y0, -1), (y1, 1)):
            # no fence at the +X end: the proto board is flush with the plate there
            xo, xi = cx + sx * (PCB_CLR + (FENCE_T if sx < 0 else 0.0)), cx - sx * PAD
            yo, yi = cy + sy * (PCB_CLR + FENCE_T), cy - sy * PAD
            add.append(box(min(xo, xi), max(xo, xi), min(yo, yi), max(yo, yi), zb, zb + PAD_H + t))
    cut.append(box(x0 - PCB_CLR, x1 + PCB_CLR, y0 - PCB_CLR, y1 + PCB_CLR, zb + PAD_H, zb + PAD_H + t + 50))
    hd = FASTENER_HOLE_D[FASTENER]
    clamps = []
    for cxm in PROTO_CLAMP_XS:
        for sy in (-1, 1):
            by = (y0 - PCB_CLR - CLAMP_BOSS_OFFSET) if sy < 0 else (y1 + PCB_CLR + CLAMP_BOSS_OFFSET)
            add.append(cyl(cxm, by, CLAMP_BOSS_R, zb, zb + PAD_H + t))
            cut.append(cyl(cxm, by, hd / 2, zb + PAD_H + t - 6.3, zb + PAD_H + t + 1))
            clamps.append((cxm, by, sy))
    # support rib in the 0.3 in centre channel, where the Perma-Proto has no holes,
    # under the two header rows so the board does not flex when Walter is pressed in
    xa, _ = w_xy(0, WALTER["pin1_y"] + 13 * WALTER["pitch"] + 1.27)
    xb, _ = w_xy(0, WALTER["pin1_y"] - 1.27)
    add.append(box(xa, xb, PB_YC - RIB_W / 2, PB_YC + RIB_W / 2, zb, zb + PAD_H))
    return union(add), union(cut), clamps


def build_sled_walter():
    s = {}
    outline = sled_outline()
    plate = extrude(outline, 0, SLED_T)
    add, cut = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut.append(cyl(sx * BOX["m3_x"] / 2, sy * BOX["m3_y"] / 2, SCREW_CLEAR_D / 2, -1, SLED_T + 1))
    bay_add, bay_cut, clamps = proto_bay(SLED_T - 0.01)
    # keep the pads and fences on the plate (the proto board is flush with the plate's +X end)
    bay_add = bay_add ^ extrude(outline, -1, 80)
    add.append(bay_add)
    cut.append(bay_cut.translate([0, 0, 0.01]))
    s["clamps"] = clamps
    # strain relief: a row of zip-tie anchors across the cable-gland side, plus one for the antenna lead
    s["anchors"] = [(x, CABLE_ANCHOR_Y) for x in CABLE_ANCHOR_XS] + [COAX_ANCHOR]
    for (x, y) in s["anchors"]:
        add.append(tent_anchor(x, y, SLED_T - 0.01))
    # upright antenna pad on the +Y edge: wall, shallow pocket, 45 degree shelf
    y_face = outline.bounds()[3] - ANT_WALL_T
    s["ant_face_y"] = round(y_face, 2)
    x0, x1 = ANT_WALL_X
    add.append(box(x0, x1, y_face, y_face + ANT_WALL_T, SLED_T - 0.01, ANT_WALL_TOP))
    ax0, ax1 = ANT["x0"] - 0.5, ANT["x0"] + ANT["l"] + 0.5
    z_top = ANT["z0"] + ANT["w"] + 0.5
    # pocket with a 45 degree roof (no flat ceiling to bridge)
    pocket = poly([(y_face - 1.5, ANT["z0"]), (y_face + ANT_RECESS, ANT["z0"]),
                   (y_face + ANT_RECESS, z_top), (y_face - 1.5, z_top + ANT_RECESS + 1.5)])
    cut.append(extrude_yz(pocket, ax0, ax1))
    # shelf under the antenna: flat top, 45 degree underside, 0.8 mm at its tip
    shelf = poly([(y_face + 0.01, ANT["z0"] - ANT_LIP - 0.8), (y_face + 0.01, ANT["z0"]),
                  (y_face - ANT_LIP, ANT["z0"]), (y_face - ANT_LIP, ANT["z0"] - 0.8)])
    add.append(extrude_yz(shelf, ax0, ax1))
    sled = plate + union(add) - union(cut)
    s["zc"] = SLED_T + PAD_H
    return dict(sled=finish(sled), dims=s)


def walter_stack(zc, y_face):
    """Placeholder solids for the proto board, the Walter, headers, terminals and
    the antenna (keep-out volumes and previews). zc = underside of the proto board."""
    W, P = WALTER, PROTO
    zct = zc + P["t"]
    out = {}
    x0, x1, y0, y1 = PB_X0, PB_X0 + P["w"], PB_Y0, PB_Y0 + P["l"]
    out["proto_pcb"] = box(x0, x1, y0, y1, zc, zct)
    out["terminals"] = box(TERM["x0"], TERM["x1"], TERM["y0"], TERM["y1"], zct, zct + TERM["h"])
    # solder tails under the board, 3 mm, except over the four corner pads and the rib
    tails = box(x0, x1, y0, y1, zc - 3.0, zc)
    corners = [box(min(cx, cx - sx * (PAD + 0.5)), max(cx, cx - sx * (PAD + 0.5)),
                   min(cy, cy - sy * (PAD + 0.5)), max(cy, cy - sy * (PAD + 0.5)), zc - 10, zc + 1)
               for (cx, sx) in ((x0, -1), (x1, 1)) for (cy, sy) in ((y0, -1), (y1, 1))]
    xa, _ = w_xy(0, W["pin1_y"] + 13 * W["pitch"] + 1.27)
    xb, _ = w_xy(0, W["pin1_y"] - 1.27)
    rib = box(xa, xb, PB_YC - RIB_W / 2, PB_YC + RIB_W / 2, zc - 10, zc + 1)
    out["solder_side"] = tails - union(corners + [rib])
    # two 14-pin female headers (8.5 mm) with Walter's own header body above them
    ya, yb = W["pin1_y"] - 1.27, W["pin1_y"] + 13 * W["pitch"] + 1.27
    z_wb = zct + W["above_carrier"]
    out["headers"] = union([wbox(sx * W["row_x"] - 1.27, sx * W["row_x"] + 1.27, ya, yb, zct, z_wb)
                            for sx in (-1, 1)])
    z_wt = z_wb + W["pcb_t"]
    out["walter_pcb"] = wbox(-W["w"] / 2, W["w"] / 2, 0, W["l"], z_wb, z_wt)
    out["walter_top"] = wbox(-W["w"] / 2, W["w"] / 2, 0, W["l"], z_wt, z_wt + W["top_h"])
    sx_, sl_ = W["sim"]
    out["sim_holder"] = wbox(sx_ - W["sim_w"] / 2, sx_ + W["sim_w"] / 2, sl_ - W["sim_l"] / 2,
                             sl_ + W["sim_l"] / 2, z_wb - W["sim_h"], z_wb)
    zu = z_wt + W["top_h"] / 2
    plug = wbox(W["usb_x"] - 6.2, W["usb_x"] + 6.2, -45.0, 0.5, zu - 3.3, zu + 3.3)
    out["usb_plug"] = plug
    out["antenna"] = box(ANT["x0"], ANT["x0"] + ANT["l"], y_face + ANT_RECESS - ANT["t"],
                         y_face + ANT_RECESS, ANT["z0"], ANT["z0"] + ANT["w"])
    out["z"] = dict(proto_top=zct, walter_bottom=z_wb, walter_top=z_wt + W["top_h"])
    return out


def metal_near_antenna(clamps, zct):
    """Metal parts the antenna must stay away from that are not in walter_stack:
    the four box screws with their inserts and the four clamp screws."""
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * BOX["m3_x"] / 2, sy * BOX["m3_y"] / 2
            parts.append(cyl(x, y, 2.9, SLED_T, SLED_T + 2.6))          # screw head
            parts.append(cyl(x, y, 2.3, -BOX["boss_h"], SLED_T))        # screw shaft and insert
    for (x, y, sy) in clamps:
        parts.append(cyl(x, y, 2.9, zct + CLAMP_T, zct + CLAMP_T + 2.6))
    return union(parts)


def validate_walter(sled):
    W, P = WALTER, PROTO
    rep = dict(part=SLED_NAME_WALTER, rev=REV_WALTER, walter=W["label"], proto_board=P["name"],
               fastener=FASTENER, solids={}, problems=[])
    s, d = sled["sled"], sled["dims"]
    ok, tm = check_solid(SLED_NAME_WALTER, s, rep["solids"])
    sol = rep["solids"][SLED_NAME_WALTER]
    if not ok:
        rep["problems"].append("sled: not a single watertight body (in memory or after STL reload)")
    b = tm.bounds
    size = (b[1] - b[0]).round(2).tolist()
    sol["size_xyz"] = size
    sol["fits_bed_256"] = bool(max(size[0], size[1]) <= BED and size[2] <= BED)
    sol["z_min"] = round(float(b[0][2]), 3)
    sol["overhangs_over_50deg"] = summarize_overhangs(overhangs(tm))
    sol["thickness_min_p1_median"] = list(wall_thickness(tm))
    if not sol["fits_bed_256"]:
        rep["problems"].append("sled: does not fit the bed")
    if sol["overhangs_over_50deg"]:
        rep["problems"].append("sled: overhangs over 50 degrees (needs supports)")

    el = walter_stack(d["zc"], d["ant_face_y"])
    zct = el["z"]["proto_top"]
    clamps = union([toe_clamp().rotate([0, 0, 0 if sy < 0 else 180]).translate([x, y, zct])
                    for (x, y, sy) in d["clamps"]])
    keep = {}
    for nm in ("proto_pcb", "terminals", "solder_side", "headers", "walter_pcb", "walter_top",
               "sim_holder", "usb_plug", "antenna"):
        keep[nm] = dict(vs_sled=vol(el[nm] ^ s), vs_clamps=vol(el[nm] ^ clamps))
        if max(keep[nm].values()) > 1e-3:
            rep["problems"].append(f"keep-out violated: {nm}")
    keep["clamps_vs_sled_mm3"] = vol(clamps ^ s)
    rep["keepout_mm3"] = keep

    # headroom and fit in the Hammond box (stack on 6 mm bosses, box lid on)
    parts_all = union([s, el["proto_pcb"], el["terminals"], el["headers"], el["walter_pcb"],
                       el["walter_top"], el["sim_holder"], el["antenna"], clamps])
    bb = to_trimesh(parts_all).bounds
    z_top_stack = el["z"]["walter_top"]
    rep["box_fit"] = dict(
        box=BOX["name"],
        assembly_extent_xyz=[round(float(bb[0][0]), 2), round(float(bb[1][0]), 2),
                             round(float(bb[0][1]), 2), round(float(bb[1][1]), 2),
                             round(float(bb[0][2]), 2), round(float(bb[1][2]), 2)],
        box_inside_xy=[BOX["inside_l"], BOX["inside_w"]],
        side_clearance_x=[round(BOX["inside_l"] / 2 + float(bb[0][0]), 2),
                          round(BOX["inside_l"] / 2 - float(bb[1][0]), 2)],
        side_clearance_y=[round(BOX["inside_w"] / 2 + float(bb[0][1]), 2),
                          round(BOX["inside_w"] / 2 - float(bb[1][1]), 2)],
        walter_top_above_box_floor=round(BOX["boss_h"] + z_top_stack, 2),
        highest_point_above_box_floor=round(BOX["boss_h"] + float(bb[1][2]), 2),
        headroom_under_box_lid=round(BOX["inside_h"] - BOX["boss_h"] - float(bb[1][2]), 2),
        headroom_over_walter=round(BOX["inside_h"] - BOX["boss_h"] - z_top_stack, 2),
    )
    if (bb[0][0] < -BOX["inside_l"] / 2 or bb[1][0] > BOX["inside_l"] / 2 or
            bb[0][1] < -BOX["inside_w"] / 2 or bb[1][1] > BOX["inside_w"] / 2 or
            rep["box_fit"]["headroom_under_box_lid"] < 5.0):
        rep["problems"].append("assembly does not fit the box with the lid on")

    # LTE antenna: distance to metal (datasheet: at least 10 mm, ideally 20 mm)
    metal = metal_near_antenna(d["clamps"], zct)
    dist = {}
    for nm in ("proto_pcb", "terminals", "headers", "walter_pcb", "walter_top"):
        dist[nm] = round(float(el["antenna"].min_gap(el[nm], 60.0)), 1)
    dist["screws_and_inserts"] = round(float(el["antenna"].min_gap(metal, 60.0)), 1)
    near = min(dist.values())
    rep["antenna"] = dict(part="Taoglas FXUB63.07.0150C, 96 x 21 x 0.2 mm, 150 mm lead, I-PEX MHF I",
                          pad_face_y=d["ant_face_y"], z_range=[ANT["z0"], ANT["z0"] + ANT["w"]],
                          x_range=[ANT["x0"], ANT["x0"] + ANT["l"]], min_distance_to_metal_mm=dist,
                          nearest_mm=near, vendor_minimum_mm=10, vendor_ideal_mm=20)
    if near < 10.0:
        rep["problems"].append("antenna closer than 10 mm to metal")

    # access: USB-C plug (drawn 45 mm long, over the board, nothing above 19.1 mm in its way)
    rep["usb_access"] = dict(
        plug_vs_sled_board_terminals_clamps_antenna_mm3=vol(el["usb_plug"] ^ union(
            [s, el["proto_pcb"], el["terminals"], el["headers"], el["antenna"], clamps])),
        plug_z_range=[round(float(to_trimesh(el["usb_plug"]).bounds[0][2]), 2),
                      round(float(to_trimesh(el["usb_plug"]).bounds[1][2]), 2)],
        tallest_thing_under_plug=round(zct + TERM["h"], 2))
    sx_, sl_ = W["sim"]
    xs, _ = w_xy(0, W["l"])
    holder_x, _ = w_xy(0, sl_)
    rep["sim_access"] = dict(
        walter_antenna_end_x=round(xs, 2),
        free_beyond_walter_end_to_box_wall_mm=round(BOX["inside_l"] / 2 + xs, 2),
        proto_board_edge_x=PB_X0,
        walter_overhang_beyond_board_mm=round(PB_X0 - xs, 2),
        free_height_under_sim_holder_mm=round(el["z"]["walter_bottom"] - W["sim_h"] - zct, 2),
        nano_sim_length_mm=12.3,
        note="card enters from the antenna end; only the card's last few mm reach the box wall, so "
             "lift Walter out of its sockets to change the SIM, or fit the SIM before mounting")
    rep["wifi_keepout"] = dict(
        copper_free_beyond_board_edge_mm=round(PB_X0 - xs, 2), vendor_minimum_mm=6.0,
        note="the proto board stops 8 mm short of Walter's antenna end (datasheet 6.5: copper-free 24.8 x 6 mm)")
    rep["layout"] = dict(
        sled_plate=[round(float(b[1][0] - b[0][0]), 2), round(float(b[1][1] - b[0][1]), 2), SLED_T],
        m3_hole_pattern=[BOX["m3_x"], BOX["m3_y"]],
        proto_board_xy=[PB_X0, PB_X0 + P["w"], PB_Y0, PB_Y0 + P["l"]],
        walter_usb_end_x=WALTER_X_USB, walter_centre_y=PB_YC,
        board_underside_z=d["zc"], proto_top_z=zct, walter_pcb_bottom_z=el["z"]["walter_bottom"],
        clamp_positions=[(x, round(y, 2)) for (x, y, _sy) in d["clamps"]],
        cable_anchors=d["anchors"], antenna_wall_x=list(ANT_WALL_X), antenna_wall_top_z=ANT_WALL_TOP,
        terminal_row=[TERM["x0"], TERM["x1"], TERM["y0"], TERM["y1"]],
        terminal_positions_at_3p5mm=int((TERM["x1"] - TERM["x0"]) // 3.5))
    rep["assumed_not_measured"] = [
        "Walter and Perma-Proto outlines come from vendor documents, not calipers",
        "Perma-Proto mounting-hole positions are not used by this sled (clamps hold the board)",
        "SIM holder footprint 12 x 14 mm and header body height 8.5 mm are assumed",
        "terminal-block height 9.5 mm is assumed",
    ]
    return rep


def make_previews_walter(sled, outroot):
    d = sled["dims"]
    outdir = os.path.join(outroot, "pictures", SLED_DIR)
    os.makedirs(outdir, exist_ok=True)
    el = walter_stack(d["zc"], d["ant_face_y"])
    zct = el["z"]["proto_top"]
    cl = union([toe_clamp().rotate([0, 0, 0 if sy < 0 else 180]).translate([x, y, zct])
                for (x, y, sy) in d["clamps"]])
    tag = f"walter-rev{REV_WALTER}"
    paths = []
    p = os.path.join(outdir, f"preview-sled-bare-{tag}.png")
    render([(sled["sled"], COL["sled"])], p, az=-25, el=50)
    paths.append(p)
    bl, bw = BOX["inside_l"] / 2, BOX["inside_w"] / 2
    shell = box(-bl - 3.5, bl + 3.5, -bw - 3.5, bw + 3.5, -BOX["boss_h"] - 3.0, 39.0) \
        - box(-bl, bl, -bw, bw, -BOX["boss_h"], 60.0)
    bosses = union([cyl(sx * BOX["m3_x"] / 2, sy * BOX["m3_y"] / 2, 4.0, -BOX["boss_h"], 0)
                    for sx in (-1, 1) for sy in (-1, 1)])
    items = [(shell + bosses, COL["boxc"]), (sled["sled"], COL["sled"]), (cl, COL["clamp"]),
             (el["proto_pcb"], COL["pcb"]), (el["terminals"], (90, 160, 90)),
             (el["headers"], COL["parts"]), (el["walter_pcb"], COL["board"]),
             (el["walter_top"], COL["metal"]), (el["usb_plug"], COL["plug"]),
             (el["antenna"], (200, 70, 150))]
    p = os.path.join(outdir, f"preview-sled-in-box-{tag}.png")
    render(items, p, az=-25, el=52)
    paths.append(p)
    return paths


def export_walter(sled, outroot):
    outdir = os.path.join(outroot, "print", SLED_DIR)
    os.makedirs(outdir, exist_ok=True)
    tm = to_trimesh(sled["sled"])
    written = []
    for ext in ("stl", "3mf"):
        path = os.path.join(outdir, f"{SLED_NAME_WALTER}-rev{REV_WALTER}.{ext}")
        if os.path.exists(path):
            raise SystemExit(f"REFUSING to overwrite {path}\n"
                             f"Bump REV_WALTER at the top of this script (currently {REV_WALTER}).")
        tm.export(path)
        written.append(path)
    return written


def main_walter(args):
    print("== Walter sled (part rev %d)" % REV_WALTER)
    sled = build_sled_walter()
    rep = validate_walter(sled)
    if not args.no_export:
        rep["files"] = [os.path.basename(p) for p in export_walter(sled, args.outdir)]
    if not args.no_render:
        rep["previews"] = [os.path.basename(p) for p in make_previews_walter(sled, args.outdir)]
    s = rep["solids"][SLED_NAME_WALTER]
    print(f"  watertight={s['watertight']} stl_reload={s['stl_reload']} bodies={s['bodies']} "
          f"size={s['size_xyz']} vol={s['volume_cm3']} cm3 thickness(min/p1/med)={s['thickness_min_p1_median']}")
    print(f"  overhangs over 50 deg: {s['overhangs_over_50deg'] or 'none'}")
    print(f"  box fit: {rep['box_fit']}")
    print(f"  antenna nearest metal: {rep['antenna']['nearest_mm']} mm")
    print(f"  problems: {rep['problems'] or 'none'}")
    rpath = os.path.join(args.outdir, "checks", f"validation-walter-rev{REV_WALTER}.json")
    if not args.no_export:
        os.makedirs(os.path.dirname(rpath), exist_ok=True)
        if os.path.exists(rpath):
            raise SystemExit(f"REFUSING to overwrite {rpath}; bump REV_WALTER.")
        with open(rpath, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1)
    return bool(rep["problems"])


def main_legacy(args):
    """Case, lid, toe clamp and the two dev-board sleds (revision REV)."""
    keys = sorted(VARIANTS) if args.variant == "all" else [args.variant]
    clamp = toe_clamp()
    all_reports, failed = [], False
    for k in keys:
        v = VARIANTS[k]
        print(f"== variant {k}: {v['carrier']} + {v['board']}")
        case, sled = build_case(v), build_sled(v)
        rep, parts_print = validate(v, case, sled, clamp)
        rep["fastener"] = FASTENER
        if not args.no_export:
            rep["files"] = [os.path.basename(p) for p in export(parts_print, v, args.outdir)]
        if not args.no_render:
            rep["previews"] = [os.path.basename(p) for p in
                               make_previews(v, case, sled, clamp, args.outdir)]
        all_reports.append(rep)
        for name, s in rep["solids"].items():
            print(f"  {name:11s} watertight={s['watertight']} stl_reload={s['stl_reload']} bodies={s['bodies']} "
                  f"size={s['size_xyz']} vol={s['volume_cm3']} cm3 "
                  f"thickness(min/p1/med)={s['thickness_min_p1_median']}")
        print(f"  fit: {rep['fit']}")
        print(f"  problems: {rep['problems'] or 'none'}")
        failed |= bool(rep["problems"])
    rpath = os.path.join(args.outdir, "checks", f"validation-rev{REV}.json")
    if not args.no_export:
        os.makedirs(os.path.dirname(rpath), exist_ok=True)
        if os.path.exists(rpath):
            raise SystemExit(f"REFUSING to overwrite {rpath}; bump REV.")
        with open(rpath, "w", encoding="utf-8") as fh:
            json.dump(all_reports, fh, indent=1)
    else:
        print(json.dumps(all_reports, indent=1))
    return failed



def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--part", choices=["all", "legacy", "walter"], default="all",
                    help="legacy = case, lid, clamp and dev-board sleds; walter = the Walter sled only")
    ap.add_argument("--variant", choices=sorted(VARIANTS) + ["all"], default="all",
                    help="dev-board variant (legacy part only)")
    ap.add_argument("--outdir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="output root; print/, pictures/ and checks/ are created under it "
                         "(default: the folder that holds source/)")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-export", action="store_true", help="validate only")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    failed = False
    if args.part in ("all", "legacy"):
        failed |= main_legacy(args)
    if args.part in ("all", "walter"):
        failed |= main_walter(args)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
