"""S09 — one turbulent cloud layer, three levels of modelling: RANS (average) | LES (big eddies) | DNS (all).

Uses the S08 Kelvin-Helmholtz dye fields (cache/s08). python shot_s09_models.py -> renders/S09/####.png
"""
from __future__ import annotations

import sys

import cv2
import numpy as np

from common import H, W, cache_dir, save_png16, shot_dir
from look import bloom, filmic, gblur, vignette
from shot_s08_kh import NX, NY, Y0
from textfx import FONT_CAPTION_IT, FONT_LABEL, paste, text_layer

NFR = 180
SRC0 = 150  # first KH frame used


def main(first=0, last=NFR):
    src = cache_dir("s08")
    dst = shot_dir("S09")
    # mean profiles for the RANS band (x-average, then smoothed in time)
    profs = []
    for k in range(SRC0 - 40, min(SRC0 + NFR + 40, 336)):
        c = np.load(src / f"c_{k:04d}.npy").astype(np.float32)
        profs.append(c.mean(axis=1))
    profs = np.array(profs)
    rng = np.random.default_rng(1)
    det = np.zeros((NY // 2, NX // 2), np.float32)
    for oc in range(5):
        s = 2 ** oc
        n = rng.standard_normal((NY // 2 // s + 2, NX // 2 // s + 2)).astype(np.float32)
        det += cv2.resize(n, (NX // 2, NY // 2), interpolation=cv2.INTER_CUBIC) / (1.6 ** (5 - oc))
    det = cv2.resize(det / det.std(), (NX, NY), interpolation=cv2.INTER_LINEAR)
    det_low = gblur(det, 14)
    det_low /= det_low.std() + 1e-6
    yy_full = np.arange(NY, dtype=np.float32)[:, None]
    xx = np.arange(NX, dtype=np.float32)[None, :]
    third = NX / 3
    wl = np.clip((xx - (third - 150)) / 300, 0, 1)  # 0 left of the first divider
    wr = np.clip((xx - (2 * third - 150)) / 300, 0, 1)
    vig = vignette(H, W, 0.32)
    labels = [(text_layer("RANS", 30, FONT_LABEL, tracking=0.35, color=(0.97, 0.95, 0.93)),
               text_layer("the average flow", 26, FONT_CAPTION_IT, color=(0.9, 0.86, 0.82))),
              (text_layer("LES", 30, FONT_LABEL, tracking=0.35, color=(0.97, 0.95, 0.93)),
               text_layer("only the big eddies", 26, FONT_CAPTION_IT, color=(0.9, 0.86, 0.82))),
              (text_layer("DNS", 30, FONT_LABEL, tracking=0.35, color=(0.97, 0.95, 0.93)),
               text_layer("every single eddy", 26, FONT_CAPTION_IT, color=(0.9, 0.86, 0.82)))]
    for f in range(first, last):
        k = SRC0 + f
        c = np.load(src / f"c_{min(k, 335):04d}.npy").astype(np.float32)
        pi = k - (SRC0 - 40)
        prof = profs[max(pi - 30, 0):pi + 30].mean(axis=0)
        rans = np.broadcast_to(prof[:, None], c.shape)
        les = gblur(c, 16)
        field = rans * (1 - wl) + les * wl
        field = field * (1 - wr) + c * wr
        detail = wr  # fractal edge detail only for the resolved band
        edge = 4 * field * (1 - field)
        rho = np.clip(field + 0.16 * det * edge * detail, 0, 1) ** 1.2
        band = np.clip(1 - (Y0 - 170 - yy_full) / 520.0, 0, 1) ** 1.5
        band = np.clip(band + 0.18 * det_low * band * (1 - band) * 4, 0, 1)
        rho = rho * band * (1 + 0.08 * det_low)
        small = cv2.resize(rho, (NX // 4, NY // 4), interpolation=cv2.INTER_AREA)
        tau = np.zeros_like(small)
        cur = small
        for _ in range(70):
            cur = np.roll(cur, -2, axis=1)
            cur = np.roll(cur, -1, axis=0)
            cur[-1, :] = 0
            tau += cur
        light = np.exp(-0.30 * cv2.resize(tau, (NX, NY), interpolation=cv2.INTER_CUBIC))
        # full-domain view (scale 0.5), vertical: interface slightly below centre
        rho_c = cv2.resize(rho[::-1], (W, H), interpolation=cv2.INTER_AREA)
        light_c = cv2.resize(light[::-1], (W, H), interpolation=cv2.INTER_AREA)
        ycoord = cv2.resize(np.broadcast_to(yy_full, (NY, NX)).astype(np.float32)[::-1], (W, H))
        hgrad = np.clip((ycoord - 400) / 2400.0, 0, 1)[..., None]
        sky_low = np.array([1.00, 0.55, 0.28], np.float32)
        sky_mid = np.array([0.55, 0.42, 0.52], np.float32)
        sky_high = np.array([0.10, 0.16, 0.36], np.float32)
        sky = np.where(hgrad < 0.45, sky_low + (sky_mid - sky_low) * (hgrad / 0.45),
                       sky_mid + (sky_high - sky_mid) * ((hgrad - 0.45) / 0.55)) * 0.65
        yyp, xxp = np.mgrid[0:H, 0:W].astype(np.float32)
        sg = np.exp(-((xxp - W * 1.05) ** 2 + (yyp - H * 0.62) ** 2) / (2 * (W * 0.28) ** 2))
        sky += sg[..., None] * np.array([1.0, 0.6, 0.3], np.float32) * 0.5
        lit = light_c[..., None]
        cloud = np.array([0.30, 0.28, 0.38], np.float32) * (0.55 + 0.45 * (1 - hgrad)) + \
            np.array([1.55, 1.00, 0.62], np.float32) * lit * (0.65 + 0.35 * sg[..., None])
        eg = gblur(rho_c, 1.0)
        cloud += (np.clip(eg * (1 - eg) * 4, 0, 1) * light_c)[..., None] ** 2 * np.array([1.3, 0.9, 0.6]) * 0.5
        alpha = (1 - np.exp(-6.0 * rho_c))[..., None]
        rgb = sky * (1 - alpha) + cloud * alpha
        rgb = rgb * 0.93 + 0.07 * sky_low * 0.6
        rgb = bloom(rgb, threshold=0.75, strength=0.18)
        rgb = filmic(rgb * vig, exposure=1.15)
        # dividers + labels
        for xd in (W // 3, 2 * W // 3):
            rgb[:, xd - 1:xd + 1] = rgb[:, xd - 1:xd + 1] * 0.55 + 0.35
        fade = float(np.clip(f / 14.0, 0, 1))
        for i, (a, b) in enumerate(labels):
            cxp = W / 6 + i * W / 3
            paste(rgb, a, cxp, 84, opacity=fade, anchor="ct")
            paste(rgb, b, cxp, 128, opacity=fade * 0.95, anchor="ct")
        save_png16(dst / f"{f:04d}.png", rgb)
        if f % 30 == 0:
            print("render", f, flush=True)


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else NFR
    main(a, b)
