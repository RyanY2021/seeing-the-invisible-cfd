"""S06 — flow past a cylinder starts from rest and develops a von Karman vortex street.

Stage 1 (sim):   python shot_s06_vortex_street.py sim     -> cache/s06/dens_####.npy (+ meta.npz)
Stage 2 (render):python shot_s06_vortex_street.py render  -> renders/S06/####.png
Look: smoke-rake streaklines in a dark wind tunnel, lit by a light sheet.
"""
from __future__ import annotations

import sys
import time

import numpy as np

from common import H, W, cache_dir, save_png16, shot_dir, smoothstep

NX, NY = 2800, 1200
D = 100.0
CX, CY = 620.0, 600.5
U = 0.08
RE = 150.0
NFRAMES = 432  # 18 s incl. handles
RAKE_X = 330.0
RAKE_DY = 32.0
SS = 2  # supersampling of the splat
EXPO = 0.55  # density -> optical coverage


def steps_for_frame(f):
    return int(round(50 + (220 - 50) * smoothstep(0, 250, f)))


def camera(f):
    """View window in lattice coords: returns x0, y0, scale(px per cell)."""
    t = f / (NFRAMES - 1)
    scale = 0.90 + 0.12 * smoothstep(0.0, 1.0, t)  # slow push-in
    vw, vh = W / scale, H / scale
    frac = 0.24 - 0.03 * smoothstep(0.0, 1.0, t)  # cylinder sits ~1/4 from the left edge
    cyv = 600.0
    return CX - frac * vw, cyv - vh / 2, scale


def sim():
    from lbm2d import LBM2D, Particles, cylinder_mask, wp

    out = cache_dir("s06")
    nu = U * D / RE
    solid = cylinder_mask(NX, NY, CX, CY, D / 2)
    s = LBM2D(NX, NY, nu, solid=solid, periodic_y=True, csmag=0.0)
    P = Particles(20_000_000)
    rake = [(RAKE_X, y) for y in np.arange(RAKE_DY / 2, NY, RAKE_DY)]
    t0 = time.time()
    step = 0
    steps_log = []
    for f in range(NFRAMES):
        n = steps_for_frame(f)
        for _ in range(n):
            uin = U * min(1.0, step / 1500)
            vin = 0.08 * U * np.sin(np.pi * (step - 2500) / 2500) if 2500 < step < 5000 else 0.0
            s.step(uin, vin)
            if step % 2 == 0:
                P.emit(rake, per_source=8, jitter=0.35)
                P.advect(s, 2.0, diff0=0.0004)
            step += 1
        x0, y0, sc = camera(f)
        img = P.splat(x0, y0, sc * SS, W * SS, H * SS)
        import cv2

        img = cv2.GaussianBlur(img, (0, 0), 1.8)
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
        np.save(out / f"dens_{f:04d}.npy", img.astype(np.float16))
        if f % 4 == 0:
            w = s.vorticity()
            np.save(out / f"vort_{f:04d}.npy", w[::2, ::2].astype(np.float16))
        steps_log.append(step)
        if f % 24 == 0:
            print(f"frame {f} step {step} {time.time() - t0:.0f}s", flush=True)
    np.savez(out / "meta.npz", steps=np.array(steps_log), nx=NX, ny=NY, D=D, cx=CX, cy=CY)
    print("sim done", time.time() - t0)


def render(first=0, last=NFRAMES):
    import cv2

    from look import bloom, disc_mask, filmic, gblur, vignette

    src = cache_dir("s06")
    dst = shot_dir("S06")
    vig = vignette(H, W, 0.45)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # dark tunnel back wall: faint large-scale unevenness
    rng = np.random.default_rng(3)
    wall = gblur(rng.standard_normal((H, W)).astype(np.float32), 90) * 6 + 1
    wall = wall[..., None] * np.array([0.010, 0.012, 0.016], np.float32)
    for f in range(first, last):
        dens = np.load(src / f"dens_{f:04d}.npy").astype(np.float32)
        x0, y0, sc = camera(f)
        # light sheet from above: slightly brighter towards the top, gentle falloff
        sheet = 0.80 + 0.25 * (1 - yy / H)
        a = 1 - np.exp(-EXPO * dens)  # optical coverage
        glow = gblur(a, 2.5)
        smoke = (a * 0.92 + 0.25 * glow) * sheet
        col = np.array([1.0, 0.965, 0.92], np.float32)
        rgb = wall + smoke[..., None] * col * 1.25
        # faint scattered haze around dense smoke
        rgb += gblur(a, 30)[..., None] * np.array([0.05, 0.06, 0.08], np.float32)
        # cylinder seen end-on: dark polished rod with a light-sheet rim highlight
        pcx = (CX - x0) * sc
        pcy = H - 1 - (CY - y0) * sc
        r = D / 2 * sc
        m, dx, dy, d = disc_mask(H, W, pcx, pcy, r, 1.2)
        ang = np.arctan2(-dy, dx)
        rim = np.clip(1 - np.abs(d - r * 0.965) / (r * 0.05), 0, 1) * np.clip(np.sin(ang) * 1.2 + 0.1, 0, 1)
        face = np.array([0.018, 0.019, 0.022], np.float32) * (1 + 0.6 * np.clip(-dy / r, -1, 1))[..., None]
        face = face + (rim ** 2)[..., None] * np.array([0.55, 0.52, 0.48], np.float32)
        face += (np.exp(-((dx + r * 0.35) ** 2 + (dy + r * 0.35) ** 2) / (2 * (r * 0.18) ** 2)) * 0.05)[..., None]
        rgb = rgb * (1 - m[..., None]) + face * m[..., None]
        # contact shadow ring
        rgb *= (1 - 0.5 * np.clip(1 - (d - r) / (r * 0.08), 0, 1) * (d > r))[..., None]
        # smoke-rake nozzles at the left (thin tubes ending at RAKE_X)
        nx_end = (RAKE_X - x0) * sc
        if nx_end > -5:
            xe = int(np.clip(nx_end + 2, 0, W))
            for yl in np.arange(RAKE_DY / 2, NY, RAKE_DY):
                py = H - 1 - (yl - y0) * sc
                r0, r1 = int(max(py - 4, 0)), int(min(py + 5, H))
                if r1 <= r0 or xe <= 0:
                    continue
                ys = yy[r0:r1, :xe]
                xs = xx[r0:r1, :xe]
                tube = (np.clip(1 - np.abs(ys - py) / (1.6 * sc), 0, 1) * np.clip(nx_end - xs, 0, 1))[..., None]
                hl = (0.6 + 0.4 * np.clip(1 - np.abs(ys - py + 0.6) / (0.8 * sc), 0, 1))[..., None]
                sl = rgb[r0:r1, :xe]
                rgb[r0:r1, :xe] = sl * (1 - tube * 0.9) + tube * np.array([0.10, 0.10, 0.11], np.float32) * hl
        rgb = bloom(rgb, threshold=0.5, strength=0.22)
        rgb = filmic(rgb * vig, exposure=1.1)
        save_png16(dst / f"{f:04d}.png", rgb)
        if f % 48 == 0:
            print("render", f, flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("sim", "all"):
        sim()
    if mode in ("render", "all"):
        a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
        render(a, b)
