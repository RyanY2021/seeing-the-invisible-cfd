"""S10 — wake roll-up behind an elliptically loaded wing (Krasny vortex-blob method), smoke-curtain markers.

The aircraft flies through a smoke curtain; behind it the trailing vortex sheet rolls up into two tip
vortices that wind the smoke into spirals. 2D (Trefftz-plane) dynamics, time since passage = tau.
Units: semi-span = 1 (= 6 m in the scene), bound circulation Gamma0 = 1 (time unit 0.84 s).
  python sim_wing.py [nframes t_pass outdir] -> cache/wing_tex/####.png  (v2: 336 4.0 wing_tex_v2)
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from common import FPS, cache_dir, init_warp

wp = init_warp()

N = 600
DELTA = 0.06
M = 3_000_000
import sys
NFRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 196
T_PASS = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2  # s: when the wing reaches the curtain
OUTNAME = sys.argv[3] if len(sys.argv) > 3 else "wing_tex"
T_UNIT = 1.4  # s per tau unit
YR = (-2.6, 2.6)
ZR = (-1.6, 1.0)
IMW, IMH = 1600, 800


@wp.kernel
def k_vel(p: wp.array(dtype=wp.vec2), vp: wp.array(dtype=wp.vec2), vs: wp.array(dtype=float), d2: float,
          out: wp.array(dtype=wp.vec2)):
    i = wp.tid()
    x = p[i]
    u = wp.vec2(0.0, 0.0)
    for k in range(vp.shape[0]):
        r = x - vp[k]
        w = vs[k] / (6.2831853 * (r[0] * r[0] + r[1] * r[1] + d2))
        u = u + wp.vec2(-w * r[1], w * r[0])
    out[i] = u


@wp.kernel
def k_axpy(a: wp.array(dtype=wp.vec2), b: wp.array(dtype=wp.vec2), s: float, out: wp.array(dtype=wp.vec2)):
    i = wp.tid()
    out[i] = a[i] + s * b[i]


@wp.kernel
def k_rk4(p: wp.array(dtype=wp.vec2), k1: wp.array(dtype=wp.vec2), k2: wp.array(dtype=wp.vec2),
          k3: wp.array(dtype=wp.vec2), k4: wp.array(dtype=wp.vec2), dt: float):
    i = wp.tid()
    p[i] = p[i] + dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])


def main():
    out = cache_dir(OUTNAME)
    rng = np.random.default_rng(2)
    a = np.linspace(0, np.pi, N + 1)
    yn = -np.cos(a)
    yc = -np.cos(0.5 * (a[1:] + a[:-1]))
    strength = (np.sin(a[:-1]) - np.sin(a[1:])).astype(np.float32)
    sheet = np.stack([yc, np.zeros(N)], -1).astype(np.float32)
    mk = np.stack([rng.uniform(*YR, M), rng.uniform(*ZR, M)], -1).astype(np.float32)
    # clumpy smoke: fractal noise weight in the initial curtain
    nz = np.zeros((128, 256), np.float32)
    for o in range(4):
        n = rng.standard_normal((4 * 2 ** o, 8 * 2 ** o)).astype(np.float32)
        nz += cv2.resize(n, (256, 128), interpolation=cv2.INTER_CUBIC) / 1.8 ** o
    nz = (nz - nz.mean()) / nz.std()
    iy = ((mk[:, 0] - YR[0]) / (YR[1] - YR[0]) * 255).astype(int)
    iz = ((mk[:, 1] - ZR[0]) / (ZR[1] - ZR[0]) * 127).astype(int)
    wgt = np.clip(0.55 + 0.35 * nz[iz, iy], 0.05, 1.0)
    # soft curtain edges (top / bottom / sides)
    wgt *= np.clip((mk[:, 1] - ZR[0]) / 0.35, 0, 1) * np.clip((ZR[1] - mk[:, 1]) / 0.5, 0, 1)
    wgt *= np.clip((YR[1] - np.abs(mk[:, 0])) / 0.4, 0, 1)
    P = wp.array(np.concatenate([sheet, mk]), dtype=wp.vec2)
    S = wp.array(strength, dtype=float)
    n_all = N + M
    k1, k2, k3, k4, tmp = [wp.zeros(n_all, dtype=wp.vec2) for _ in range(5)]
    d2 = DELTA * DELTA
    tau = 0.0
    t0 = time.time()
    norm = None
    for f in range(NFRAMES):
        target = max(0.0, (f / FPS - T_PASS) / T_UNIT)
        while tau < target - 1e-9:
            dt = min(0.0125, target - tau)
            vp = P[:N]
            wp.launch(k_vel, dim=n_all, inputs=[P, vp, S, d2, k1])
            wp.launch(k_axpy, dim=n_all, inputs=[P, k1, 0.5 * dt, tmp])
            wp.launch(k_vel, dim=n_all, inputs=[tmp, tmp[:N], S, d2, k2])
            wp.launch(k_axpy, dim=n_all, inputs=[P, k2, 0.5 * dt, tmp])
            wp.launch(k_vel, dim=n_all, inputs=[tmp, tmp[:N], S, d2, k3])
            wp.launch(k_axpy, dim=n_all, inputs=[P, k3, dt, tmp])
            wp.launch(k_vel, dim=n_all, inputs=[tmp, tmp[:N], S, d2, k4])
            wp.launch(k_rk4, dim=n_all, inputs=[P, k1, k2, k3, k4, float(dt)])
            tau += dt
        pts = P.numpy()
        m = pts[N:]
        px = (m[:, 0] - YR[0]) / (YR[1] - YR[0]) * IMW
        pz = (ZR[1] - m[:, 1]) / (ZR[1] - ZR[0]) * IMH
        ok = (px >= 0) & (px < IMW - 1) & (pz >= 0) & (pz < IMH - 1)
        img = np.zeros(IMH * IMW, np.float32)
        np.add.at(img, pz[ok].astype(int) * IMW + px[ok].astype(int), wgt[ok])
        img = cv2.GaussianBlur(img.reshape(IMH, IMW), (0, 0), 3.2)
        if norm is None:
            norm = np.percentile(img[img > 0], 99.5)
        cv2.imwrite(str(out / f"{f:04d}.png"), (np.clip(img / norm * 0.8, 0, 1) * 65535).astype(np.uint16))
        if f % 24 == 0:
            vz = pts[:N, 1]
            print(f"frame {f} tau {tau:.2f} sheet z-range {vz.min():.2f}..{vz.max():.2f} {time.time() - t0:.0f}s",
                  flush=True)
    print("done")


if __name__ == "__main__":
    main()
