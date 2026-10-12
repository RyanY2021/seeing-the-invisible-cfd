"""Procedural light aircraft (low wing, ~12 m span) as an implicit surface -> PLY meshes for S10.

Frame: x forward (flight direction, nose at +x), y to port (left), z up. Origin at wing root quarter-chord.
  python plane_sdf.py  -> cache/plane/plane_body.ply, plane_canopy.ply
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator

from car_sdf import grid_eval, smax, smin, write_ply
from common import cache_dir

SEMI = 6.0


def _p(xs, ys):
    f = PchipInterpolator(np.array(xs), np.array(ys))
    return lambda x: f(np.clip(x, xs[0], xs[-1]))


# fuselage: radius (half-width) and half-height along x, centre-line height
fx = [-5.2, -4.6, -3.0, -1.0, 0.5, 1.6, 2.4, 2.95, 3.15]
fus_w = _p(fx, [0.06, 0.14, 0.32, 0.52, 0.60, 0.60, 0.52, 0.36, 0.10])
fus_h = _p(fx, [0.10, 0.22, 0.40, 0.62, 0.75, 0.72, 0.58, 0.40, 0.12])
fus_z = _p(fx, [0.55, 0.50, 0.38, 0.30, 0.32, 0.30, 0.25, 0.20, 0.18])


def naca(xc, t=0.13, m=0.03, p=0.4):
    xc = np.clip(xc, 0, 1)
    yt = 5 * t * (0.2969 * np.sqrt(xc) - 0.1260 * xc - 0.3516 * xc ** 2 + 0.2843 * xc ** 3 - 0.1036 * xc ** 4)
    yc = np.where(xc < p, m / p ** 2 * (2 * p * xc - xc ** 2), m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * xc - xc ** 2))
    return yt, yc


def lifting_surface(x, y, z, semi, c_root, c_tip, x_le_root, sweep, dihedral, z0, t=0.13, m=0.03, axis="z"):
    """Implicit for a tapered wing. axis='z' horizontal surface, 'y' vertical fin (span along z)."""
    if axis == "z":
        s = np.abs(y)
        h = z
    else:
        s = z - z0
        h = y
    sn = np.clip(s / semi, 0, 1)
    c = c_root + (c_tip - c_root) * sn
    xle = x_le_root - sweep * s
    xc = (xle - x) / c
    yt, yc = naca(xc, t, m)
    hz = (z0 + dihedral * s) if axis == "z" else 0.0
    d_th = np.abs(h - hz - yc * c) - yt * c
    d_ch = np.maximum(-xc, xc - 1) * c
    d = np.maximum(d_th, d_ch * 0.5)
    tip = (s - semi) if axis == "z" else np.maximum(s - semi, -s)
    d = smax(d, tip, 0.06)
    return d


def body_sdf(x, y, z):
    w = np.maximum(fus_w(x), 1e-3)
    hh = np.maximum(fus_h(x), 1e-3)
    zc = fus_z(x)
    g = ((np.abs(y) / w) ** 2.4 + (np.abs(z - zc) / hh) ** 2.4) ** (1 / 2.4) - 1
    d = g * np.minimum(w, hh)
    d = smax(d, x - 3.15, 0.15)
    d = smax(d, -5.2 - x, 0.1)
    wing = lifting_surface(x, y, z, SEMI, 1.75, 1.05, 0.55, 0.06, 0.07, 0.0, t=0.14)
    d = smin(d, wing, 0.10)
    ht = lifting_surface(x, y, z, 1.8, 0.95, 0.6, -3.9, 0.15, 0.0, 0.48, t=0.10, m=0.0)
    d = smin(d, ht, 0.06)
    vt = lifting_surface(x, y, z, 1.45, 1.25, 0.65, -3.75, 0.45, 0.0, 0.55, t=0.10, m=0.0, axis="y")
    d = smin(d, vt, 0.06)
    # spinner
    sp = np.sqrt(((x - 3.25) / 0.32) ** 2 + (y / 0.16) ** 2 + ((z - 0.18) / 0.16) ** 2) - 1
    d = smin(d, sp * 0.16, 0.04)
    return d


def canopy_sdf(x, y, z):
    g = np.sqrt(((x - 0.75) / 1.25) ** 2 + (y / 0.46) ** 2 + ((z - 0.92) / 0.42) ** 2) - 1
    return smax(g * 0.42, 0.95 - z - 0.02, 0.03)


if __name__ == "__main__":
    from skimage.measure import marching_cubes

    out = cache_dir("plane")
    for name, fn, h in (("plane_body", body_sdf, 0.022), ("plane_canopy", canopy_sdf, 0.02)):
        vol, (xs, ys, zs) = grid_eval(fn, (-5.4, -SEMI - 0.3, -0.7), (3.7, SEMI + 0.3, 2.3), h)
        v, f, n, _ = marching_cubes(vol, 0.0, spacing=(h, h, h))
        v = v + np.array([xs[0], ys[0], zs[0]])
        write_ply(out / f"{name}.ply", v, f[:, ::-1])
        print(name, len(v), len(f))
