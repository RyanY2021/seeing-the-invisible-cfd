"""3D smoke particles advected by an LBM3D velocity field, splatted into a refined density grid (Warp)."""
from __future__ import annotations

import numpy as np

from lbm3d import trilin, wp


@wp.kernel
def k_emit3(pos: wp.array(dtype=wp.vec3), age: wp.array(dtype=float), src: wp.array(dtype=wp.vec3), head: int,
            nslots: int, jitter: float, seed: int):
    i = wp.tid()
    ns = src.shape[0]
    k = (head + i) % nslots
    s = src[i % ns]
    st = wp.rand_init(seed, i)
    pos[k] = wp.vec3(s[0] + jitter * wp.randn(st), s[1] + jitter * wp.randn(st), s[2] + jitter * wp.randn(st))
    age[k] = 0.0


@wp.kernel
def k_adv3(pos: wp.array(dtype=wp.vec3), age: wp.array(dtype=float), ux: wp.array3d(dtype=float),
           uy: wp.array3d(dtype=float), uz: wp.array3d(dtype=float), solid: wp.array3d(dtype=wp.uint8),
           nx: int, ny: int, nz: int, dt: float, d0: float, d1: float, maxage: float, seed: int):
    i = wp.tid()
    a = age[i]
    if a < 0.0:
        return
    p = pos[i]
    v1 = wp.vec3(trilin(ux, p[0], p[1], p[2], nx, ny, nz, 0, 0, 0), trilin(uy, p[0], p[1], p[2], nx, ny, nz, 0, 0, 0),
                 trilin(uz, p[0], p[1], p[2], nx, ny, nz, 0, 0, 0))
    m = p + 0.5 * dt * v1
    v2 = wp.vec3(trilin(ux, m[0], m[1], m[2], nx, ny, nz, 0, 0, 0), trilin(uy, m[0], m[1], m[2], nx, ny, nz, 0, 0, 0),
                 trilin(uz, m[0], m[1], m[2], nx, ny, nz, 0, 0, 0))
    q = p + dt * v2
    st = wp.rand_init(seed, i)
    sig = wp.sqrt(2.0 * (d0 + d1 * a) * dt)
    q = q + sig * wp.vec3(wp.randn(st), wp.randn(st), wp.randn(st))
    if q[0] < 0.0 or q[0] > float(nx - 2) or q[1] < 0.0 or q[1] > float(ny - 2) or q[2] < 0.0 or q[2] > float(nz - 2) or a > maxage:
        age[i] = -1.0
        return
    if solid[int(q[2] + 0.5), int(q[1] + 0.5), int(q[0] + 0.5)] != wp.uint8(0):
        q = p
    pos[i] = q
    age[i] = a + dt


@wp.kernel
def k_splat3(pos: wp.array(dtype=wp.vec3), age: wp.array(dtype=float), grid: wp.array3d(dtype=float),
             ox: float, oy: float, oz: float, r: float, gx: int, gy: int, gz: int, w0: float, fade_age: float):
    """Trilinear splat into grid[z, y, x]; grid cell (0,0,0) centre at base coords (ox, oy, oz); r = refinement."""
    i = wp.tid()
    a = age[i]
    if a < 0.0:
        return
    p = pos[i]
    fx = (p[0] - ox) * r
    fy = (p[1] - oy) * r
    fz = (p[2] - oz) * r
    if fx < 0.0 or fy < 0.0 or fz < 0.0 or fx >= float(gx - 1) or fy >= float(gy - 1) or fz >= float(gz - 1):
        return
    ix = int(fx)
    iy = int(fy)
    iz = int(fz)
    tx = fx - float(ix)
    ty = fy - float(iy)
    tz = fz - float(iz)
    w = w0 * wp.exp(-a / fade_age)
    for dz in range(2):
        wz = tz
        if dz == 0:
            wz = 1.0 - tz
        for dy in range(2):
            wy = ty
            if dy == 0:
                wy = 1.0 - ty
            for dx in range(2):
                wx = tx
                if dx == 0:
                    wx = 1.0 - tx
                wp.atomic_add(grid, iz + dz, iy + dy, ix + dx, w * wx * wy * wz)


class Particles3D:
    def __init__(self, n, device="cuda:0"):
        self.n = n
        self.d = device
        self.pos = wp.zeros(n, dtype=wp.vec3, device=device)
        self.age = wp.full(n, -1.0, dtype=float, device=device)
        self.head = 0
        self.seed = 1

    def emit(self, src, per_source, jitter):
        src = np.asarray(src, np.float32).reshape(-1, 3)
        sw = wp.array(src, dtype=wp.vec3, device=self.d)
        cnt = len(src) * per_source
        self.seed += 1
        wp.launch(k_emit3, dim=cnt, inputs=[self.pos, self.age, sw, self.head, self.n, float(jitter), self.seed],
                  device=self.d)
        self.head = (self.head + cnt) % self.n

    def advect(self, sim, dt, d0=0.0, d1=0.0, maxage=1e9):
        self.seed += 1
        wp.launch(k_adv3, dim=self.n, inputs=[self.pos, self.age, sim.ux, sim.uy, sim.uz, sim.solid, sim.nx, sim.ny,
                                              sim.nz, float(dt), float(d0), float(d1), float(maxage), self.seed],
                  device=self.d)

    def splat(self, grid, origin, r, w0=1.0, fade_age=1e9):
        gz, gy, gx = grid.shape
        grid.zero_()
        wp.launch(k_splat3, dim=self.n, inputs=[self.pos, self.age, grid, float(origin[0]), float(origin[1]),
                                                float(origin[2]), float(r), gx, gy, gz, float(w0), float(fade_age)],
                  device=self.d)
        return grid
