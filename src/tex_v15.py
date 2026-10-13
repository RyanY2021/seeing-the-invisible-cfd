"""Bake the Clawd-flow dye fields into glossy-paint textures (scene-linear EXR sequences for Blender).

  python tex_v15.py v15            -> cache/v2/v15_tex/####.exr   (fine sim, frames 1..408, 2048x768)
  python tex_v15.py v17            -> cache/v2/v17_tex/r{1,4,16}/####.exr  (coarse ones nearest-upscaled = pixels)
The obstacle (Clawd's silhouette) is painted as glowing orange pixels.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import OpenEXR

sys.path.insert(0, str(Path(__file__).parent))
import paint25d  # noqa: E402
from common import cache_dir  # noqa: E402

ORANGE = np.array([0.72, 0.15, 0.055], np.float32) * 1.6
W, H = 2048, 768


def write_exr(path, lin):
    OpenEXR.File({"type": OpenEXR.scanlineimage, "compression": OpenEXR.DWAA_COMPRESSION},
                 {"RGB": lin.astype(np.float16)}).write(str(path))


def shade_frame(div, f):
    src = cache_dir(f"v2/v15_r{div}")
    c = np.flipud(np.load(src / f"c_{f:04d}.npy").astype(np.float32))
    mask = np.flipud(np.load(src / "meta.npz")["mask"])
    if div > 1:
        c = cv2.resize(c, (W, H), interpolation=cv2.INTER_NEAREST)
        mask = cv2.resize(mask.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    lin = paint25d.shade(c, relief=6.0 if div == 1 else 2.0)
    lin[mask] = ORANGE
    if div > 1:   # faint pixel grid so the cells read as cells
        k = div * W // 2048
        g = np.ones((H, W), np.float32)
        g[::k, :] = 0.75
        g[:, ::k] = 0.75
        lin *= g[..., None]
    return lin


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "v15"
    if which == "v15":
        out = cache_dir("v2/v15_tex")
        for k in range(1, 409):
            p = out / f"{k:04d}.exr"
            if not p.exists():
                write_exr(p, shade_frame(1, min(k - 1 + 20, 431)))
            if k % 48 == 0:
                print("v15", k, flush=True)
    else:
        for div in (1, 4, 16):
            out = cache_dir(f"v2/v17_tex/r{div}")
            for k in range(1, 313):
                p = out / f"{k:04d}.exr"
                if not p.exists():
                    write_exr(p, shade_frame(div, min(110 + k, 431)))
            print("v17 div", div, "done", flush=True)


if __name__ == "__main__":
    main()
