r"""Preview images of the demo door (system Python: numpy, trimesh, manifold3d, matplotlib).

    python demo-door-render.py [--out DIR]

Builds the geometry with demo-door-generator.py (nothing is read from the STL) and writes
PNG files named demo-door-rev<REV>-<view>.png. Existing images are overwritten: they are
previews, not print files.
"""
import argparse
import importlib.util
import os

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gen", os.path.join(HERE, "demo-door-generator.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

FRAME_RGB = np.array([0.93, 0.91, 0.86])
DOOR_RGB = np.array([0.78, 0.22, 0.20])


def swing(mesh, open_deg):
    """Door at an opening angle: 180 is the print pose, 0 is closed."""
    R = trimesh.transformations.rotation_matrix(np.radians(180 - open_deg), [1, 0, 0], [0, 0, gen.AX_Z])
    return mesh.copy().apply_transform(R)


def render(bodies, right, up, path, px_per_mm=7.0, margin=4.0, title=None):
    """Orthographic z-buffer render. bodies: list of (trimesh, rgb). right/up: view axes."""
    right, up = np.asarray(right, float), np.asarray(up, float)
    right /= np.linalg.norm(right)
    up = up - right * up.dot(right)
    up /= np.linalg.norm(up)
    toward = np.cross(right, up)
    V = np.array([right, up, toward])
    light = V.T @ np.array([-0.35, 0.55, 0.76])
    light /= np.linalg.norm(light)
    tris, cols, norms = [], [], []
    for mesh, rgb in bodies:
        t = mesh.triangles @ V.T
        n = mesh.face_normals
        keep = n @ toward > 1e-6
        lam = np.clip(n[keep] @ light, 0, 1)
        shade = 0.38 + 0.62 * lam
        tris.append(t[keep])
        cols.append(shade[:, None] * rgb[None, :])
        norms.append(n[keep] @ V.T)
    tris, cols, norms = np.vstack(tris), np.vstack(cols), np.vstack(norms)
    lo = tris[:, :, :2].reshape(-1, 2).min(0) - margin
    hi = tris[:, :, :2].reshape(-1, 2).max(0) + margin
    s = px_per_mm * 2                                    # 2x supersampling
    W, H = int(np.ceil((hi[0] - lo[0]) * s)), int(np.ceil((hi[1] - lo[1]) * s))
    zbuf = np.full((H, W), -1e9)
    img = np.ones((H, W, 3))
    nbuf = np.zeros((H, W, 3))
    P = tris.copy()
    P[:, :, 0] = (P[:, :, 0] - lo[0]) * s
    P[:, :, 1] = (hi[1] - P[:, :, 1]) * s
    for i in range(len(P)):
        (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = P[i]
        xa, xb = int(max(np.floor(min(x0, x1, x2)), 0)), int(min(np.ceil(max(x0, x1, x2)), W - 1))
        ya, yb = int(max(np.floor(min(y0, y1, y2)), 0)), int(min(np.ceil(max(y0, y1, y2)), H - 1))
        if xb < xa or yb < ya:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        xs = np.arange(xa, xb + 1) + 0.5
        ys = np.arange(ya, yb + 1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        a = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
        b = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
        c = 1 - a - b
        z = a * z0 + b * z1 + c * z2
        sub = zbuf[ya:yb + 1, xa:xb + 1]
        m = (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9) & (z > sub)
        if m.any():
            sub[m] = z[m]
            img[ya:yb + 1, xa:xb + 1][m] = cols[i]
            nbuf[ya:yb + 1, xa:xb + 1][m] = norms[i]
    # outlines where depth jumps or the surface turns sharply
    edge = np.zeros((H, W), bool)
    for ax in (0, 1):
        dz = np.abs(np.diff(zbuf, axis=ax))
        dn = 1 - (np.take(nbuf, range(1, nbuf.shape[ax]), axis=ax) * np.take(nbuf, range(0, nbuf.shape[ax] - 1), axis=ax)).sum(-1)
        e = (dz > 0.25) | (dn > 0.25)
        if ax == 0:
            edge[1:, :] |= e
        else:
            edge[:, 1:] |= e
    img[edge] *= 0.35
    img = img.reshape(H // 2, 2, W // 2, 2, 3).mean((1, 3)) if H % 2 == 0 and W % 2 == 0 else img[:H - H % 2, :W - W % 2].reshape(H // 2, 2, W // 2, 2, 3).mean((1, 3))
    fig = plt.figure(figsize=(img.shape[1] / 100.0, img.shape[0] / 100.0 + (0.4 if title else 0)), dpi=100)
    ax = fig.add_axes([0, 0, 1, img.shape[0] / (img.shape[0] + (40 if title else 0))])
    ax.imshow(np.clip(img, 0, 1))
    ax.axis("off")
    if title:
        fig.suptitle(title, fontsize=11)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    print("wrote", path)


def section_plot(ax, bodies, origin, normal, axes, title, xlim=None, ylim=None):
    from matplotlib.path import Path
    for mesh, rgb in bodies:
        sec = mesh.section(plane_origin=origin, plane_normal=normal)
        if sec is None:
            continue
        loops = [e[:, list(axes)] for e in sec.discrete if len(e) >= 3]
        # even-odd nesting: a loop inside an odd number of others is a hole
        depth = [sum(Path(o).contains_point(l[0] * 0.5 + l[1] * 0.5 + 1e-7) for j, o in enumerate(loops) if j != i) for i, l in enumerate(loops)]
        for d, l in sorted(zip(depth, loops), key=lambda t: t[0]):
            ax.fill(l[:, 0], l[:, 1], facecolor=tuple(rgb) if d % 2 == 0 else "white", edgecolor="k", linewidth=0.6)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, linewidth=0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()
    name = os.path.join(args.out, "demo-door-rev%d-" % gen.REV)
    fm, dm = gen.build(True)
    frame, door = gen.to_trimesh(fm), gen.to_trimesh(dm)
    fc, dc = (frame, FRAME_RGB), (door, DOOR_RGB)

    # 1. the plate as printed, from above
    render([fc, dc], [0, -1, 0], [1, 0, 0], name + "print-pose-top.png", px_per_mm=6,
           title="Print pose from above (bed = frame front face; door printed open 180 deg, front face up)")
    t = np.array([0.5, -0.6, 0.8])
    r = np.cross([0, 0, 1.0], t)
    render([fc, dc], r, np.cross(t, r), name + "print-pose-iso.png", px_per_mm=6,
           title="Print pose, oblique")
    # 2./3. standing on its sill: right = +y, up = +x, viewer in front (-z)
    t = np.array([0.35, 0.5, -1.0])                      # from the scene toward the camera
    r = np.array([0.0, 1.0, 0.5])
    u = np.cross(t, r)
    render([fc, (swing(door, 0), DOOR_RGB)], r, u, name + "standing-closed.png", title="Standing, door closed")
    render([fc, (swing(door, 100), DOOR_RGB)], r, u, name + "standing-open-100.png", title="Standing, door open 100 deg")
    render([fc, (swing(door, 0), DOOR_RGB)], [0, 1, 0], [1, 0, 0], name + "front.png", title="Front elevation, door closed")
    render([fc, (swing(door, 100), DOOR_RGB)], np.array([0.0, -1.0, -0.35]), np.cross([0.45, -0.35, 1.0], [0.0, -1.0, -0.35]), name + "back-open-100.png",
           title="From behind, door open 100 deg: stop rib on the latch wall, wire pocket, zip-tie slots")

    # 4. sections through the hinge
    kc = gen.KNUCKLE_C[0]
    xg = kc - gen.KNUCKLE_L / 2 - gen.FLAT_GAP / 2
    xt = (gen.KNUCKLE_C[0] + gen.KNUCKLE_C[1]) / 2
    fig, axs = plt.subplots(2, 3, figsize=(17, 10))
    lim = dict(xlim=(-13, 13), ylim=(-9, 24))
    section_plot(axs[0, 0], [fc, dc], [kc, 0, 0], [1, 0, 0], (1, 2), "PRINT POSE: section across a door knuckle (y, z)", **lim)
    section_plot(axs[0, 1], [fc, dc], [xt, 0, 0], [1, 0, 0], (1, 2), "PRINT POSE: section across a frame knuckle (y, z)", **lim)
    section_plot(axs[0, 2], [fc, dc], [0, 0, gen.AX_Z], [0, 0, 1], (0, 1),
                 "Section through the hinge axis (x, y): cones, z = %.2f" % gen.AX_Z, xlim=(xg - 7, xg + 7), ylim=(-8, 8))
    cl = (swing(door, 0), DOOR_RGB)
    section_plot(axs[1, 0], [fc, cl], [kc, 0, 0], [1, 0, 0], (1, 2), "CLOSED: section across a door knuckle", **lim)
    section_plot(axs[1, 1], [fc, cl], [xt, 0, 0], [1, 0, 0], (1, 2), "CLOSED: section across a frame knuckle", **lim)
    section_plot(axs[1, 2], [fc, cl], [xt, 0, 0], [1, 0, 0], (1, 2), "CLOSED: latch side with the 45 deg door stop",
                 xlim=(gen.Y_DL - 9, gen.Y_DL + 15), ylim=(-3, 22))
    for a in axs.flat:
        a.axhline(0, color="tab:blue", linewidth=0.8, linestyle="--")
    fig.suptitle("Hinge sections (dashed line = bed / frame front face). Cone gap %.3f mm square to the face, %.2f along the axis"
                 % (gen.CONE_AXIAL_GAP / np.sqrt(2), gen.CONE_AXIAL_GAP), fontsize=11)
    fig.tight_layout()
    fig.savefig(name + "hinge-sections.png", dpi=95)
    plt.close(fig)
    print("wrote", name + "hinge-sections.png")

    # 5. section through the switch and magnet bores (closed)
    fig, axs = plt.subplots(1, 2, figsize=(15, 7))
    section_plot(axs[0], [fc, cl], [0, gen.Y_SW, 0], [0, 1, 0], (0, 2),
                 "CLOSED: section along the switch / magnet axis (x, z), y = %.1f" % gen.Y_SW,
                 xlim=(gen.X_D1 - 36, gen.H_TOTAL + 2), ylim=(-3, 30))
    section_plot(axs[1], [fc, cl], [gen.X_HEAD + 12, 0, 0], [1, 0, 0], (1, 2), "Section across the switch bore in the header (y, z)",
                 xlim=(gen.Y_SW - 12, gen.Y_SW + 12), ylim=(-2, 16))
    fig.tight_layout()
    fig.savefig(name + "switch-sections.png", dpi=95)
    plt.close(fig)
    print("wrote", name + "switch-sections.png")


if __name__ == "__main__":
    main()
