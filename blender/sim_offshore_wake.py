"""S12 helical tip-vortex wake of an offshore wind turbine -> VDB sequence (condensation 'fog' density).

Rotor frame: s = downstream distance along the axis, (y, z) lateral/vertical relative to the hub.
Blade k tip at time t sits at angle th_k(t) = TH0 - OMEGA*t + 2*pi*k/3 (theta = 0 -> straight up, +y side positive).
A vortex element released at time t - s/UW keeps that angle while it convects downstream.
blender.exe -b --factory-startup --python blender/sim_offshore_wake.py -- [nframes]
"""
import math
import sys
import time
from pathlib import Path

import numpy as np
import openvdb as vdb

ROOT = Path(r"D:\Creative\CFD Intro")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NFR = int(argv[0]) if argv else 190

R = 80.0
OMEGA = 2 * math.pi * 10 / 60  # 10 rpm
UW = 7.0  # wake convection speed (m/s)
TH0 = 0.0
VOX = 1.2
S_MAX = 430.0
LAT = 125.0
OUT = ROOT / "cache" / "wake_vdb"
OUT.mkdir(parents=True, exist_ok=True)

s = np.arange(0, S_MAX, VOX, dtype=np.float32)
y = np.arange(-LAT, LAT, VOX, dtype=np.float32)
z = np.arange(-LAT, LAT, VOX, dtype=np.float32)
S, Y, Z = np.meshgrid(s, y, z, indexing="ij")
rad = np.sqrt(Y * Y + Z * Z)
theta = np.arctan2(Y, Z)  # 0 = up
rng = np.random.default_rng(4)


def lowfreq_noise(shape, scales, seed):
    r = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    for sc, amp in scales:
        n = r.standard_normal(tuple(max(2, int(d / sc)) for d in shape)).astype(np.float32)
        # trilinear upsample via numpy (separable)
        for ax, d in enumerate(shape):
            xp = np.linspace(0, n.shape[ax] - 1, d)
            i0 = np.floor(xp).astype(int)
            i1 = np.minimum(i0 + 1, n.shape[ax] - 1)
            t = (xp - i0).astype(np.float32)
            a0 = np.take(n, i0, axis=ax)
            a1 = np.take(n, i1, axis=ax)
            sh = [1] * len(shape)
            sh[ax] = d
            n = a0 * (1 - t.reshape(sh)) + a1 * t.reshape(sh)
        out += amp * n
    return out


# static turbulence fields (advected downstream each frame by shifting the sample index)
NOISE = lowfreq_noise(S.shape, [(18, 1.0), (7, 0.5)], 1)
expand = R * (1 + 0.12 * (1 - np.exp(-S / (1.5 * R))))
core = 2.6 + 0.030 * S
amp = np.exp(-S / 210.0) * np.clip(S / 8.0, 0, 1)
t0 = time.time()
for f in range(NFR):
    t = f / 24.0
    shift = int(round(UW * t / VOX))
    nz = np.roll(NOISE, shift, axis=0)
    wob = (0.015 + S / 2200.0) * nz  # gentle radial/angular wobble growing downstream
    dens = np.zeros(S.shape, np.float32)
    for k in range(3):
        th = TH0 - OMEGA * (t - S / UW) + 2 * math.pi * k / 3
        dth = ((theta - th + np.pi) % (2 * np.pi) - np.pi).astype(np.float32)
        dr = rad - expand * (1 + 0.15 * wob)
        d2 = dr * dr + (rad * (dth + 0.25 * wob)) ** 2
        dens += np.exp(-d2 / (2 * (core * (1 + 0.3 * np.abs(wob))) ** 2))
    dens *= amp * np.clip(0.9 + 0.15 * nz, 0.5, 1.2)
    # faint hub / root vortex
    dens += 0.12 * np.exp(-(rad ** 2) / (2 * (4.0 + 0.05 * S) ** 2)) * np.exp(-S / 200.0) * np.clip(0.6 + 0.6 * nz, 0, 1)
    dens[dens < 0.01] = 0
    g = vdb.FloatGrid()
    g.copyFromArray(np.ascontiguousarray(dens), tolerance=0.005)
    g.name = "density"
    g.saveFloatAsHalf = True
    vdb.write(str(OUT / f"wake_{f:04d}.vdb"), grids=[g])
    if f % 20 == 0:
        print(f"frame {f} {time.time() - t0:.0f}s active={g.activeVoxelCount()}", flush=True)
print("done", flush=True)
