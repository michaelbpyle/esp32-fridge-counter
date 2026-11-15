r"""Numerical checks of the demo door print plate (system Python: numpy, trimesh, manifold3d).

    python demo-door-check.py [--dir DIR] [--orig PATH-TO-Clamshell+Parts+Box+Standard.stl]

Reads demo-door-rev<REV>.stl and demo-door-rev<REV>-surface-switch.stl from DIR (default:
this folder) - the STL files themselves, not the generator's solids - and reports:
bodies and watertightness, bed fit and sizes, the smallest distance between door and frame,
the hinge clearances (against Nick Johnson's original if --orig is given), overhangs, a
swing collision sweep from the print pose to closed, wall thickness, and stand stability.
Exit code 1 if a hard check fails.
"""
import argparse
import importlib.util
import os
import sys

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gen", os.path.join(HERE, "demo-door-generator.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

BED = 256.0
OVERHANG_DEG = 50.0            # limit, measured from vertical
PLA = 1.24e-3                  # g/mm3
SHELL, INFILL = 1.2, 0.15      # print model for the mass estimate: 1.2 mm skin, 15 % infill
FAILS = []


def check(ok, text):
    print("  [%s] %s" % ("ok" if ok else "FAIL", text))
    if not ok:
        FAILS.append(text)


def to_manifold(mesh):
    m = Manifold(Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32), tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
    return m


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def swing(m, open_deg, ay, az, dx=0.0):
    """Door manifold at an opening angle: 180 is the print pose, 0 is closed."""
    return m.translate([0, -ay, -az]).rotate([180.0 - open_deg, 0, 0]).translate([dx, ay, az])


def overhangs(mesh, label):
    n, c, a = mesh.face_normals, mesh.triangles_center, mesh.area_faces
    lim = -np.sin(np.radians(OVERHANG_DEG))
    bad = (n[:, 2] < lim) & (mesh.triangles[:, :, 2].max(1) > 0.02)
    idx = np.nonzero(bad)[0]
    out = []
    if len(idx):
        adj = mesh.face_adjacency
        keep = bad[adj[:, 0]] & bad[adj[:, 1]]
        groups = trimesh.graph.connected_components(adj[keep], nodes=idx)
        for g in groups:
            v = mesh.triangles[g].reshape(-1, 3)
            lo, hi = v.min(0), v.max(0)
            flat = bool(np.all(n[g][:, 2] < -0.999))
            out.append(dict(area=float(a[g].sum()), lo=lo, hi=hi, flat=flat, span=float(min(hi[0] - lo[0], hi[1] - lo[1]))))
    out.sort(key=lambda d: -d["area"])
    print("  %s: %d downward areas steeper than %.0f deg from vertical, %.1f mm2 in all" % (label, len(out), OVERHANG_DEG, sum(d["area"] for d in out)))
    return out


def thickness(mesh, n=3000, seed=1):
    """Wall thickness by casting a ray inward from random surface points."""
    rng = np.random.default_rng(seed)
    pts, fid = trimesh.sample.sample_surface(mesh, n, seed=seed)
    nrm = mesh.face_normals[fid]
    org = pts - nrm * 1e-3
    loc, ray, _ = mesh.ray.intersects_location(org, -nrm, multiple_hits=False)
    d = np.full(n, np.nan)
    d[ray] = np.linalg.norm(loc - org[ray], axis=1)
    return pts, d


def mass_model(mesh):
    """Mass (g) and centre of mass for a 1.2 mm skin plus 15 % infill."""
    A, V = mesh.area, mesh.volume
    cA = (mesh.triangles_center * mesh.area_faces[:, None]).sum(0) / A
    cV = mesh.center_mass
    ws, wi = A * SHELL * (1 - INFILL), INFILL * V
    return PLA * (ws + wi), (ws * cA + wi * cV) / (ws + wi)


def original(path):
    print("\nNick Johnson's original (%s)" % os.path.basename(path))
    m = trimesh.load(path, force="mesh")
    parts = m.split(only_watertight=False)
    base = to_manifold([p for p in parts if p.bounds[0][1] < 60][0])
    lid = to_manifold([p for p in parts if p.bounds[0][1] > 60][0])
    print("  smallest distance between his two bodies as printed: %.3f mm (a knuckle leg passing the corner of the other half's wall)" % base.min_gap(lid, 2.0))
    # one inner cone joint (lid knuckle 13.26-19.39, base knuckle 18.64-26.77), inside r 1.2 of the axis
    cone = box(17.5, 20.5, 68 - 0.85, 68 + 0.85, 12.5 - 0.85, 12.5 + 0.85)
    print("  cone gap, inner joint (x 18.4-19.6): %.3f mm" % (base ^ cone).min_gap(lid ^ cone, 2.0))
    cone = box(12.5, 15.0, 68 - 0.85, 68 + 0.85, 12.5 - 0.85, 12.5 + 0.85)
    print("  cone gap, end joint (x 13.0-14.3): %.3f mm" % (base ^ cone).min_gap(lid ^ cone, 2.0))
    slab = box(15.5, 17.0, 60, 67.3, 11.0, 15)
    print("  knuckle round to its hollow in the other half (x 15.5-17, away from the cones): %.3f mm" % (base ^ slab).min_gap(lid ^ slab, 2.0))


def run(path, recessed):
    print("\n%s" % os.path.basename(path))
    plate = trimesh.load(path, force="mesh")
    p3 = os.path.splitext(path)[0] + ".3mf"
    if os.path.exists(p3):
        m3 = trimesh.load(p3, force="mesh")
        check(len(m3.faces) == len(plate.faces) and abs(m3.volume - plate.volume) < 1.0 and np.allclose(m3.bounds, plate.bounds, atol=1e-3),
              "%s holds the same plate (%d triangles, %.1f cm3)" % (os.path.basename(p3), len(m3.faces), m3.volume / 1000))
    parts = plate.split(only_watertight=False)
    check(len(parts) == 2, "separate bodies in the plate: %d (want 2: frame and door, not fused)" % len(parts))
    if len(parts) != 2:
        return
    frame, door = sorted(parts, key=lambda p: -p.extents[2])
    for nm, p in (("frame", frame), ("door", door)):
        check(p.is_watertight and p.is_winding_consistent and p.volume > 0,
              "%s watertight %s, winding consistent %s, volume %.1f cm3, %d triangles" % (nm, p.is_watertight, p.is_winding_consistent, p.volume / 1000, len(p.faces)))
    F, D = to_manifold(frame), to_manifold(door)
    check(F.status().name == "NoError" and D.status().name == "NoError" and F.genus() >= 0, "both bodies load as valid manifolds (manifold3d)")

    ext, lo = plate.extents, plate.bounds[0]
    check(abs(lo[2]) < 1e-4 and ext[0] <= BED - 20 and ext[1] <= BED - 20 and ext[2] <= BED - 20,
          "plate %.2f x %.2f x %.2f mm, min z %.4f: fits the %d mm bed with %.0f / %.0f mm to spare" % (ext[0], ext[1], ext[2], lo[2], BED, BED - ext[0], BED - ext[1]))
    check(abs(frame.extents[0] - gen.H_TOTAL) < 0.01, "overall height %.3f mm (target %.1f)" % (frame.extents[0], gen.H_TOTAL))
    check(abs(frame.extents[2] - gen.DEPTH) < 0.01, "entry depth %.3f mm (target %.1f)" % (frame.extents[2], gen.DEPTH))
    print("  frame width %.2f mm, door %.2f x %.2f x %.2f mm (height x width x thickness; knob stands %.1f mm proud)"
          % (frame.extents[1], gen.X_D1 - gen.X_D0, gen.DOOR_W, gen.T, door.extents[2] - gen.T))
    for nm, p in (("frame", frame), ("door", door)):
        on_bed = p.area_faces[(p.face_normals[:, 2] < -0.999) & (np.abs(p.triangles_center[:, 2]) < 1e-3)].sum()
        print("  %s first-layer contact area %.0f mm2" % (nm, on_bed))

    # ---- hinge ---------------------------------------------------------------------------------
    ay, az = -door.bounds[0][1] + 0.0, gen.AX_Z                # axis: y = distance from plate edge to hinge line
    ay = gen.Y_DL
    gap = F.min_gap(D, 3.0)
    check(gap >= 0.15, "smallest door-to-frame distance anywhere, print pose: %.3f mm (want >= 0.15)" % gap)
    r = gen.CONE_R_BASE
    for i, (xg, d) in enumerate(gen.knuckle_gaps()):
        k = r * 0.6
        cone = box(xg - 1.0, xg + r + 1.0, ay - k, ay + k, az - k, az + k) if d > 0 else box(xg - r - 1.0, xg + 1.0, ay - k, ay + k, az - k, az + k)
        g_cone = (F ^ cone).min_gap(D ^ cone, 3.0)
        # flat faces: a block beside the cone, outside its base radius
        blk = box(xg - 1.0, xg + 1.0, ay - 5.9, ay - r - 0.3, az - 2, az + 2)
        g_flat = (F ^ blk).min_gap(D ^ blk, 3.0)
        blk = box(xg - 1.0, xg + 1.0, ay - 6, ay + 6, -0.01, 0.05)
        g_bed = (F ^ blk).min_gap(D ^ blk, 5.0)
        print("  joint %d at x %.2f: cone gap %.3f mm, flat faces %.3f mm, at the bed (first layer) %.3f mm" % (i + 1, xg, g_cone, g_flat, g_bed))
        check(abs(g_cone - gen.CONE_AXIAL_GAP / np.sqrt(2)) < 0.01, "joint %d cone gap is the designed %.3f mm" % (i + 1, gen.CONE_AXIAL_GAP / np.sqrt(2)))
    edge = box(gen.X_D0, gen.KNUCKLE_C[0] - gen.KNUCKLE_L / 2 - 1.0, ay - gen.Y_DH - 1, ay + gen.Y_PIL0 + 1, gen.REVEAL_CH + 0.1, gen.T)
    print("  print-pose door edge to hinge jamb: %.3f mm above the jamb's chamfer" % (F ^ edge).min_gap(D ^ edge, 3.0))
    edge = box(gen.X_D0, gen.KNUCKLE_C[0] - gen.KNUCKLE_L / 2 - 1.0, ay - gen.Y_DH - 1, ay + gen.Y_PIL0 + 3, -0.01, 0.05)
    print("  the same at the bed: %.3f mm" % (F ^ edge).min_gap(D ^ edge, 8.0))

    # ---- overhangs -----------------------------------------------------------------------------
    for nm, p in (("frame", frame), ("door", door)):
        sign = []
        for o in overhangs(p, nm):
            if o["flat"] and abs(o["hi"][2] - gen.SIGN_DEPTH) < 1e-3 and o["lo"][0] > gen.X_HEAD:
                sign.append(o)
                continue
            what = "flat bridge" if o["flat"] else "curved/sloped"
            print("      %-13s %6.1f mm2  x %.1f..%.1f  y %.1f..%.1f  z %.2f..%.2f  short side %.1f mm"
                  % (what, o["area"], o["lo"][0], o["hi"][0], o["lo"][1], o["hi"][1], o["lo"][2], o["hi"][2], o["span"]))
            check(o["span"] <= 6.0, "%s overhang at z %.2f: unsupported span %.1f mm (limit 6)" % (nm, o["hi"][2], o["span"]))
        if sign:
            print("      sign engraving: %d letter ceilings at z %.2f, %.1f mm2 in all, each bridged across a letter stroke (about %.1f mm)"
                  % (len(sign), gen.SIGN_DEPTH, sum(o["area"] for o in sign), 0.2 * gen.SIGN_CAP_H / 0.73))

    # ---- swing ---------------------------------------------------------------------------------
    # dummy switch and magnet from the listed dimensions, fitted in their bores (recessed version)
    Fs, Ds = F, D
    if recessed:
        def barrel(x_flange_face, direction):
            a, b = sorted((x_flange_face, x_flange_face + direction * gen.SW_FLANGE_T))
            c, e = sorted((x_flange_face, x_flange_face + direction * gen.SW_TOTAL_L))
            fl = Manifold.cylinder(b - a, gen.SW_FLANGE_D / 2).transform([[0, 0, 1, a], [1, 0, 0, 0], [0, 1, 0, 0]])
            br = Manifold.cylinder(e - c, gen.SW_BARREL_D / 2).transform([[0, 0, 1, c], [1, 0, 0, 0], [0, 1, 0, 0]])
            return fl + br
        rec = gen.FLANGE_NOTCH - gen.SW_FLANGE_T                    # how far each flange face sits below its edge
        sw = barrel(gen.X_HEAD + rec, +1).translate([0, ay + gen.Y_SW, az])
        mg = barrel(gen.X_D1 - rec, -1).translate([0, ay - gen.Y_SW, az])    # print pose: mirrored side
        Fs, Ds = F + sw, D + mg
        print("  face-to-face distance of the two fitted flanges, door closed: %.2f mm (rated operating gap %.0f-%.0f mm)"
              % (gen.X_HEAD - gen.X_D1 + 2 * rec, *gen.SW_RATED_GAP))
    worst, at = 0.0, None
    shifts = [(0.0, 0.0, 0.0), (-0.2, 0.0, 0.0), (0.2, 0.0, 0.0), (0.0, 0.15, 0.0), (0.0, -0.15, 0.0), (0.0, 0.0, 0.15), (0.0, 0.0, -0.15)]
    for sh in shifts:
        radial = sh[1] != 0.0 or sh[2] != 0.0
        for ang in np.arange(180.0, 2.4 if radial else -0.01, -2.5):      # radial play is not tested at 0: the stop is in the way by design
            pose = swing(D, ang, ay, az).translate(list(sh))
            v = (F ^ pose).volume()
            if recessed and sh == shifts[0]:
                v = max(v, (Fs ^ swing(Ds, ang, ay, az)).volume() - (sw ^ F).volume() - (mg ^ D).volume())
            if v > worst:
                worst, at = v, (ang, sh)
    bb = swing(D, 90.0, ay, az).bounding_box()
    print("  at 90 deg the door spans z %.1f..%.1f (it swings out in front of the frame, z < 0)" % (bb[2], bb[5]))
    check(worst < 1e-3, "swing 180 -> 0 deg in 2.5 deg steps (also with the door shifted +/-0.2 mm along the axis and +/-0.15 mm across it%s): worst overlap %.5f mm3%s"
          % (", and with the switch and magnet fitted" if recessed else "", worst, "" if at is None else " at %.1f deg, shift %s" % at))
    closed = swing(D, 0.0, ay, az)
    g0 = F.min_gap(closed, 3.0)
    stop = box(gen.X_D0, gen.X_D1, ay + gen.Y_DL - 5, ay + gen.Y_LJ + 1, gen.T - gen.STOP_BEVEL - 2, gen.T + 6)
    gs = (F ^ stop).min_gap(closed ^ stop, 3.0)
    print("  closed (0 deg): smallest distance to the frame %.3f mm; door bevel to stop rib %.3f mm" % (g0, gs))
    for ang in (-0.25, -0.5, -1.0):
        v = (F ^ swing(D, ang, ay, az)).volume()
        print("  pushed %.2f deg past closed: overlap %.3f mm3 (the stop rib)" % (-ang, v))
    check((F ^ swing(D, -0.5, ay, az)).volume() > 0.05 and gs < 0.2, "the door reaches closed and lands on the stop rib within 0.5 deg of flush")
    tops = [(gen.X_D0 - gen.X_SILL, "bottom"), (gen.X_HEAD - gen.X_D1, "top"), (gen.GAP_HINGE, "hinge side"), (gen.GAP_LATCH, "latch side")]
    print("  closed gaps: " + ", ".join("%s %.2f" % (n, g) for g, n in tops) + " mm; in use the door drops %.2f mm onto its cones" % gen.CONE_AXIAL_GAP)
    d_sw = gen.Y_SW
    for ang in (5, 10, 15, 20, 30):
        move = 2 * d_sw * np.sin(np.radians(ang) / 2)
        print("  magnet travel at %2d deg open: %.1f mm (magnet axis is %.1f mm from the hinge axis)" % (ang, move, d_sw))

    # ---- wall thickness ------------------------------------------------------------------------
    for nm, p in (("frame", frame), ("door", door)):
        pts, d = thickness(p)
        d2 = d[np.isfinite(d)]
        thin = np.isfinite(d) & (d < 0.8)
        print("  %s wall thickness from %d inward rays: min %.2f, 1st percentile %.2f, median %.2f mm; %.1f %% of the surface under 0.8 mm"
              % (nm, len(d2), d2.min(), np.percentile(d2, 1), np.median(d2), 100.0 * thin.sum() / len(d2)))
        if thin.any():
            q = pts[thin]
            print("      thin spots lie in x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f (crush ribs in the switch bores, knife edges of chamfers and grooves - not walls)"
                  % (q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max(), q[:, 2].min(), q[:, 2].max()))
    if recessed:
        br = gen.BORE_R
        print("  designed skins round the switch bores: %.2f mm below, %.2f mm above the flat cap; sign engraving to bore %.2f mm"
              % (gen.AX_Z - br, gen.T - (gen.AX_Z + br + 0.2), gen.AX_Z - br - gen.SIGN_DEPTH))

    # ---- stability, standing on the sill (x up; footprint = underside of the sill) -------------
    mf, cf = mass_model(frame)
    md, cd = mass_model(door)
    foot = frame.vertices[frame.vertices[:, 0] < 1e-3]
    y0, y1, z0, z1 = foot[:, 1].min(), foot[:, 1].max(), foot[:, 2].min(), foot[:, 2].max()
    print("  mass estimate (PLA, %.1f mm skin + %.0f %% infill): frame %.0f g, door %.0f g; solid would be %.0f g + %.0f g"
          % (SHELL, 100 * INFILL, mf, md, PLA * frame.volume, PLA * door.volume))
    print("  footprint %.1f wide x %.1f deep" % (y1 - y0, z1 - z0))
    for ang in (0, 90, 180):
        t = np.radians(180 - ang)
        ry, rz = cd[1] - ay, cd[2] - az
        dc = np.array([cd[0], ay + ry * np.cos(t) - rz * np.sin(t), az + ry * np.sin(t) + rz * np.cos(t)])
        c = (mf * cf + md * dc) / (mf + md)
        front, back, left, right = c[2] - z0, z1 - c[2], c[1] - y0, y1 - c[1]
        w = (mf + md) * 9.81e-3
        print("  door open %3d deg: centre of mass %.1f mm above the table, %.1f mm behind the front edge, margins front %.1f back %.1f left %.1f right %.1f mm;"
              " tips forward when pulled with %.2f N at knob height" % (ang, c[0], front, front, back, left, right, w * front / ((gen.X_D0 + gen.X_D1) / 2)))
        if ang == 90:
            check(min(front, back, left, right) > 5.0, "door open 90 deg: centre of mass is inside the footprint by %.1f mm at the nearest edge" % min(front, back, left, right))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE)
    ap.add_argument("--orig", default=None)
    args = ap.parse_args()
    if args.orig:
        original(args.orig)
    for recessed, tag in ((True, ""), (False, "-surface-switch")):
        run(os.path.join(args.dir, "demo-door-rev%d%s.stl" % (gen.REV, tag)), recessed)
    print("\n%s" % ("ALL HARD CHECKS PASS" if not FAILS else "%d CHECK(S) FAILED:\n  " % len(FAILS) + "\n  ".join(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
