"""V18 — turbulence: the v1 Kelvin-Helmholtz shear layer (cache/s08, 3840x2160 dye) as glossy neon acrylic paint
(paint25d), slowed 1.5x (frame blending), with a slow 4x push into one billow: swirls within swirls.
Writes scene-linear EXR frames to renders/V18/.     python shot_v18.py [first] [last]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import OpenEXR

sys.path.insert(0, str(Path(__file__).parent))
import paint25d  # noqa: E402
from common import CACHE, RENDERS, smoothstep  # noqa: E402

W, H = 1920, 1080
N = 10 * 48 + 24
NX, NY, Y0 = 3840, 2160, 1180
NSIM = 336
SRC = CACHE / "s08"
OUT = RENDERS / "V18"
OUT.mkdir(parents=True, exist_ok=True)
LUT = paint25d.palette_lut(paint25d.NEON_POUR)


def load(i):
    return np.load(SRC / f"c_{int(i):04d}.npy").astype(np.float32)


def window(f):
    t = smoothstep(60, N - 10, f)
    w = NX * (1 - 0.75 * t)
    cx = NX * 0.5 + 330 * t
    cy = Y0 - 20 + 30 * t
    return cx, cy, w


def frame(f):
    s = 55 + (NSIM - 56) * (f - 1) / (N - 1)            # sim frames 55..335 over the shot
    a, b = int(np.floor(s)), min(int(np.floor(s)) + 1, NSIM - 1)
    k = s - a
    c = load(a) * (1 - k) + load(b) * k
    cx, cy, w = window(f)
    h = w * 9 / 16
    M = np.float32([[W / w, 0, -(cx - w / 2) * W / w], [0, H / h, -(cy - h / 2) * H / h]])
    crop = cv2.warpAffine(c, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    zoom = NX / w
    return paint25d.shade(np.clip(crop, 0, 1), lut=LUT, bands=2.0, relief=6.0 / zoom ** 0.5, undul=0.0004)


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    last = int(sys.argv[2]) if len(sys.argv) > 2 else N
    for f in range(first, last + 1):
        p = OUT / f"{f:04d}.exr"
        if p.exists():
            continue
        lin = frame(f)
        OpenEXR.File({"type": OpenEXR.scanlineimage, "compression": OpenEXR.DWAA_COMPRESSION},
                     {"RGB": lin.astype(np.float16)}).write(str(p))
        if f % 48 == 0:
            print("V18", f, flush=True)


if __name__ == "__main__":
    main()
