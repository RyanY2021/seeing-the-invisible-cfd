"""S11 car in a wind tunnel: 3D LBM around the SDF car + centre-plane smoke rake -> OpenVDB density per frame.

Pre-step (venv):  python src/sim_car_mask.py      -> cache/car/solid.npy
Run (Blender):    blender.exe -b --factory-startup --python blender/sim_car.py -- [nframes] [warmup]
Output: cache/car_vdb/car_####.vdb (grid 'density'); smoke grid voxel = DX/2 metres.
LBM axes: x = flow (car length), y = up, z = lateral.  Car frame: x length, y lateral, z up.
"""
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\Creative\CFD Intro")
sys.path.append(str(ROOT / ".venv" / "Lib" / "site-packages"))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import openvdb as vdb

from lbm3d import INLET, OUTLET, SLIP, LBM3D, wp
from particles3d import Particles3D

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NFRAMES = int(argv[0]) if len(argv) > 0 else 200
WARMUP = int(argv[1]) if len(argv) > 1 else 8000
STEPS_PER_FRAME = 60

meta = np.load(ROOT / "cache" / "car" / "solid_meta.npz")
DX = float(meta["dx"])
ORIGIN = meta["origin"]  # car-frame (x, z_up, y_lat) of LBM cell (0,0,0)
solid = np.load(ROOT / "cache" / "car" / "solid.npy")
NZ, NY, NX = solid.shape
U = 0.07

sim = LBM3D(NX, NY, NZ, nu=1e-4, solid=solid, bounds=(INLET, OUTLET, SLIP, SLIP, SLIP, SLIP), csmag=0.16,
            u_init=(U, 0, 0), u_in=(U, 0, 0), sponge=(0, int(NX * 0.9), 0.04))


def car_to_lbm(xc, yl, zu):
    return ((xc - ORIGIN[0]) / DX, (zu - ORIGIN[1]) / DX, (yl - ORIGIN[2]) / DX)


# smoke rake: centre plane + one plane over each fender line
rake = []
for zu in np.arange(0.22, 1.75, 0.075):
    rake.append(car_to_lbm(-0.55, 0.0, zu))
for yl in (-0.62, 0.62):
    for zu in np.arange(0.30, 1.20, 0.15):
        rake.append(car_to_lbm(-0.55, yl, zu))
rake = np.array(rake, np.float32)
P = Particles3D(3_000_000)

R = 2
# smoke grid region (car frame): x -1.0..9.0, up 0..2.4, lateral -1.5..1.5
g_lo = np.array(car_to_lbm(-1.0, -1.5, 0.0))
g_hi = np.array(car_to_lbm(9.0, 1.5, 2.4))
GX, GY, GZ = [int((g_hi[i] - g_lo[i]) * R) for i in range(3)]
grid = wp.zeros((GZ, GY, GX), dtype=float, device="cuda:0")
OUT = ROOT / "cache" / "car_vdb"
OUT.mkdir(parents=True, exist_ok=True)
print("lbm", NX, NY, NZ, "grid", GX, GY, GZ, flush=True)

t0 = time.time()
step = 0
for _ in range(WARMUP):
    sim.step()
    step += 1
wp.synchronize()
print(f"warmup {WARMUP} {time.time() - t0:.0f}s", flush=True)
# pre-fill smoke for ~1 car length so the first frame already shows streaks
for k in range(2400):
    sim.step()
    if k % 2 == 0:
        P.emit(rake, 6, 0.18)
        P.advect(sim, 2.0, d0=0.0015, d1=2.5e-6, maxage=9000)
    step += 1
for f in range(NFRAMES):
    for k in range(STEPS_PER_FRAME):
        sim.step()
        if k % 2 == 0:
            P.emit(rake, 6, 0.18)
            P.advect(sim, 2.0, d0=0.0015, d1=2.5e-6, maxage=9000)
        step += 1
    P.splat(grid, g_lo, R, w0=0.08, fade_age=5000)
    d = grid.numpy()  # [lat, up, x]
    d[d < 1e-3] = 0
    g = vdb.FloatGrid()
    # VDB index (x, lateral, up) -> Blender X (length), Y (lateral), Z (up)
    g.copyFromArray(np.ascontiguousarray(d.transpose(2, 0, 1)), tolerance=1e-4)
    g.name = "density"
    g.saveFloatAsHalf = True
    vdb.write(str(OUT / f"car_{f:04d}.vdb"), grids=[g])
    if f % 20 == 0:
        print(f"frame {f} step {step} {time.time() - t0:.0f}s active={g.activeVoxelCount()}", flush=True)
np.savez(OUT / "meta.npz", grid_origin_car=np.array([-1.0, -1.5, 0.0]), voxel=DX / R)
print("done", time.time() - t0, flush=True)
