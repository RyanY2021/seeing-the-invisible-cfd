"""Procedural clay-model sports coupe as an implicit surface (approximate SDF, metres).

Car frame: x along the length (nose at x=0, tail at x=L), y lateral, z up, ground at z=0.
  python car_sdf.py mesh   -> cache/car/car_body.ply, car_wheels.ply  (marching cubes)
Used by: S11 LBM wind tunnel (solid mask) and Blender shots S04/S11.
"""
from __future__ import annotations

import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

from common import cache_dir

L = 4.50
WHEELS_X = (0.92, 3.58)
WHEEL_R = 0.335
WHEEL_W = 0.245
WHEEL_Y = 0.80
WHEEL_Z = 0.335


def _p(xs, ys):
    f = PchipInterpolator(np.array(xs), np.array(ys), extrapolate=True)
    return lambda x: f(np.clip(x, xs[0], xs[-1]))


# side profile (z) of the lower body top edge (belt / hood / deck)
belt = _p([0.00, 0.10, 0.35, 0.80, 1.40, 2.20, 3.30, 3.95, 4.38, 4.50],
          [0.44, 0.55, 0.66, 0.75, 0.82, 0.87, 0.92, 0.95, 0.94, 0.86])
# underside
bottom = _p([0.00, 0.12, 0.40, 1.0, 3.6, 4.15, 4.50], [0.34, 0.22, 0.165, 0.15, 0.15, 0.21, 0.38])
# half-width of the lower body
halfw = _p([0.00, 0.08, 0.30, 0.75, 1.40, 2.60, 3.50, 4.20, 4.45, 4.50],
           [0.42, 0.62, 0.80, 0.90, 0.93, 0.94, 0.94, 0.90, 0.80, 0.64])
# roof line (cabin top)
roof = _p([1.30, 1.55, 1.95, 2.35, 2.75, 3.15, 3.60, 4.05, 4.30],
          [0.86, 0.98, 1.17, 1.27, 1.285, 1.24, 1.13, 1.00, 0.95])
cab_hw = _p([1.30, 1.70, 2.30, 2.90, 3.50, 4.10, 4.30], [0.66, 0.70, 0.71, 0.70, 0.66, 0.56, 0.46])


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def body_sdf(x, y, z):
    # lower body: lofted superellipse (n=4) in the y-z plane
    zb, zt = bottom(x), belt(x)
    zc = 0.5 * (zb + zt)
    hb = np.maximum(0.5 * (zt - zb), 1e-3)
    hw = np.maximum(halfw(x), 1e-3)
    n = 4.0
    u = np.abs(y) / hw
    v = np.abs(z - zc) / hb
    g = (u ** n + v ** n) ** (1 / n) - 1
    d_low = g * np.minimum(hw, hb)
    # end caps (nose / tail) via smooth intersection with the x-range
    d_low = smax(d_low, -x + 0.0, 0.12)
    d_low = smax(d_low, x - L, 0.10)
    # cabin: superellipse (n=3) whose top follows the roof line, sides with tumblehome
    xr = np.clip(x, 1.30, 4.30)
    zr = roof(xr)
    zcb = zt - 0.18
    zcc = 0.5 * (zr + zcb)
    hcz = np.maximum(0.5 * (zr - zcb), 1e-3)
    t = np.clip((z - zcb) / np.maximum(zr - zcb, 1e-3), 0, 1)
    hcw = cab_hw(xr) * (1 - 0.22 * t ** 2)
    u2 = np.abs(y) / hcw
    v2 = np.abs(z - zcc) / hcz
    g2 = (u2 ** 3 + v2 ** 3) ** (1 / 3) - 1
    d_cab = g2 * np.minimum(hcw, hcz)
    d_cab = smax(d_cab, 1.30 - x, 0.25)
    d_cab = smax(d_cab, x - 4.30, 0.15)
    d = smin(d_low, d_cab, 0.10)
    # wheel arches cut into the body sides
    for xw in WHEELS_X:
        r = np.sqrt((x - xw) ** 2 + (z - WHEEL_Z) ** 2)
        arch = smax(r - (WHEEL_R + 0.045), 0.52 - np.abs(y), 0.02)
        d = smax(d, -arch, 0.035)
    return d


def wheels_sdf(x, y, z):
    d = np.full(np.shape(x), 1e3)
    for xw in WHEELS_X:
        r = np.sqrt((x - xw) ** 2 + (z - WHEEL_Z) ** 2)
        for side in (-1, 1):
            dy = np.abs(y - side * WHEEL_Y) - WHEEL_W / 2
            dr = r - WHEEL_R
            q = np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dy, 0) ** 2) + np.minimum(np.maximum(dr, dy), 0)
            d = np.minimum(d, q - 0.035)
    return d


def car_sdf(x, y, z):
    return np.minimum(body_sdf(x, y, z), wheels_sdf(x, y, z))


def grid_eval(fn, lo, hi, h):
    xs = np.arange(lo[0], hi[0] + h, h)
    ys = np.arange(lo[1], hi[1] + h, h)
    zs = np.arange(lo[2], hi[2] + h, h)
    out = np.empty((len(xs), len(ys), len(zs)), np.float32)
    for i in range(0, len(xs), 32):
        X, Y, Z = np.meshgrid(xs[i:i + 32], ys, zs, indexing="ij")
        out[i:i + 32] = fn(X, Y, Z)
    return out, (xs, ys, zs)


def write_ply(path, verts, faces):
    with open(path, "wb") as fh:
        hdr = (f"ply\nformat binary_little_endian 1.0\nelement vertex {len(verts)}\nproperty float x\nproperty float y\n"
               f"property float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n")
        fh.write(hdr.encode())
        fh.write(verts.astype("<f4").tobytes())
        fa = np.empty((len(faces),), dtype=[("n", "u1"), ("i", "<i4", (3,))])
        fa["n"] = 3
        fa["i"] = faces
        fh.write(fa.tobytes())


def glass_mask(v, n):
    """Per-vertex 0..1 'glass' weight (windscreen, side and rear windows); roof panel and pillars stay clay."""
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    nz = np.abs(n[:, 2])
    bz = belt(x)
    xr = np.clip(x, 1.30, 4.30)
    rz = roof(xr)
    hw = cab_hw(xr)
    roof_panel = (x > 2.12) & (x < 3.30) & (nz > 0.80)
    ws = (x > 1.44) & (x < 2.20) & (z > bz + 0.035) & (np.abs(y) < 0.80 * hw)
    sw = (x > 1.80) & (x < 3.50) & (z > bz + 0.055) & (z < rz - 0.06) & (nz < 0.72)
    rw = (x > 3.32) & (x < 4.12) & (z > bz + 0.05) & (np.abs(y) < 0.70 * hw) & (nz > 0.25)
    g = (ws | sw | rw) & ~roof_panel
    return g.astype(np.float32)


def write_ply_rgb(path, verts, faces, rgb):
    with open(path, "wb") as fh:
        hdr = "\n".join(["ply", "format binary_little_endian 1.0", f"element vertex {len(verts)}",
                         "property float x", "property float y", "property float z", "property uchar red",
                         "property uchar green", "property uchar blue", f"element face {len(faces)}",
                         "property list uchar int vertex_indices", "end_header", ""])
        fh.write(hdr.encode())
        va = np.empty((len(verts),), dtype=[("p", "<f4", (3,)), ("c", "u1", (3,))])
        va["p"] = verts
        va["c"] = rgb
        fh.write(va.tobytes())
        fa = np.empty((len(faces),), dtype=[("n", "u1"), ("i", "<i4", (3,))])
        fa["n"] = 3
        fa["i"] = faces
        fh.write(fa.tobytes())


def mesh(h=0.012):
    from skimage.measure import marching_cubes

    out = cache_dir("car")
    for name, fn in (("car_body", body_sdf), ("car_wheels", wheels_sdf)):
        vol, (xs, ys, zs) = grid_eval(fn, (-0.08, -1.05, 0.0), (L + 0.08, 1.05, 1.42), h)
        v, f, nrm, _ = marching_cubes(vol, 0.0, spacing=(h, h, h))
        v = v + np.array([xs[0], ys[0], zs[0]])
        f = f[:, ::-1]  # outward winding
        if name == "car_body":
            g = glass_mask(v, -nrm)
            # smooth the mask over the mesh (vertex adjacency) so window edges are clean curves
            import scipy.sparse as sp

            nv = len(v)
            rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]])
            cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]])
            A = sp.coo_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(nv, nv)).tocsr()
            A = A + sp.identity(nv, dtype=np.float32, format="csr")
            dinv = sp.diags(1.0 / np.asarray(A.sum(axis=1)).ravel())
            A = dinv @ A
            for _ in range(6):
                g = A @ g
            rgb = np.stack([g * 255, np.zeros_like(g), np.zeros_like(g)], -1).astype(np.uint8)
            write_ply_rgb(out / f"{name}.ply", v, f, rgb)
        else:
            write_ply(out / f"{name}.ply", v, f)
        print(name, len(v), "verts", len(f), "faces")


def solid_mask(nx, ny, nz, dx, origin):
    """Voxel mask for the LBM grid. LBM axes: x=flow(length), y=up, z=lateral; array [z, y, x].
    origin = car-frame coordinates (x, z_up, y_lat) of LBM cell (0,0,0) centre."""
    xs = origin[0] + dx * np.arange(nx)
    us = origin[1] + dx * np.arange(ny)
    ls = origin[2] + dx * np.arange(nz)
    m = np.zeros((nz, ny, nx), np.uint8)
    for k in range(nz):
        X, U = np.meshgrid(xs, us, indexing="xy")  # (ny, nx)
        Yl = np.full_like(X, ls[k])
        m[k] = (car_sdf(X, Yl, U) < 0).astype(np.uint8)
    return m


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "mesh") == "mesh":
        mesh()
