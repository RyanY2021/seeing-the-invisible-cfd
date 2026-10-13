"""V19 polaroid pictures: one turbulent moment of the KH shear layer seen three ways, shaded as glossy paint.
  DNS  = the full field (every swirl)
  LES  = spatially filtered (big swirls sharp, the small ones smeared = 'estimated')
  RANS = time-averaged over many frames (just the average)
Writes cache/v2/v19/{dns,les,rans}.exr (1200x900, scene-linear) and the live 'scene' texture.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import OpenEXR

sys.path.insert(0, str(Path(__file__).parent))
import paint25d  # noqa: E402
from common import CACHE, cache_dir  # noqa: E402

SRC = CACHE / "s08"
OUT = cache_dir("v2/v19")
F = 320
CX, CY, CW = 2250, 1180, 1500                # crop (sim px) around a mature billow pair
CH = CW * 3 // 4


def crop(c):
    return cv2.resize(c[CY - CH // 2:CY + CH // 2, CX - CW // 2:CX + CW // 2], (1200, 900), interpolation=cv2.INTER_AREA)


def write(path, lin):
    OpenEXR.File({"type": OpenEXR.scanlineimage, "compression": OpenEXR.ZIP_COMPRESSION},
                 {"RGB": lin.astype(np.float16)}).write(str(path))


def main():
    dns = np.load(SRC / f"c_{F:04d}.npy").astype(np.float32)
    les = cv2.GaussianBlur(dns, (0, 0), 14)
    rans = np.mean([np.load(SRC / f"c_{k:04d}.npy").astype(np.float32) for k in range(200, 336, 3)], axis=0)
    rans = np.repeat(rans.mean(axis=1, keepdims=True), rans.shape[1], axis=1)   # homogeneous along the flow
    for name, c in (("dns", dns), ("les", les), ("rans", rans)):
        lin = paint25d.shade(np.clip(crop(c), 0, 1), relief=4.0, undul=0.0004)
        write(OUT / f"{name}.exr", lin)
        print(name, lin.shape)


if __name__ == "__main__":
    main()
