import sys, time
sys.path.insert(0, r"D:\Creative\CFD Intro\src")
import numpy as np, cv2
from lbm3d import LBM3D, Scalar3D, wp, set_velocity, curl_noise
NX, NY, NZ = 128, 320, 128
nu = float(sys.argv[1]); amp = float(sys.argv[2]); buoy = float(sys.argv[3]); nsteps = int(sys.argv[4]); tag = sys.argv[5]
sim = LBM3D(NX, NY, NZ, nu=nu, bounds=(0,0,1,4,0,0), csmag=0.12)
ux, uy, uz = curl_noise((NZ, NY, NX), 10.0, amp, seed=1)
set_velocity(sim, ux, uy, uz)
T = Scalar3D(sim, 1, arr=sim.temp); S = Scalar3D(sim, 2)
sim.buoy = buoy
src = np.array([64.0, 12.0, 64.0])
rng = np.random.default_rng(0)
t0 = time.time()
snaps = []
for s in range(nsteps):
    sim.gforce = (2e-7*np.sin(s*2e-4), 0.0, 1.5e-7*np.cos(s*1.3e-4))
    sim.step()
    if s % 2 == 0:
        p = src + np.array([0.2*rng.standard_normal(), 0, 0.2*rng.standard_normal()])
        T.add_source(p, 1.2, 0.25, cap=1.0)
        T.advect(2.0, keep=0.9993); sim.temp = T.c
    if s % 4 == 0:
        S.add_source(p, 0.6, 0.6, cap=1.0)
        S.advect(4.0, keep=0.9997)
    if (s+1) % (nsteps//4) == 0:
        d = S.c.numpy()
        snaps.append((1-np.exp(-0.12*d.sum(axis=0)))[::-1])
        print(s+1, f"{time.time()-t0:.0f}s umax", float(np.abs(sim.uy.numpy()).max()), flush=True)
img = np.concatenate(snaps, axis=1)
cv2.imwrite(rf"D:\Creative\CFD Intro\cache\test_plume2_{tag}.png", (img*255).astype(np.uint8))
