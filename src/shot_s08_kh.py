"""S08 — Kelvin-Helmholtz instability: a shear layer rolls up into billows that pair and merge
(swirls within swirls). Rendered as a sunset cloud layer (KH 'fluctus' clouds).

python shot_s08_kh.py sim      -> cache/s08/c_####.npy (float16 3840x2160 dye field)
python shot_s08_kh.py render   -> renders/S08/####.png
"""
from __future__ import annotations

import sys
import time

import numpy as np

from common import H, W, cache_dir, save_png16, shot_dir, smoothstep

NX, NY = 3840, 2160
U = 0.10  # velocity difference across the layer
DELTA = 9.0
Y0 = 1180.0
NFRAMES = 336
NU = 0.00025


def steps_for_frame(f):
    return 70 + int(70 * smoothstep(0, 200, f))


def sim():
    from lbm2d import LBM2D, Scalar, wp

    out = cache_dir("s08")
    yy, xx = np.mgrid[0:NY, 0:NX].astype(np.float32)
    eta = (yy - Y0) / DELTA
    ux = 0.5 * U * np.tanh(eta)
    rng = np.random.default_rng(5)
    pert = np.zeros_like(xx)
    for n, a in ((6, 1.0), (12, 0.6), (3, 0.5), (24, 0.25)):
        pert += a * np.sin(2 * np.pi * n * xx / NX + rng.uniform(0, 2 * np.pi))
    uy = 0.004 * U * pert * np.exp(-eta ** 2 / 8)
    s = LBM2D(NX, NY, NU, u_init=(ux, uy), periodic_x=True, periodic_y=False, inlet=False, csmag=0.10, sponge_frac=0)
    # cloud = lower layer; slightly soft interface
    c0 = 0.5 * (1 - np.tanh((yy - Y0) / 4.0))
    C = Scalar(s, c0.astype(np.float32))
    t0 = time.time()
    for f in range(NFRAMES):
        n = steps_for_frame(f)
        for k in range(n):
            s.step()
            if k % 2 == 1:
                C.advect(2.0)
        np.save(out / f"c_{f:04d}.npy", C.numpy().astype(np.float16))
        if f % 24 == 0:
            print(f"frame {f} step {s.t} {time.time() - t0:.0f}s", flush=True)
    print("done", time.time() - t0)


def camera(f):
    """Returns crop window (x0, y0, w) in sim pixels (h = w*9/16); slow push into a billow."""
    t = smoothstep(30, NFRAMES - 1, f)
    w = NX * (1 - 0.5 * t)
    cx = NX * 0.5 + 260 * t
    cy = Y0 + 40 * t
    return cx - w / 2, cy - w * 9 / 32, w


def render(first=0, last=NFRAMES):
    import cv2

    from look import bloom, filmic, gblur, vignette

    src = cache_dir("s08")
    dst = shot_dir("S08")
    vig = vignette(H, W, 0.35)
    # sun from the right, low: direction of light travel (towards -x, slightly down)
    rng = np.random.default_rng(1)
    # fine fractal detail to break up the sim's smooth edges (static in cloud space)
    det = np.zeros((NY // 2, NX // 2), np.float32)
    for oc in range(5):
        s = 2 ** oc
        n = rng.standard_normal((NY // 2 // s + 2, NX // 2 // s + 2)).astype(np.float32)
        n = cv2.resize(n, (NX // 2, NY // 2), interpolation=cv2.INTER_CUBIC)
        det += n / (1.6 ** (5 - oc))
    det = cv2.resize(det / det.std(), (NX, NY), interpolation=cv2.INTER_LINEAR)
    yy_full = np.arange(NY, dtype=np.float32)[:, None]
    for f in range(first, last):
        c = np.load(src / f"c_{f:04d}.npy").astype(np.float32)
        # density with soft fractal edge detail (only near the interface)
        edge = 4 * c * (1 - c)
        rho = np.clip(c + 0.16 * det * edge, 0, 1) ** 1.2
        # optical depth towards the sun (sun up-right): march by shifting a half-res copy
        small = cv2.resize(rho, (NX // 4, NY // 4), interpolation=cv2.INTER_AREA)
        tau = np.zeros_like(small)
        acc = small.copy()
        sx, sy = -1, 0  # step towards the sun in (x, y_img): sun to the right & above -> shift left/down
        cur = small
        for k in range(1, 90):
            cur = np.roll(cur, -1, axis=1)  # sample to the right
            if k % 4 == 0:
                cur = np.roll(cur, 1, axis=0)  # and slightly above (image y grows downward in roll)
            tau += cur
        tau = cv2.resize(tau, (NX, NY), interpolation=cv2.INTER_CUBIC)
        light = np.exp(-0.22 * tau)
        # crop camera window
        x0, y0, w = camera(f)
        hgt = w * 9 / 16
        M = np.float32([[W / w, 0, -x0 * W / w], [0, H / hgt, -(NY - y0 - hgt) * H / hgt]])
        flipped = lambda a: a[::-1]

        def crop(a):
            return cv2.warpAffine(flipped(a), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        rho_c = crop(rho)
        light_c = crop(light)
        ycoord = crop(np.broadcast_to(yy_full, (NY, NX)).astype(np.float32))
        # sky: warm near the horizon (bottom), deep blue above
        hgrad = np.clip((ycoord - 400) / 2400.0, 0, 1)[..., None]
        sky_low = np.array([1.00, 0.55, 0.28], np.float32)
        sky_mid = np.array([0.55, 0.42, 0.52], np.float32)
        sky_high = np.array([0.10, 0.16, 0.36], np.float32)
        sky = np.where(hgrad < 0.45, sky_low + (sky_mid - sky_low) * (hgrad / 0.45),
                       sky_mid + (sky_high - sky_mid) * ((hgrad - 0.45) / 0.55))
        sky *= 0.65
        # sun glow (off-screen right, low)
        yyp, xxp = np.mgrid[0:H, 0:W].astype(np.float32)
        sg = np.exp(-((xxp - W * 1.05) ** 2 + (yyp - H * 0.62) ** 2) / (2 * (W * 0.28) ** 2))
        sky += sg[..., None] * np.array([1.0, 0.6, 0.3], np.float32) * 0.5
        # cloud shading: lit side warm gold, shadowed side cool violet-grey, forward-scatter silver lining
        lit = light_c[..., None]
        sun_col = np.array([1.35, 0.82, 0.48], np.float32)
        amb_col = np.array([0.20, 0.17, 0.24], np.float32)
        cloud = amb_col + sun_col * lit * (0.55 + 0.45 * sg[..., None])
        edgeg = gblur(rho_c, 1.5)
        rim = np.clip(edgeg * (1 - edgeg) * 4, 0, 1) * light_c
        cloud += (rim ** 2)[..., None] * np.array([1.2, 0.85, 0.55], np.float32) * 0.6
        alpha = (1 - np.exp(-6.0 * rho_c))[..., None]
        rgb = sky * (1 - alpha) + cloud * alpha
        # aerial haze toward the bottom
        rgb = rgb * 0.93 + 0.07 * sky_low * 0.6
        rgb = bloom(rgb, threshold=0.75, strength=0.18)
        rgb = filmic(rgb * vig, exposure=1.15)
        save_png16(dst / f"{f:04d}.png", rgb)
        if f % 24 == 0:
            print("render", f, flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("sim", "all"):
        sim()
    if mode in ("render", "all"):
        a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
        render(a, b)
