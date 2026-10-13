"""S13 — real GFS 10 m winds (2026-10-12/13) as glowing particle streaks (equirectangular texture sequence).

python shot_s13_wind.py  -> cache/wind_tex/####.png (RGBA, 4096x2048) + prints the strongest cyclone (lat, lon)
Particles move ~1 h of wind per video frame while the field itself time-lapses 24 h over the shot.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy.io import netcdf_file

from common import ASSETS, cache_dir, init_warp

wp = init_warp()
TW, TH = 4096, 2048
NP = 260_000
import sys
NFR = int(sys.argv[1]) if len(sys.argv) > 1 else 190
OUTNAME = sys.argv[2] if len(sys.argv) > 2 else "wind_tex"
NEON = OUTNAME != "wind_tex"          # v2: neon palette
WARM = 70
DT_H = 1.0  # hours of particle motion per frame
FADE = 0.90


@wp.kernel
def k_adv(lon: wp.array(dtype=float), lat: wp.array(dtype=float), life: wp.array(dtype=float),
          U0: wp.array2d(dtype=float), V0: wp.array2d(dtype=float), U1: wp.array2d(dtype=float),
          V1: wp.array2d(dtype=float), a: float, nlat: int, nlon: int, dt_h: float, seed: int,
          img: wp.array3d(dtype=float), tw: int, th: int):
    i = wp.tid()
    st = wp.rand_init(seed, i)
    L = life[i] - 1.0
    if L <= 0.0:
        lon[i] = wp.randf(st) * 360.0
        lat[i] = wp.asin(wp.randf(st) * 2.0 - 1.0) * 57.29578
        L = 30.0 + wp.randf(st) * 70.0
    x = lon[i]
    y = lat[i]
    # grid: lat from +90 (row 0) to -90, lon 0..359.5 step 0.5
    fy = (90.0 - y) / 180.0 * float(nlat - 1)
    fx = x / 360.0 * float(nlon)
    iy = wp.clamp(int(fy), 0, nlat - 2)
    ix = int(wp.floor(fx))
    ty = fy - float(iy)
    tx = fx - float(ix)
    ix0 = (ix % nlon + nlon) % nlon
    ix1 = (ix0 + 1) % nlon
    u = (1.0 - a) * ((U0[iy, ix0] * (1.0 - tx) + U0[iy, ix1] * tx) * (1.0 - ty) + (U0[iy + 1, ix0] * (1.0 - tx) + U0[iy + 1, ix1] * tx) * ty) \
        + a * ((U1[iy, ix0] * (1.0 - tx) + U1[iy, ix1] * tx) * (1.0 - ty) + (U1[iy + 1, ix0] * (1.0 - tx) + U1[iy + 1, ix1] * tx) * ty)
    v = (1.0 - a) * ((V0[iy, ix0] * (1.0 - tx) + V0[iy, ix1] * tx) * (1.0 - ty) + (V0[iy + 1, ix0] * (1.0 - tx) + V0[iy + 1, ix1] * tx) * ty) \
        + a * ((V1[iy, ix0] * (1.0 - tx) + V1[iy, ix1] * tx) * (1.0 - ty) + (V1[iy + 1, ix0] * (1.0 - tx) + V1[iy + 1, ix1] * tx) * ty)
    # m/s -> deg per hour
    coslat = wp.max(wp.cos(y / 57.29578), 0.05)
    dlat = v * 3600.0 / 111320.0 * dt_h
    dlon = u * 3600.0 / (111320.0 * coslat) * dt_h
    y2 = wp.clamp(y + dlat, -89.5, 89.5)
    x2 = x + dlon
    x2 = x2 - 360.0 * wp.floor(x2 / 360.0)
    lon[i] = x2
    lat[i] = y2
    life[i] = L
    spd = wp.sqrt(u * u + v * v)
    # draw a short segment (4 sub-steps) into the RGBA accumulation image
    w = wp.min(spd / 14.0, 1.0)
    for k in range(4):
        s = float(k) / 4.0
        xx = x + dlon * s
        yy = y + dlat * s
        if wp.abs(dlon) > 30.0:
            continue
        px = int((xx - 360.0 * wp.floor(xx / 360.0)) / 360.0 * float(tw))
        py = int((90.0 - yy) / 180.0 * float(th))
        px = wp.clamp(px, 0, tw - 1)
        py = wp.clamp(py, 0, th - 1)
        wp.atomic_add(img, py, px, 0, w * 0.35)
        wp.atomic_add(img, py, px, 1, spd)
        wp.atomic_add(img, py, px, 2, 0.35)


def main():
    f = netcdf_file(str(ASSETS / "gfs" / "gfs_10m_24h.nc"), "r", mmap=False)
    U = f.variables["u-component_of_wind_height_above_ground"].data[:, 0].astype(np.float32)
    V = f.variables["v-component_of_wind_height_above_ground"].data[:, 0].astype(np.float32)
    lats = f.variables["latitude"].data
    lons = f.variables["longitude"].data
    nt, nlat, nlon = U.shape
    # strongest cyclone: max relative vorticity magnitude * sign(lat) (cyclonic), smoothed, |lat| 8..50
    dy = 0.5 * 111320.0
    vort = np.gradient(V[0], axis=1) / (dy * np.cos(np.radians(lats))[:, None] + 1) - np.gradient(U[0], axis=0) / -dy
    cyc = cv2.GaussianBlur((vort * np.sign(lats)[:, None]).astype(np.float32), (0, 0), 3)
    band = (np.abs(lats) > 8) & (np.abs(lats) < 50)
    cyc[~band] = -1
    iy, ix = np.unravel_index(np.argmax(cyc), cyc.shape)
    print(f"strongest cyclone near lat {lats[iy]:.1f}, lon {lons[ix]:.1f}")
    out = cache_dir(OUTNAME)
    rng = np.random.default_rng(0)
    lon = wp.array(rng.uniform(0, 360, NP).astype(np.float32), dtype=float)
    lat = wp.array(np.degrees(np.arcsin(rng.uniform(-1, 1, NP))).astype(np.float32), dtype=float)
    life = wp.array(rng.uniform(1, 100, NP).astype(np.float32), dtype=float)
    Us = [wp.array(U[k], dtype=float) for k in range(nt)]
    Vs = [wp.array(V[k], dtype=float) for k in range(nt)]
    acc = np.zeros((TH, TW, 3), np.float32)
    t0 = time.time()
    for f_ in range(-WARM, NFR):
        tt = max(f_, 0) / (NFR - 1) * (nt - 1)
        k0 = min(int(tt), nt - 2)
        a = tt - k0
        img = wp.zeros((TH, TW, 3), dtype=float)
        wp.launch(k_adv, dim=NP, inputs=[lon, lat, life, Us[k0], Vs[k0], Us[k0 + 1], Vs[k0 + 1], float(a), nlat, nlon,
                                         DT_H, f_ + 1000, img, TW, TH])
        new = img.numpy()
        acc *= FADE
        acc += new
        if f_ < 0:
            continue
        cnt = np.maximum(acc[..., 2], 1e-6)
        inten = np.clip(acc[..., 0], 0, 1.5)
        spd = acc[..., 1] / cnt
        inten = cv2.GaussianBlur(inten, (0, 0), 0.7)
        # colour by speed: calm = soft blue-white, strong = warm white/amber
        t = np.clip((spd - 9.0) / 16.0, 0, 1)[..., None] ** 1.3
        if NEON:   # calm = cyan, strong = hot magenta-pink
            col = (1 - t) * np.array([0.25, 0.85, 1.0]) + t * np.array([1.0, 0.28, 0.72])
        else:
            col = (1 - t) * np.array([0.74, 0.86, 1.0]) + t * np.array([1.0, 0.80, 0.48])
        alpha = np.clip(inten * 1.1, 0, 1)
        rgba = np.concatenate([col * alpha[..., None], alpha[..., None]], -1)
        cv2.imwrite(str(out / f"{f_:04d}.png"), (np.clip(rgba[..., [2, 1, 0, 3]], 0, 1) * 255).astype(np.uint8))
        if f_ % 30 == 0:
            print("frame", f_, f"{time.time() - t0:.0f}s", flush=True)
    print("done")


if __name__ == "__main__":
    main()
