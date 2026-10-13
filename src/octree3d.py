"""3D octree mesh around the SDF car (v2 V13 'chop space into cells'): cells refine towards the body surface.

Only the far half (y >= 0) is kept, so the camera looks into a cutaway. Cells inside the body are dropped.
Saves cache/v2/octree_car.npz: cells (n, 5) = [x0, y0, z0, h, level], plus 'parent' index for the build animation.
"""
import numpy as np

from car_sdf import car_sdf
from common import cache_dir

H0 = 1.6
LMAX = 5
BOX = (-3.2, 9.6, 0.0, 4.8, 0.0, 4.8)     # x0, x1, y0, y1, z0, z1  (car: x 0..4.5, |y| < 0.95, z < 1.3)


def build():
    x0, x1, y0, y1, z0, z1 = BOX
    nx, ny, nz = (int(round((b - a) / H0)) for a, b in ((x0, x1), (y0, y1), (z0, z1)))
    stack = [(x0 + i * H0, y0 + j * H0, z0 + k * H0, H0, 0, -1)
             for i in range(nx) for j in range(ny) for k in range(nz)]
    cells, parents = [], []
    level_nodes = []                      # every node ever created (for the subdivision animation)
    while stack:
        c = np.array([[cx + h / 2, cy + h / 2, cz + h / 2] for (cx, cy, cz, h, L, p) in stack])
        d = car_sdf(c[:, 0], c[:, 1], c[:, 2])
        nxt = []
        for (cx, cy, cz, h, L, p), dd in zip(stack, d):
            me = len(level_nodes)
            level_nodes.append((cx, cy, cz, h, L, p))
            wake = cx + h / 2 > 3.8 and cx < 8.0 and cy < 1.4 and cz < 1.8
            if (abs(dd) < 1.0 * h * 0.87 and L < LMAX) or (wake and L < 3):
                hh = h / 2
                for a in (0, 1):
                    for b in (0, 1):
                        for e in (0, 1):
                            nxt.append((cx + a * hh, cy + b * hh, cz + e * hh, hh, L + 1, me))
            elif dd > -0.5 * h:
                cells.append((cx, cy, cz, h, L))
                parents.append(p)
        stack = nxt
    return np.array(cells, np.float32), np.array(parents, np.int32), np.array(level_nodes, np.float32)


if __name__ == "__main__":
    cells, parents, nodes = build()
    out = cache_dir("v2")
    np.savez(out / "octree_car.npz", cells=cells, parents=parents, nodes=nodes)
    print("cells", len(cells), "nodes", len(nodes), "levels", np.bincount(cells[:, 4].astype(int)))
