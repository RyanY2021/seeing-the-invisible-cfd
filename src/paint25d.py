"""2.5D 'glossy acrylic paint' shader for 2D flow fields (v2 look for the turbulence / vortex-street shots).

A dye field c(x, y) in [0, 1] becomes poured paint:
  colour  : a banded neon palette along c  -> mixed layers marble into thin stripes that trace every swirl
  relief  : height from c (+ a ridge at each band edge, like paint layers of different thickness)
  light   : lambert key + soft heightfield shadows + glossy reflections of neon strip lights (with a thin-film
            hue shift on the highlight) -> real light & shadow instead of a flat colour map
Output is scene-linear HDR (graded later by grade.py).
"""
import cv2
import numpy as np

# palette stops (position in c, linear RGB): ink violet sky -> magenta / peach / gold / white stripes -> deep teal
NEON_POUR = [
    (0.00, (0.030, 0.004, 0.060)),
    (0.10, (0.090, 0.010, 0.160)),
    (0.22, (0.60, 0.02, 0.45)),
    (0.32, (1.00, 0.18, 0.30)),
    (0.42, (1.00, 0.55, 0.20)),
    (0.50, (1.00, 0.90, 0.75)),
    (0.58, (0.30, 0.85, 1.00)),
    (0.70, (0.05, 0.35, 0.80)),
    (0.84, (0.10, 0.03, 0.30)),
    (1.00, (0.006, 0.010, 0.030)),
]


def palette_lut(stops, n=1024):
    xs = np.array([s[0] for s in stops])
    cs = np.array([s[1] for s in stops], np.float32)
    t = np.linspace(0, 1, n)
    return np.stack([np.interp(t, xs, cs[:, k]) for k in range(3)], -1).astype(np.float32)


def thin_film(cos_t, thickness=420.0, n_film=1.38):
    """approximate thin-film interference tint (RGB) for a given cos(angle)"""
    lam = np.array([650.0, 532.0, 460.0], np.float32)
    sin2 = np.clip(1 - cos_t ** 2, 0, 1)
    cos_f = np.sqrt(np.clip(1 - sin2 / n_film ** 2, 0, 1))
    phase = 4 * np.pi * n_film * thickness * cos_f[..., None] / lam
    return 0.5 + 0.5 * np.cos(phase)


_UNDUL = {}


def _undulation(h, w, seed=3):
    """static, very smooth surface waviness so flat paint still catches broad glossy gradients"""
    key = (h, w, seed)
    if key not in _UNDUL:
        rng = np.random.default_rng(seed)
        n = rng.standard_normal((h // 16 + 2, w // 16 + 2)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 3.0)
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)
        n = cv2.GaussianBlur(n, (0, 0), 24.0 * h / 1080.0)
        _UNDUL[key] = n / (n.std() + 1e-6)
    return _UNDUL[key]


def shade(c, lut=None, bands=2.0, relief=6.0, ridge=0.35, light=(-0.55, -0.45, 0.70), shadow=0.55,
          strips=None, spec=2.2, rough=0.10, ambient=0.18, film=0.6, sharpen=1.0, undul=0.0012):
    """c: (H, W) float in [0,1]. Returns (H, W, 3) linear HDR."""
    c = np.clip(c.astype(np.float32), 0, 1)
    c = cv2.GaussianBlur(c, (0, 0), 1.2 * c.shape[0] / 1080.0)
    if lut is None:
        lut = palette_lut(NEON_POUR)
    h_, w_ = c.shape
    s = h_ / 1080.0
    # banded colour: c is remapped through a few repeats of the palette inside the mixing zone
    mix_zone = 4 * c * (1 - c)                                      # 0 outside, 1 at the interface
    cb = c + (bands - 1) * 0.08 * np.sin(2 * np.pi * bands * c) * mix_zone
    cb = np.clip(cb, 0, 1)
    albedo = lut[(cb * (len(lut) - 1)).astype(np.int32)]
    # height: the dye bulges + a crisp ridge at each band edge
    hgt = 0.6 * c + ridge * mix_zone * (0.5 + 0.5 * np.cos(2 * np.pi * bands * 2 * c))
    hgt = cv2.GaussianBlur(hgt, (0, 0), 1.2 * s) + undul * _undulation(h_, w_)
    gy, gx = np.gradient(hgt)
    k = relief * 60.0 / s
    n = np.dstack([-gx * k, -gy * k, np.ones_like(c)])
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    diff = np.clip(n @ L, 0, 1)
    # soft heightfield shadows: march towards the light in screen space
    occl = np.zeros_like(c)
    dx, dy = L[0] / np.hypot(L[0], L[1]), -L[1] / np.hypot(L[0], L[1])
    slope = L[2] / np.hypot(L[0], L[1])
    hs = hgt * 40.0 * s
    for step in (2, 4, 7, 11, 16, 23, 32):
        st_ = step * s
        M = np.float32([[1, 0, dx * st_], [0, 1, dy * st_]])
        ahead = cv2.warpAffine(hs, M, (w_, h_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        occl = np.maximum(occl, np.clip((ahead - hs - st_ * slope * 0.25) / 6.0, 0, 1))
    sh = 1 - shadow * cv2.GaussianBlur(occl, (0, 0), 2.0 * s)
    # glossy reflection of neon strip lights (view straight down; r = reflected view direction)
    r = 2 * n[..., 2:3] * n - np.array([0, 0, 1], np.float32)
    if strips is None:
        strips = [((-0.25, 0.30), (0.9, 0.05), (1.0, 0.95, 0.9), 1.0),     # (centre rx, ry), (half-len, half-width)
                  ((0.35, -0.15), (0.05, 0.6), (1.0, 0.15, 0.7), 0.8),
                  ((-0.40, -0.35), (0.6, 0.04), (0.1, 0.8, 1.0), 0.8)]
    spec_rgb = np.zeros_like(albedo)
    w_rough = rough
    for (cx, cy), (hx, hy), col, gain in strips:
        ax = np.clip((np.abs(r[..., 0] - cx) - hx) / w_rough, 0, None)
        ay = np.clip((np.abs(r[..., 1] - cy) - hy) / w_rough, 0, None)
        lobe = np.exp(-(ax ** 2 + ay ** 2) * 2.0)
        spec_rgb += gain * lobe[..., None] * np.array(col, np.float32)
    # broad overhead softbox: gives the flat paint a soft glossy gradient
    soft = np.exp(-((r[..., 0] + 0.05) ** 2 / 0.02 + (r[..., 1] - 0.10) ** 2 / 0.006))
    spec_rgb += 0.18 * soft[..., None] * np.array((0.85, 0.8, 1.0), np.float32)
    cos_t = np.clip(n[..., 2], 0, 1)
    fres = 0.04 + 0.96 * (1 - cos_t) ** 5
    tint = (1 - film) + film * thin_film(cos_t)
    out = albedo * (ambient + 1.25 * diff * sh)[..., None] + spec * spec_rgb * tint * (0.35 + fres)[..., None]
    # a little light bleeding through the thin bright layers (acrylic translucency)
    out += 0.25 * albedo * cv2.GaussianBlur(albedo, (0, 0), 6 * s) * mix_zone[..., None]
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    import grade
    from common import CACHE

    f = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    c = np.load(CACHE / "s08" / f"c_{f:04d}.npy").astype(np.float32)
    # a 1920x1080 window around the interface
    y0 = 1180 - 540
    x0 = 900
    crop = c[y0:y0 + 1080, x0:x0 + 1920]
    lin = shade(crop)
    out = CACHE / "lookdev_v2" / f"paint_{f:04d}.png"
    grade.save_png(grade.grade(lin, exposure=0.0, bloom_strength=0.06, ca=1.0), out)
    print(out)
