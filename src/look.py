"""Shared 'photographic' finishing helpers for 2D shots (bloom, vignette, tone)."""
from __future__ import annotations

import cv2
import numpy as np


def gblur(img, sigma):
    if sigma <= 0:
        return img
    return cv2.GaussianBlur(img, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)


def bloom(rgb, threshold=0.6, strength=0.25, sigmas=(6, 18, 48)):
    lum = rgb.mean(-1, keepdims=True)
    hi = rgb * np.clip((lum - threshold) / (1 - threshold + 1e-6), 0, 1)
    acc = np.zeros_like(rgb)
    for i, s in enumerate(sigmas):
        acc += gblur(hi, s) * (0.6 ** i)
    return rgb + strength * acc


def vignette(h, w, strength=0.35, power=2.2):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx / (w - 1) - 0.5) * 2 * (w / h) / 1.7778
    ny = (yy / (h - 1) - 0.5) * 2
    r = np.sqrt(nx * nx * 0.75 + ny * ny * 0.95)
    return (1 - strength * np.clip(r, 0, 1.6) ** power / 1.6 ** power * 1.6).clip(0, 1)[..., None]


def filmic(x, exposure=1.0):
    """Soft-shoulder tone curve (ACES-like fit)."""
    x = np.maximum(x * exposure, 0)
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


def downsample2(img):
    return cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)


def disc_mask(h, w, cx, cy, r, aa=1.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip((r - d) / aa + 0.5, 0, 1), xx - cx, yy - cy, d
