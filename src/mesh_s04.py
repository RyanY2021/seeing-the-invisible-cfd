"""S04 — octree/quadtree CFD mesh around the SDF car on two slice planes (precomputed for Blender).

Vertical slice: y = 0 (x-z plane).  Horizontal slice: z = 0.55 (x-y plane).
Cells refine towards the car surface (|sdf| < k*h) and in a wake box. Saves cache/car/mesh_cells.npz:
  for each plane: array (n, 4) of [u0, v0, size, level] (u,v = plane coords), cells inside the body dropped.
"""
import numpy as np

from car_sdf import car_sdf
from common import cache_dir

H0 = 0.8
LMAX = 5


def build(plane):
    if plane == "xz":
        u0, u1, v0, v1 = -3.2, 10.4, 0.0, 4.0
        f = lambda u, v: car_sdf(u, np.zeros_like(u), v)
    else:
        u0, u1, v0, v1 = -3.2, 10.4, -3.2, 3.2
        f = lambda u, v: car_sdf(u, v, np.full_like(u, 0.55))
    cells = []
    nu, nv = int(round((u1 - u0) / H0)), int(round((v1 - v0) / H0))
    stack = [(u0 + i * H0, v0 + j * H0, H0, 0) for i in range(nu) for j in range(nv)]
    while stack:
        nxt = []
        for (cu, cv, h, L) in stack:
            uc, vc = np.array([cu + h / 2]), np.array([cv + h / 2])
            d = float(f(uc, vc)[0])
            wake = (cu + h / 2 > 3.6) and (cu < 8.5) and (abs((cv + h / 2) - (0.6 if plane == "xz" else 0.0)) < 1.3)
            need = (abs(d) < 1.6 * h and L < LMAX) or (wake and L < 3)
            if need:
                hh = h / 2
                nxt += [(cu, cv, hh, L + 1), (cu + hh, cv, hh, L + 1), (cu, cv + hh, hh, L + 1), (cu + hh, cv + hh, hh, L + 1)]
            else:
                if d > -0.5 * h:  # keep fluid cells (and cut cells)
                    cells.append((cu, cv, h, L))
        stack = nxt
    return np.array(cells, np.float32)


if __name__ == "__main__":
    out = cache_dir("car")
    xz = build("xz")
    xy = build("xy")
    np.savez(out / "mesh_cells.npz", xz=xz, xy=xy)
    print("cells xz", len(xz), "xy", len(xy))
