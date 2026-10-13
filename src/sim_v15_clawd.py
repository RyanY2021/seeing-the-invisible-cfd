"""V15/V17: 2D flow past a Clawd-shaped obstacle (the banner sprite as the solid), starting from rest.
The inflow carries horizontal dye stripes (values cycling through the paint palette) that marble into a
Kármán vortex street behind Clawd. Same physical setup at several resolutions (V17: coarse vs fine).

  python sim_v15_clawd.py [res_div] [nframes]     res_div 1 = 2048x768 (V15), 4 = 512x192, 16 = 128x48
Writes cache/v2/v15_r<div>/c_####.npy (float16 dye) + meta.npz (step count per frame).
"""
import sys
import time

import numpy as np

from common import cache_dir, init_warp

wp = init_warp()
from lbm2d import LBM2D, Scalar  # noqa: E402

DIV = int(sys.argv[1]) if len(sys.argv) > 1 else 1
NFRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 432
NX, NY = 2048 // DIV, 768 // DIV
S = 8.0 / DIV                          # lattice cells per sprite pixel (width); sprite pixels are 1:2
U = 0.08
RE = 220.0
CX = 0.24 * NX                         # Clawd's centre
CY = NY / 2
STEPS_PER_FRAME_FINE = 96              # fine grid; coarser grids take proportionally fewer (same physical time)
OUT = cache_dir(f"v2/v15_r{DIV}")

SPRITE = ["   ############   ",
          "   ##.######.##   ",
          " ################ ",
          "   ############   ",
          "    # #    # #    "]


def clawd_mask():
    yy, xx = np.mgrid[0:NY, 0:NX]
    m = np.zeros((NY, NX), bool)
    w_px, h_px = S, 2 * S
    x0 = CX - 9 * w_px
    y_top = CY + 2.5 * h_px                 # sprite row 0 at the top (lattice y grows upward in the shader view)
    for r, row in enumerate(SPRITE):
        for c, ch in enumerate(row):
            if ch == "#":
                xa, xb = x0 + c * w_px, x0 + (c + 1) * w_px
                ya, yb = y_top - (r + 1) * h_px, y_top - r * h_px
                m |= (xx + 0.5 >= xa) & (xx + 0.5 < xb) & (yy + 0.5 >= ya) & (yy + 0.5 < yb)
    return m


@wp.kernel
def k_inlet_stripes(c: wp.array2d(dtype=float), x1: int, band: float, phase: float):
    y, x = wp.tid()
    if x >= x1:
        return
    k = int(wp.floor((float(y) + phase) / band))
    v = 0.12 + 0.18 * float(((k % 5) + 5) % 5)          # 0.12, 0.30, 0.48, 0.66, 0.84 (palette bands)
    c[y, x] = v


def main():
    mask = clawd_mask()
    h_obst = 10 * S                                     # Clawd's height in cells
    nu = U * h_obst / RE
    sim = LBM2D(NX, NY, nu, solid=mask.astype(np.uint8), periodic_y=True, csmag=0.06 if DIV == 1 else 0.1)
    yy = np.arange(NY)[:, None] * np.ones((1, NX))
    band = NY / 14.0
    c0 = 0.12 + 0.18 * (np.floor(yy / band) % 5)
    C = Scalar(sim, c0.astype(np.float32))
    spf = max(1, STEPS_PER_FRAME_FINE // DIV)
    t0 = time.time()
    step = 0
    steps = []
    for f in range(NFRAMES):
        for _ in range(spf):
            ramp = min(1.0, step / (1500 / DIV))
            kick = 0.06 * U * np.sin(np.pi * (step - 3000 / DIV) / (3000 / DIV)) if 3000 / DIV < step < 6000 / DIV else 0.0
            sim.step(U * ramp, kick)
            C.advect(1.0)
            wp.launch(k_inlet_stripes, dim=(NY, NX), inputs=[C.c, max(2, 8 // DIV), float(band), 0.0], device=sim.device)
            step += 1
        np.save(OUT / f"c_{f:04d}.npy", C.numpy().astype(np.float16))
        steps.append(step)
        if f % 48 == 0:
            print(f"div {DIV} frame {f} step {step} {time.time() - t0:.0f}s", flush=True)
    np.savez(OUT / "meta.npz", steps=np.array(steps), mask=mask, cx=CX, cy=CY, s=S)
    print("done", time.time() - t0)


if __name__ == "__main__":
    main()
