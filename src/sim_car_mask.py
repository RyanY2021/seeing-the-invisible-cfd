"""Voxelise the SDF car for the S11 wind-tunnel LBM (saves cache/car/solid.npy + solid_meta.npz)."""
import numpy as np

from car_sdf import solid_mask
from common import cache_dir

DX = 0.03
# LBM cell (0,0,0) centre in car frame: x (length), z (up), y (lateral)
ORIGIN = np.array([-2.4 + DX / 2, DX / 2, -2.88 + DX / 2])
NX, NY, NZ = 460, 128, 192

if __name__ == "__main__":
    out = cache_dir("car")
    m = solid_mask(NX, NY, NZ, DX, ORIGIN)
    np.save(out / "solid.npy", m)
    np.savez(out / "solid_meta.npz", dx=DX, origin=ORIGIN)
    print("solid cells", int(m.sum()), "of", m.size)
