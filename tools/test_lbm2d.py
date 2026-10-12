import sys, time
sys.path.insert(0, r"D:\Creative\CFD Intro\src")
import numpy as np
from lbm2d import LBM2D, Particles, cylinder_mask, wp
import cv2
nx, ny = 1400, 600
D = 60; cx, cy = 300, 300.5
U = 0.08; Re = 150
nu = U*D/Re
solid = cylinder_mask(nx, ny, cx, cy, D/2)
sim = LBM2D(nx, ny, nu, solid=solid, periodic_y=True, csmag=0.0)
P = Particles(3_000_000)
rake = [(150.0, y) for y in np.arange(15, ny, 20.0)]
t0 = time.time()
nsteps = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
for s in range(nsteps):
    uin = U*min(1.0, s/1500)
    vin = 0.08*U*np.sin(np.pi*(s-1500)/2000) if 1500 < s < 3500 else 0.0
    sim.step(uin, vin)
    if s % 4 == 0:
        P.emit(rake, per_source=2, jitter=0.3)
        P.advect(sim, 4.0, diff0=0.0004, diff_age=0.0)
    if s % 5000 == 0:
        w = sim.vorticity(); print(s, "asym", float(np.abs(w + w[::-1]).mean()))
wp.synchronize()
dt = time.time()-t0
print(f"{nsteps} steps in {dt:.1f}s")
w = sim.vorticity()
img = P.splat(0, 0, 1.0, nx, ny)
img = cv2.GaussianBlur(img, (0,0), 0.7)
im = 1-np.exp(-0.5*img)
cv2.imwrite(r"D:\Creative\CFD Intro\cache\test_particles.png", (im*255).astype(np.uint8))
wv = np.clip(w/0.01*0.5+0.5, 0, 1)[::-1]
cv2.imwrite(r"D:\Creative\CFD Intro\cache\test_vort.png", cv2.applyColorMap((wv*255).astype(np.uint8), cv2.COLORMAP_TWILIGHT_SHIFTED))
