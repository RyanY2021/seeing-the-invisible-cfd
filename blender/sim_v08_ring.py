"""V08 smoke ring: an air-cannon 'piston' (a short cylindrical push at the hole) launches a vortex ring that flies
across the table on its own momentum. 3D LBM (lbm3d.py) + smoke on a 2x grid, written as VDB.

Run inside Blender (openvdb):  blender.exe -b --factory-startup --python blender/sim_v08_ring.py -- [nframes]
Scene mapping (Blender metres): base cell = 1.5 mm; lattice (x, up, depth) -> world x = X0 + x*dx,
z = Z0 + up*dx, y = Y0 + depth*dx.  Output cache/v08_vdb/ring_####.vdb (file k = V08 frame k+1).
"""
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\Creative\CFD Intro")
sys.path.append(str(ROOT / ".venv" / "Lib" / "site-packages"))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import openvdb as vdb  # noqa: E402
import warp as wp  # noqa: E402

from lbm3d import LBM3D, Scalar3D, feq3  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NFRAMES = int(argv[0]) if argv else 216
NX, NY, NZ = 320, 144, 144
R = 2
DX = 0.0015
SPF = 32
HOLE_X, HOLE_R = 26, 15.0            # lattice: the cannon's mouth plane and radius
CY, CZ = NY / 2, NZ / 2
FIRES = ((30, 33), (126, 129))       # V08 frames during which the piston pushes (two thumps)
U_JET = 0.075
OUT = ROOT / "cache" / "v08_vdb"
OUT.mkdir(parents=True, exist_ok=True)


@wp.kernel
def k_piston(f: wp.array4d(dtype=float), cxa: wp.array(dtype=int), cya: wp.array(dtype=int),
             cza: wp.array(dtype=int), wa: wp.array(dtype=float), x0: int, x1: int, cy: float, cz: float, r: float,
             u: float, amt: float):
    k, j, i = wp.tid()
    x = i + x0
    if x >= x1:
        return
    dy = float(j) - cy
    dz = float(k) - cz
    rr = wp.sqrt(dy * dy + dz * dz)
    a = wp.clamp((r - rr) / 1.5, 0.0, 1.0) * amt
    if a <= 0.0:
        return
    rho = float(0.0)
    for q in range(19):
        rho += f[q, k, j, x]
    for q in range(19):
        f[q, k, j, x] = (1.0 - a) * f[q, k, j, x] + a * feq3(q, rho, u, 0.0, 0.0, cxa, cya, cza, wa)


@wp.kernel
def k_fill(c: wp.array3d(dtype=float), r: float, x0: float, x1: float, cy: float, cz: float, rad: float):
    k, j, i = wp.tid()
    bx = (float(i) + 0.5) / r - 0.5
    by = (float(j) + 0.5) / r - 0.5
    bz = (float(k) + 0.5) / r - 0.5
    if bx < x0 or bx > x1:
        return
    rr = wp.sqrt((by - cy) * (by - cy) + (bz - cz) * (bz - cz))
    # only an annulus at the lip: the smoke that rolls up into the vortex core (the ring stays clear inside)
    a = wp.clamp((rad - rr) / 1.5, 0.0, 1.0) * wp.clamp((rr - 0.55 * rad) / 2.0, 0.0, 1.0)
    if a > 0.0:
        c[k, j, i] = wp.max(c[k, j, i], a)


sim = LBM3D(NX, NY, NZ, nu=0.004, bounds=(3, 4, 0, 0, 0, 0), csmag=0.17, u_in=(0, 0, 0), sponge=(0, 270, 0.08))
S = Scalar3D(sim, R)
t0 = time.time()
step = 0
for f in range(1, NFRAMES + 1):
    for k in range(SPF):
        sim.step()
        fr = f - 1 + k / SPF
        fire = [w for w in FIRES if w[0] <= fr < w[1]]
        if fire:
            x = (fr - fire[0][0]) / (fire[0][1] - fire[0][0])
            amt = 0.35 * np.sin(np.pi * x) ** 2
            wp.launch(k_piston, dim=(NZ, NY, 14), inputs=[sim.f0, sim.cx, sim.cy, sim.cz, sim.w, HOLE_X - 14, HOLE_X,
                                                          float(CY), float(CZ), HOLE_R, U_JET, float(amt)],
                      device=sim.d)
            # the cannon is full of smoke: keep the mouth region topped up while it fires
            wp.launch(k_fill, dim=S.dims, inputs=[S.c, float(R), float(HOLE_X - 10), float(HOLE_X + 1), float(CY),
                                                  float(CZ), HOLE_R - 1.0], device=sim.d)
        if step % 2 == 0:
            S.advect(2.0, keep=0.9999)
        step += 1
    d = S.c.numpy()
    d[d < 2e-3] = 0.0
    g = vdb.FloatGrid()
    g.copyFromArray(np.ascontiguousarray(d.transpose(2, 0, 1)), tolerance=1e-4)   # (x, depth, up)
    g.name = "density"
    g.saveFloatAsHalf = True
    vdb.write(str(OUT / f"ring_{f - 1:04d}.vdb"), grids=[g])
    if f % 12 == 0:
        ux = sim.ux.numpy(); xs = np.nonzero(d.sum(axis=(0, 1)) > 1e-3)[0]
        print(f"frame {f} {time.time() - t0:.0f}s max={d.max():.3f} umax={np.abs(ux).max():.3f} umean={ux.mean():.4f} smoke_x={xs.min() if len(xs) else -1}-{xs.max() if len(xs) else -1}", flush=True)
print("done", time.time() - t0, flush=True)
