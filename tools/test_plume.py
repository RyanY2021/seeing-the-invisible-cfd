import sys, time
sys.path.insert(0, r"D:\Creative\CFD Intro\src")
import numpy as np, cv2
from lbm3d import LBM3D, Scalar3D, wp
NX, NY, NZ = 128, 256, 128
sim = LBM3D(NX, NY, NZ, nu=0.0035, bounds=(0,0,1,4,0,0), csmag=0.1)
T = Scalar3D(sim, 1, arr=sim.temp)
S = Scalar3D(sim, 2)
sim.buoy = float(sys.argv[1]) if len(sys.argv)>1 else 2e-4
src = np.array([64.0, 16.0, 64.0])
rng = np.random.default_rng(0)
t0 = time.time()
nsteps = int(sys.argv[2]) if len(sys.argv)>2 else 6000
for s in range(nsteps):
    sim.step()
    if s % 2 == 0:
        p = src + np.array([0.3*np.sin(s*0.003)+0.2*rng.standard_normal(), 0, 0.3*np.cos(s*0.0021)+0.2*rng.standard_normal()])
        T.add_source(p, 1.2, 0.25, cap=1.0)
        T.advect(2.0, keep=0.9995)
        sim.temp = T.c
    if s % 4 == 0:
        S.add_source(p, 0.7, 0.5, cap=1.0)
        S.advect(4.0, keep=0.9995)
    if s % 1000 == 0:
        print(s, "umax", float(np.abs(sim.uy.numpy()).max()), f"{time.time()-t0:.1f}s", flush=True)
wp.synchronize()
print("time", time.time()-t0)
d = S.c.numpy()
img = 1-np.exp(-0.15*d.sum(axis=0))
cv2.imwrite(r"D:\Creative\CFD Intro\cache\test_plume_front.png", (img[::-1]*255).astype(np.uint8))
img2 = 1-np.exp(-0.15*d.sum(axis=2))
cv2.imwrite(r"D:\Creative\CFD Intro\cache\test_plume_side.png", (img2[::-1]*255).astype(np.uint8))
