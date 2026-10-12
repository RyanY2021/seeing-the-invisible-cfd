import sys, time
sys.path.insert(0, r"D:\Creative\CFD Intro\src")
import numpy as np
from lbm3d import LBM3D, Scalar3D, wp
NX, NY, NZ = 128, 256, 128
sim = LBM3D(NX, NY, NZ, nu=0.0035, bounds=(0,0,1,4,0,0), csmag=0.1)
S = Scalar3D(sim, 2); T = Scalar3D(sim, 1, arr=sim.temp)
sim.step(5); S.advect(4.0); T.advect(2.0); S.add_source((64,16,64),0.7,0.5); wp.synchronize()
t=time.time(); sim.step(200); wp.synchronize(); dt=time.time()-t; print(f"LBM: {200/dt:.1f} steps/s  {NX*NY*NZ*200/dt/1e9:.2f} GLUPS")
t=time.time(); [S.advect(4.0) for _ in range(20)]; wp.synchronize(); print(f"fine advect: {(time.time()-t)/20*1000:.1f} ms")
t=time.time(); [T.advect(2.0) for _ in range(20)]; wp.synchronize(); print(f"base advect: {(time.time()-t)/20*1000:.1f} ms")
t=time.time(); [S.add_source((64,16,64),0.7,0.5) for _ in range(20)]; wp.synchronize(); print(f"source: {(time.time()-t)/20*1000:.1f} ms")
