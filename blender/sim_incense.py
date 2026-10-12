"""S01/S02/S15 incense plume: 3D LBM (D3Q19) + buoyancy, smoke on a 2x refined grid, written as OpenVDB.

Run inside Blender (for its openvdb module):
  blender.exe -b --factory-startup --python blender/sim_incense.py -- [nframes] [warmup_steps]
Output: cache/incense_vdb/incense_####.vdb  (grids: density [fine], vorticity [base, voxel 2])
1 fine voxel = 1 mm in the Blender scene (object scale 0.001). VDB index (i,j,k) = (x, depth, up).
"""
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\Creative\CFD Intro")
sys.path.append(str(ROOT / ".venv" / "Lib" / "site-packages"))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # Blender's numpy
import openvdb as vdb

from lbm3d import LBM3D, Scalar3D, curl_noise, set_velocity, wp

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NFRAMES = int(argv[0]) if len(argv) > 0 else 560
WARMUP = int(argv[1]) if len(argv) > 1 else 10000
STEPS_PER_FRAME = 24

NX, NY, NZ = 192, 384, 192
R = 2
OUT = ROOT / "cache" / "incense_vdb"
OUT.mkdir(parents=True, exist_ok=True)
PREV = ROOT / "cache" / "incense_preview"
PREV.mkdir(parents=True, exist_ok=True)

sim = LBM3D(NX, NY, NZ, nu=0.0008, bounds=(0, 0, 1, 4, 0, 0), csmag=0.12)
ux, uy, uz = curl_noise((NZ, NY, NX), 10.0, 0.0008, seed=7)
set_velocity(sim, ux, uy, uz)
T = Scalar3D(sim, 1, arr=sim.temp)
S = Scalar3D(sim, R)
sim.buoy = 4e-4
SRC = np.array([NX / 2, 12.0, NZ / 2])
rng = np.random.default_rng(11)

base_xform = vdb.createLinearTransform([[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0.5, 0.5, 0.5, 1]])


def one_step(s):
    sim.gforce = (2e-7 * np.sin(s * 2e-4 + 0.7), 0.0, 1.5e-7 * np.cos(s * 1.3e-4))
    sim.step()
    if s % 2 == 0:
        p = SRC + np.array([0.2 * rng.standard_normal(), 0, 0.2 * rng.standard_normal()])
        T.add_source(p, 1.2, 0.25, cap=1.0)
        T.advect(2.0, keep=0.9993)
        sim.temp = T.c
        one_step.p = p
    if s % 4 == 0:
        S.add_source(one_step.p, 0.6, 0.6, cap=1.0)
        S.advect(4.0, keep=0.9997)


one_step.p = SRC

t0 = time.time()
step = 0
for _ in range(WARMUP):
    one_step(step)
    step += 1
wp.synchronize()
print(f"warmup {WARMUP} steps {time.time() - t0:.0f}s", flush=True)

for f in range(NFRAMES):
    for _ in range(STEPS_PER_FRAME):
        one_step(step)
        step += 1
    d = S.c.numpy()  # [z, y, x]
    w = sim.vorticity_mag().numpy()
    d[d < 2e-3] = 0.0
    occ = d.reshape(NZ, R, NY, R, NX, R).max(axis=(1, 3, 5)) > 5e-3
    w = np.where(occ, w, 0.0).astype(np.float32)
    dg = vdb.FloatGrid()
    dg.copyFromArray(np.ascontiguousarray(d.transpose(2, 0, 1)), tolerance=1e-4)  # (x, depth, up)
    dg.name = "density"
    dg.saveFloatAsHalf = True
    wg = vdb.FloatGrid()
    wg.copyFromArray(np.ascontiguousarray(w.transpose(2, 0, 1)), tolerance=1e-5)
    wg.name = "vorticity"
    wg.transform = base_xform
    wg.saveFloatAsHalf = True
    vdb.write(str(OUT / f"incense_{f:04d}.vdb"), grids=[dg, wg])
    if f % 20 == 0:
        proj = 1 - np.exp(-0.12 * d.sum(axis=0))[::-1]
        np.save(PREV / f"proj_{f:04d}.npy", proj.astype(np.float16))
        print(f"frame {f} step {step} {time.time() - t0:.0f}s active={dg.activeVoxelCount()}", flush=True)
print("done", time.time() - t0, flush=True)
