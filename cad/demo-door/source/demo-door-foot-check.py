r"""Checks for the demo door foot, and one render of the door standing on it.

    python demo-door-foot-check.py [--out DIR] [--no-render]

Reads demo-door-foot-rev<FOOT_REV>.stl from ..\print (or --out DIR) for the print checks,
and rebuilds the frame, door and foot from their generators (in-use coordinates) for the
clearance and tipping checks. Prints a report; also writes it to
..\checks\demo-door-foot-rev<FOOT_REV>-check.txt and draws
..\pictures\base-plate-rev<FOOT_REV>-with-door-rev<REV>.png (all into --out DIR if given).
The door swings with the magnet block fitted, so its clearance to the foot is checked too.
"""
import argparse
import importlib.util
import io
import os
import sys

sys.dont_write_bytecode = True
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, fn):
    s = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


fg = load("fg", "demo-door-foot-generator.py")
gen = fg.gen
chk = load("chk", "demo-door-check.py")
G = 9.81e-3                      # N per gram
MU = 0.3                         # PLA on a typical table top, low end, for the sliding note


def hull2d(p):
    p = sorted(set(map(tuple, np.round(p, 6))))
    def half(pts):
        h = []
        for q in pts:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(q)
        return h
    lo, up = half(p), half(p[::-1])
    return np.array(lo[:-1] + up[:-1])          # counter-clockwise


def tip_force(poly, c, u, h, W):
    """Smallest horizontal force (direction u, at height h) that tips a body of weight W (N)
    with centre of mass c (y, z) about an edge of the convex footprint poly (y, z)."""
    best = np.inf
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        e = b - a
        n = np.array([e[1], -e[0]]) / np.linalg.norm(e)          # outward for a CCW polygon
        un = u @ n
        if un <= 1e-9:
            continue
        d = (a - c) @ n                                           # COM inside -> d > 0
        best = min(best, W * d / (h * un))
    return best


def rot_x(p, phi_deg):
    """Rotate points about the hinge axis (y = 0, z = AX_Z) by phi degrees, like Manifold.rotate."""
    t = np.radians(phi_deg)
    p = np.array(p, float).reshape(-1, 3).copy()
    y, z = p[:, 1], p[:, 2] - gen.AX_Z
    p[:, 1], p[:, 2] = y * np.cos(t) - z * np.sin(t), y * np.sin(t) + z * np.cos(t) + gen.AX_Z
    return p


def swing(m, open_deg, dx=0.0):
    return m.translate([0, 0, -gen.AX_Z]).rotate([180.0 - open_deg, 0, 0]).translate([dx, 0, gen.AX_Z])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    buf = io.StringIO()
    real = sys.stdout
    sys.stdout = type("Tee", (), {"write": lambda s, t: (real.write(t), buf.write(t)), "flush": lambda s: real.flush()})()

    name = "demo-door-foot-rev%d" % fg.FOOT_REV
    print("\n%s (with door rev %d)" % (name, gen.REV))
    root = os.path.dirname(HERE)
    d_print, d_checks, d_pics = ((args.out,) * 3 if args.out else
                                 tuple(os.path.join(root, s) for s in ("print", "checks", "pictures")))
    mesh = trimesh.load(os.path.join(d_print, name + ".stl"), force="mesh")
    parts = mesh.split(only_watertight=False)
    chk.check(len(parts) == 1, "one body: %d" % len(parts))
    chk.check(mesh.is_watertight and mesh.is_winding_consistent, "watertight %s, winding consistent %s, volume %.1f cm3"
              % (mesh.is_watertight, mesh.is_winding_consistent, mesh.volume / 1000))
    e = mesh.extents
    chk.check(abs(mesh.bounds[0][2]) < 1e-4 and max(e[0], e[1]) <= 236, "print size %.1f x %.1f x %.1f mm, min z %.4f (bed 256)" % (*e, mesh.bounds[0][2]))
    for o in chk.overhangs(mesh, "foot"):
        print("      %-13s %6.1f mm2  z %.2f  short side %.1f mm" % ("flat bridge" if o["flat"] else "curved/sloped", o["area"], o["hi"][2], o["span"]))
        chk.check(o["span"] <= 6.0, "foot overhang at z %.2f: unsupported span %.1f mm (limit 6)" % (o["hi"][2], o["span"]))
    pts, d = chk.thickness(mesh)
    d = d[np.isfinite(d)]
    print("  wall thickness from inward rays: min %.2f, 1st percentile %.2f, median %.2f mm" % (d.min(), np.percentile(d, 1), np.median(d)))

    # ---- in-use geometry ---------------------------------------------------------------------
    F, D = gen.build()
    DM = D + gen.magnet_block()                          # the magnet swings with the door
    FT = fg.build_foot()
    ov = (F ^ FT).volume()
    gap = F.min_gap(FT, 2.0)
    chk.check(ov < 1e-6, "frame sits in the foot without overlap (%.5f mm3); smallest frame-to-foot distance %.3f mm (sill on the plate = 0)" % (ov, gap))
    side = F.min_gap(FT - fg.box(-fg.FOOT_T - 1, 0.0, -500, 500, -500, 500), 2.0)
    print("  sill to lip (sideways clearance): %.3f mm" % side)

    worst, wa, gmin, ga = 0.0, None, 1e9, None
    for dx in (0.0, -gen.CONE_AXIAL_GAP):                   # door as printed, and dropped onto its cones
        for ang in np.arange(180.0, -0.01, -2.5):
            dm = swing(DM, ang, dx)
            v = (FT ^ dm).volume()
            if v > worst:
                worst, wa = v, (ang, dx)
            g = FT.min_gap(dm, 12.0)
            if g < gmin:
                gmin, ga = g, (ang, dx)
    chk.check(worst < 1e-6, "door swing 180 -> 0 deg in 2.5 deg steps (also dropped %.2f mm onto its cones) never touches the foot: worst overlap %.5f mm3"
              % (gen.CONE_AXIAL_GAP, worst))
    print("  smallest door-to-foot distance during the swing: %.2f mm (at %.1f deg, drop %.2f)" % (gmin, ga[0], -ga[1]))

    # ---- tipping -----------------------------------------------------------------------------
    tf, td, tft = gen.to_trimesh(F), gen.to_trimesh(D), gen.to_trimesh(FT)
    mf, cf = chk.mass_model(tf)
    md, cd0 = chk.mass_model(td)
    mft, cft = chk.mass_model(tft)
    wells = [(fg.SILL_Y0 + (fg.SILL_Y1 - fg.SILL_Y0) * (2 * i + 1) / (2.0 * fg.N_WELLS), (fg.BLOCK_Z0 + fg.BLOCK_Z1) / 2.0) for i in range(fg.N_WELLS)]
    mb = fg.N_WELLS * fg.COINS_PER_WELL * fg.COIN_G
    print("  masses (PLA, 1.2 mm skin + 15 %% infill): frame %.0f g, door %.0f g, foot %.0f g; ballast %d US quarters = %.0f g"
          % (mf, md, mft, fg.N_WELLS * fg.COINS_PER_WELL, mb))
    v = tft.vertices
    foot_poly = hull2d(v[v[:, 0] < -fg.FOOT_T + 1e-4][:, 1:])
    sill_poly = np.array([(fg.SILL_Y0, 0.0), (fg.SILL_Y1, 0.0), (fg.SILL_Y1, gen.DEPTH), (fg.SILL_Y0, gen.DEPTH)])[::-1]
    sill_poly = hull2d(sill_poly)
    print("  foot footprint y %.1f..%.1f, z %.1f..%.1f (front edge %.1f mm in front of the frame); sill alone y %.1f..%.1f, z 0..%.1f"
          % (foot_poly[:, 0].min(), foot_poly[:, 0].max(), foot_poly[:, 1].min(), foot_poly[:, 1].max(), -foot_poly[:, 1].min(),
             fg.SILL_Y0, fg.SILL_Y1, gen.DEPTH))
    knob = np.array([(gen.X_D0 + gen.X_D1) / 2.0, -gen.Y_DL + gen.KNOB_FROM_LATCH, gen.T + 5.0])
    rows = []
    for ang in np.arange(0.0, 180.1, 5.0):
        phi = 180.0 - ang
        k = rot_x(knob, phi)[0]
        cd = rot_x(cd0, phi)[0]
        r = k[1:] - np.array([0.0, gen.AX_Z])
        u_open = np.array([r[1], -r[0]]) / np.linalg.norm(r)
        res = []
        for poly, base_h, masses in ((sill_poly, 0.0, [(mf, cf), (md, cd)]),
                                     (foot_poly, fg.FOOT_T, [(mf, cf), (md, cd), (mft, cft)]),
                                     (foot_poly, fg.FOOT_T, [(mf, cf), (md, cd), (mft, cft)] + [(mb / len(wells), np.array([0, y, z])) for y, z in wells])):
            m = sum(a for a, _ in masses)
            c = sum(a * np.asarray(p) for a, p in masses) / m
            W = m * G
            h = k[0] + base_h
            res.append((tip_force(poly, c[1:], u_open, h, W), tip_force(poly, c[1:], -u_open, h, W), W))
        rows.append((ang, res))
    print("  force at the knob (horizontal, along the knob's path) that tips the stand, N:")
    print("      open   no foot: opening  closing |  foot: opening  closing |  foot + quarters: opening  closing")
    for ang, res in rows:
        print("      %3.0f deg       %7.2f  %7.2f |        %7.2f  %7.2f |                  %7.2f  %7.2f"
              % (ang, res[0][0], res[0][1], res[1][0], res[1][1], res[2][0], res[2][1]))
    mins = [min(r[i][j] for _, r in rows) for i in range(3) for j in range(2)]
    print("  worst case over 0-180 deg: no foot %.2f / %.2f N, foot %.2f / %.2f N, foot + quarters %.2f / %.2f N (opening / closing)" % tuple(mins))
    chk.check(min(mins[2], mins[3]) >= 1.5, "with the foot (no ballast) tipping takes at least 1.5 N at the knob in both directions: %.2f N" % min(mins[2], mins[3]))
    for i, lab in ((1, "foot"), (2, "foot + quarters")):
        W = rows[0][1][i][2]
        print("  sliding instead of tipping, %s: about %.2f N at friction coefficient %.1f (weight %.2f N)" % (lab, MU * W, MU, W))

    print("\n%s" % ("ALL HARD CHECKS PASS" if not chk.FAILS else "FAILED: " + "; ".join(chk.FAILS)))
    sys.stdout = real
    with open(os.path.join(d_checks, name + "-check.txt"), "w") as f:
        f.write(buf.getvalue())

    if not args.no_render:
        rnd = load("rnd", "demo-door-render.py")
        t = np.array([0.35, 0.5, -1.0])
        r = np.array([0.0, 1.0, 0.5])
        u = np.cross(t, r)
        rnd.render([(tf, rnd.FRAME_RGB), (gen.to_trimesh(swing(D, 100)), rnd.DOOR_RGB), (gen.to_trimesh(gen.switch_block()), rnd.PART_RGB), (gen.to_trimesh(swing(gen.magnet_block(), 100)), rnd.PART_RGB), (tft, np.array([0.45, 0.47, 0.52]))],
                   r, u, os.path.join(d_pics, "base-plate-rev%d-with-door-rev%d.png" % (fg.FOOT_REV, gen.REV)),
                   title="Door rev %d standing on base plate (foot) rev %d, door open 100 deg (foot grey, switch and magnet blue)" % (gen.REV, fg.FOOT_REV))


if __name__ == "__main__":
    main()
