"""v2 grade: scene-linear EXR -> bloom (in linear light) -> AgX tone map ('punchy') -> prismatic fringe -> vignette.

    python src/grade.py in.exr out.png [exposure_ev]      (look-dev preview)
"""
import sys

import cv2
import numpy as np
import OpenEXR

# AgX (Troy Sobotka) fit by Benjamin Wrensch; row-vector form (pixels @ M)
AGX = np.array([[0.842479062253094, 0.0423282422610123, 0.0423756549057051],
                [0.0784335999999992, 0.878468636469772, 0.0784336],
                [0.0792237451477643, 0.0791661274605434, 0.879142973793104]], np.float32)
AGX_INV = np.array([[1.19687900512017, -0.0528968517574562, -0.0529716355144438],
                    [-0.0980208811401368, 1.15190312990417, -0.0980434501171241],
                    [-0.0990297440797205, -0.0989611768448433, 1.15107367264116]], np.float32)
MIN_EV, MAX_EV = -12.47393, 4.026069


def read_exr(path):
    with OpenEXR.File(str(path)) as f:
        ch = f.channels()
        if "RGB" in ch:
            img = ch["RGB"].pixels
        elif "RGBA" in ch:
            img = ch["RGBA"].pixels[..., :3]
        else:
            img = np.dstack([ch[k].pixels for k in ("R", "G", "B")])
    return np.ascontiguousarray(img, dtype=np.float32)


def agx(lin, sat=1.25, contrast=1.0, offset=0.0):
    x = np.maximum(lin, 1e-10) @ AGX
    x = np.clip(np.log2(x), MIN_EV, MAX_EV)
    x = (x - MIN_EV) / (MAX_EV - MIN_EV)
    x2 = x * x
    x4 = x2 * x2
    y = 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232
    # look: offset / contrast / saturation (as in Blender's 'Punchy')
    y = np.clip(y + offset, 0, None) ** contrast
    luma = y @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    y = luma[..., None] + sat * (y - luma[..., None])
    y = np.clip(y, 0, None) @ AGX_INV
    return np.clip(y, 0, 1)   # display-encoded (~sRGB)


def _blur(img, sigma):
    """fast large gaussian via downsampling"""
    k = max(1, int(sigma // 6))
    if k > 1:
        small = cv2.resize(img, (img.shape[1] // k, img.shape[0] // k), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / k)
        return cv2.resize(small, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(img, (0, 0), sigma)


def bloom(lin, strength=0.08, threshold=1.0, radii=(6, 18, 48, 120), weights=(0.45, 0.3, 0.17, 0.08)):
    s = lin.shape[0] / 1080.0
    br = np.maximum(lin - threshold, 0) + 0.02 * lin
    acc = np.zeros_like(lin)
    for r, w in zip(radii, weights):
        acc += w * _blur(br, r * s)
    return lin + strength * acc


def prism(disp, amount=1.2):
    """radial RGB split (lateral chromatic aberration) growing towards the frame edges, in display space"""
    if amount <= 0:
        return disp
    h, w = disp.shape[:2]
    s = h / 1080.0
    out = disp.copy()
    for c, k in ((0, 1.0), (2, -1.0)):
        sc_ = 1.0 + k * amount * 1.0e-3 * s
        M = np.array([[sc_, 0, (1 - sc_) * w / 2], [0, sc_, (1 - sc_) * h / 2]], np.float32)
        out[..., c] = cv2.warpAffine(disp[..., c], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def vignette(disp, amount=0.22, power=2.2):
    h, w = disp.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    return disp * (1 - amount * r ** power)[..., None]


def fake_haze(lin, amount=0.3, radius=260, floor=(0.010, 0.006, 0.016)):
    """cheap stand-in for a volumetric haze: very wide glow of the lit scene + a faint coloured veil"""
    s = lin.shape[0] / 1080.0
    g = _blur(np.minimum(lin, 6.0), radius * s)
    g2 = _blur(np.minimum(lin, 6.0), radius * 0.35 * s)
    return lin + amount * (0.7 * g + 0.3 * g2) + np.asarray(floor, np.float32) * amount * 4


def grade(lin, exposure=0.0, bloom_strength=0.08, bloom_threshold=1.0, sat=1.25, contrast=1.0, ca=1.2, vig=0.22,
          tint=None, haze=0.0):
    lin = lin * (2.0 ** exposure)
    if tint is not None:
        lin = lin * np.asarray(tint, np.float32)
    if haze > 0:
        lin = fake_haze(lin, haze)
    if bloom_strength > 0:
        lin = bloom(lin, bloom_strength, bloom_threshold)
    disp = agx(lin, sat=sat, contrast=contrast)
    disp = prism(disp, ca)
    disp = vignette(disp, vig)
    return np.clip(disp, 0, 1)


def save_png(disp, path, bits=8):
    if bits == 16:
        cv2.imwrite(str(path), (disp[..., ::-1] * 65535 + 0.5).astype(np.uint16))
    else:
        cv2.imwrite(str(path), (disp[..., ::-1] * 255 + 0.5).astype(np.uint8))


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    ev = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    save_png(grade(read_exr(src), exposure=ev), dst)
