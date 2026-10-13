"""V16 — emergence + reality check. Part A: full-frame glossy-paint view of the simulated vortex street behind
the pixel-Clawd, slow push along the street ("Nobody told the computer to make swirls…"). Part B: dissolve into
the real thing — Landsat 7 clouds behind Alejandro Selkirk Island (NASA, public domain), rotated so the island
sits where Clawd was and the street runs the same way ("And nature agrees").
Writes scene-linear EXR frames to renders/V16/.

  python shot_v16.py [first] [last]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import OpenEXR

sys.path.insert(0, str(Path(__file__).parent))
import paint25d  # noqa: E402
from common import ASSETS, CACHE, RENDERS, smoothstep  # noqa: E402

W, H = 1920, 1080
N = 6 * 48 + 24
XF0, XF1 = 138, 176                       # the dissolve (bar 76.9 = frame 138)
SIM = CACHE / "v2" / "v15_r1"
OUT = RENDERS / "V16"
OUT.mkdir(parents=True, exist_ok=True)
ORANGE = np.array([0.72, 0.15, 0.055], np.float32) * 1.6

sat = cv2.imread(str(ASSETS / "nasa_vortex" / "Vortex-street-1.jpg"), cv2.IMREAD_GRAYSCALE)
sat = cv2.rotate(sat, cv2.ROTATE_90_CLOCKWISE).astype(np.float32) / 255.0       # 4574 x 2549, island at left
sat_lin = np.where(sat <= 0.04045, sat / 12.92, ((sat + 0.055) / 1.055) ** 2.4)
mask = np.flipud(np.load(SIM / "meta.npz")["mask"])


def write_exr(path, lin):
    OpenEXR.File({"type": OpenEXR.scanlineimage, "compression": OpenEXR.DWAA_COMPRESSION},
                 {"RGB": lin.astype(np.float16)}).write(str(path))


def window(img, cx, cy, w):
    """crop a 16:9 window (centre cx, cy, width w in source px) and resample to 1920x1080"""
    h = w * 9 / 16
    M = np.float32([[W / w, 0, -(cx - w / 2) * W / w], [0, H / h, -(cy - h / 2) * H / h]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def part_a(f):
    k = min(280 + f, 431)
    c = np.flipud(np.load(SIM / f"c_{k:04d}.npy").astype(np.float32))
    c = cv2.resize(c, (3072, 1152), interpolation=cv2.INTER_CUBIC)
    m = cv2.resize(mask.astype(np.uint8), (3072, 1152), interpolation=cv2.INTER_NEAREST).astype(bool)
    lin = paint25d.shade(np.clip(c, 0, 1))
    lin[m] = ORANGE
    t = smoothstep(0, XF1, f)
    # push along the street: from the pixel-Clawd towards the vortices
    return window(lin, 0.24 * 3072 + 700 + 500 * t, 1152 / 2, 2200 - 400 * t)


def part_b(f):
    t = smoothstep(XF0 - 20, N + 40, f)
    # opens wide with the island at the left (where the pixel-Clawd was), then drifts in along the street
    img = window(sat_lin, 2050 + 700 * t, 1050 + 80 * t, 4000 - 1300 * t)
    tint = np.array([0.92, 0.97, 1.08], np.float32)          # cool daylight, a hint of the film's violet
    return img[..., None] * tint * 0.9


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    last = int(sys.argv[2]) if len(sys.argv) > 2 else N
    for f in range(first, last + 1):
        p = OUT / f"{f:04d}.exr"
        if p.exists():
            continue
        if f < XF0:
            lin = part_a(f)
        elif f >= XF1:
            lin = part_b(f)
        else:
            w = smoothstep(XF0, XF1, f)
            lin = part_a(f) * (1 - w) + part_b(f) * w
        write_exr(p, lin)
        if f % 48 == 0:
            print("V16", f, flush=True)


if __name__ == "__main__":
    main()
