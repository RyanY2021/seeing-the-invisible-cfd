"""S07 — the same cylinder wake on a coarse, medium and fine grid (vorticity, cells visible).

python shot_s07_resolution.py sim     -> cache/s07/<level>_####.npy
python shot_s07_resolution.py render  -> renders/S07/####.png
"""
from __future__ import annotations

import sys
import time

import numpy as np

from common import H, W, cache_dir, save_png16, shot_dir

LEVELS = [("coarse", 5), ("medium", 16), ("fine", 64)]  # cylinder diameter in cells
LX, LY = 30.0, 12.0  # domain size in diameters
XC = 6.0  # cylinder centre (diameters from inlet)
U = 0.08
RE = 150.0
NFRAMES = 240
WARM = 110.0  # warm-up in D/U
DT_FRAME = 0.11  # convective times per frame
STRIP_H = 336
VIEW = (-1.8, 18.2)  # x range shown, diameters relative to cylinder centre


def sim():
    from lbm2d import LBM2D, cylinder_mask

    out = cache_dir("s07")
    for name, D in LEVELS:
        nx, ny = int(LX * D), int(LY * D)
        nu = U * D / RE
        cx, cy = XC * D, ny / 2 + 0.5 * (D / 16)
        s = LBM2D(nx, ny, nu, solid=cylinder_mask(nx, ny, cx, cy, D / 2), periodic_y=True, csmag=0.0)
        np.save(out / f"{name}_solid.npy", cylinder_mask(nx, ny, cx, cy, D / 2))
        steps_per_unit = D / U
        t0 = time.time()
        warm = int(WARM * steps_per_unit)
        for k in range(warm):
            vin = 0.08 * U * np.sin(np.pi * (k - 1500) / 1500) if 1500 < k < 3000 else 0.0
            s.step(U * min(1.0, k / 1000), vin)
        for f in range(NFRAMES):
            s.step(U, 0.0, n=max(1, int(round(DT_FRAME * steps_per_unit))))
            np.save(out / f"{name}_{f:04d}.npy", (s.vorticity() * D / U).astype(np.float16))
        print(name, nx, ny, "done", time.time() - t0, flush=True)


def icefire(v):
    """Dark-centred diverging colormap: cyan-blue (neg) / black / orange-amber (pos). v in [-1, 1]."""
    stops = np.array([-1.0, -0.55, -0.2, 0.0, 0.2, 0.55, 1.0])
    cols = np.array([[0.78, 0.96, 1.00], [0.20, 0.55, 0.95], [0.06, 0.16, 0.38], [0.015, 0.016, 0.022],
                     [0.40, 0.09, 0.07], [0.95, 0.38, 0.12], [1.00, 0.88, 0.62]], np.float32)
    v = np.clip(v, -1, 1)
    out = np.zeros(v.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(v, stops, cols[:, c])
    return out


def render(first=0, last=NFRAMES):
    import cv2

    from look import bloom, filmic, gblur, vignette
    from textfx import FONT_LABEL, paste, text_layer

    src = cache_dir("s07")
    dst = shot_dir("S07")
    gap = (H - 3 * STRIP_H) // 4
    labels = []
    cost = {"coarse": "computed in 0.8 s", "medium": "computed in 2.7 s", "fine": "computed in 3 min 25 s"}
    for name, D in LEVELS:
        cells = int(LX * D) * int(LY * D)
        labels.append((text_layer(name.upper(), 24, FONT_LABEL, tracking=0.32, color=(0.92, 0.92, 0.95)),
                       text_layer(f"{cells:,} cells  ·  {cost[name]}", 21, FONT_LABEL, tracking=0.10,
                                  color=(0.62, 0.66, 0.72))))
    vig = vignette(H, W, 0.3)
    for f in range(first, last):
        canvas = np.full((H, W, 3), 0.008, np.float32)
        for li, (name, D) in enumerate(LEVELS):
            w = np.load(src / f"{name}_{f:04d}.npy").astype(np.float32)
            solid = np.load(src / f"{name}_solid.npy")
            ny, nx = w.shape
            cx, cy = XC * D, ny / 2
            x0, x1 = cx + VIEW[0] * D, cx + VIEW[1] * D
            ppc = W / (x1 - x0)  # pixels per cell
            hh = STRIP_H / ppc  # strip height in cells
            y0 = cy - hh / 2
            # nearest-neighbour sampling -> visible cells
            px = np.arange(W) / ppc + x0
            py = (np.arange(STRIP_H)[::-1] + 0.5) / ppc + y0
            ix = np.clip(np.floor(px).astype(int), 0, nx - 1)
            iy = np.clip(np.floor(py).astype(int), 0, ny - 1)
            sub = w[np.ix_(iy, ix)]
            sol = solid[np.ix_(iy, ix)]
            col = icefire(sub / 3.6) * 1.1
            col = np.where(sol[..., None] > 0, np.array([0.30, 0.31, 0.33], np.float32), col)
            # cell edges
            if ppc >= 3.0:
                fx = (px - np.floor(px))[None, :]
                fy = (py - np.floor(py))[:, None]
                ew = 1.0 / ppc
                edge = ((fx < ew) | (fy < ew)).astype(np.float32)
                strength = 0.22 if ppc > 10 else 0.10
                col = col * (1 - strength * edge[..., None]) + strength * 0.35 * edge[..., None]
            ys = gap + li * (STRIP_H + gap)
            canvas[ys:ys + STRIP_H] = col
            # thin frame lines
            canvas[ys - 1, :] = canvas[ys - 1, :] * 0.5 + 0.08
            canvas[ys + STRIP_H, :] = canvas[ys + STRIP_H, :] * 0.5 + 0.08
            lab, sub_lab = labels[li]
            # label plate (soft dark) for legibility
            canvas[ys + 14:ys + 84, 28:448] *= 0.45
            paste(canvas, lab, 46, ys + 22)
            paste(canvas, sub_lab, 46, ys + 52)
        rgb = bloom(canvas, threshold=0.55, strength=0.2, sigmas=(4, 12, 30))
        rgb = filmic(rgb * vig, exposure=1.25)
        save_png16(dst / f"{f:04d}.png", rgb)
        if f % 48 == 0:
            print("render", f, flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("sim", "all"):
        sim()
    if mode in ("render", "all"):
        render()
