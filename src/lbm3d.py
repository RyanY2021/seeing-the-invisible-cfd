"""3D lattice-Boltzmann solver (D3Q19, regularised BGK + Smagorinsky, Guo forcing) on the GPU (Warp),
plus MacCormack passive scalars on a base or refined grid (smoke density / temperature).

Axes: x (width), y (UP), z (depth). Arrays are indexed [z, y, x] (x fastest in memory).
Boundary type per face: 0 periodic, 1 no-slip wall, 2 free-slip, 3 velocity inlet, 4 pressure outlet.
"""
from __future__ import annotations

import numpy as np

from common import init_warp

wp = init_warp()

wp.set_module_options({"max_unroll": 64})
vec19 = wp.types.vector(length=19, dtype=wp.float32)

_C = [(0, 0, 0),
      (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
      (1, 1, 0), (-1, -1, 0), (1, -1, 0), (-1, 1, 0),
      (1, 0, 1), (-1, 0, -1), (1, 0, -1), (-1, 0, 1),
      (0, 1, 1), (0, -1, -1), (0, 1, -1), (0, -1, 1)]
_W = [1 / 3] + [1 / 18] * 6 + [1 / 36] * 12


def _idx(c):
    return _C.index(tuple(c))


_OPP = [_idx((-a, -b, -c)) for a, b, c in _C]
_MX = [_idx((-a, b, c)) for a, b, c in _C]
_MY = [_idx((a, -b, c)) for a, b, c in _C]
_MZ = [_idx((a, b, -c)) for a, b, c in _C]

PERIODIC, WALL, SLIP, INLET, OUTLET = 0, 1, 2, 3, 4


@wp.func
def feq3(q: int, rho: float, ux: float, uy: float, uz: float, cxa: wp.array(dtype=int), cya: wp.array(dtype=int),
         cza: wp.array(dtype=int), wa: wp.array(dtype=float)) -> float:
    cu = float(cxa[q]) * ux + float(cya[q]) * uy + float(cza[q]) * uz
    uu = ux * ux + uy * uy + uz * uz
    return wa[q] * rho * (1.0 + 3.0 * cu + 4.5 * cu * cu - 1.5 * uu)


@wp.kernel
def k_init3(f: wp.array4d(dtype=float), cxa: wp.array(dtype=int), cya: wp.array(dtype=int), cza: wp.array(dtype=int),
            wa: wp.array(dtype=float), ux: float, uy: float, uz: float):
    z, y, x = wp.tid()
    for q in range(19):
        f[q, z, y, x] = feq3(q, 1.0, ux, uy, uz, cxa, cya, cza, wa)


@wp.func
def resolve(i: int, n: int, btype: int) -> int:
    # returns index, or -1 if outside & not periodic
    if i >= 0 and i < n:
        return i
    if btype == 0:
        return (i + n) % n
    if btype == 3 or btype == 4:
        return wp.clamp(i, 0, n - 1)
    return -1


@wp.kernel
def k_step3(fin: wp.array4d(dtype=float), fout: wp.array4d(dtype=float), solid: wp.array3d(dtype=wp.uint8),
            ux_o: wp.array3d(dtype=float), uy_o: wp.array3d(dtype=float), uz_o: wp.array3d(dtype=float),
            temp: wp.array3d(dtype=float), buoy: float, gfx: float, gfy: float, gfz: float,
            cxa: wp.array(dtype=int), cya: wp.array(dtype=int), cza: wp.array(dtype=int), wa: wp.array(dtype=float),
            oppa: wp.array(dtype=int), mxa: wp.array(dtype=int), mya: wp.array(dtype=int), mza: wp.array(dtype=int),
            nx: int, ny: int, nz: int, tau0: float, csmag2: float,
            bx0: int, bx1: int, by0: int, by1: int, bz0: int, bz1: int,
            uin_x: float, uin_y: float, uin_z: float,
            sp_axis: int, sp_start: int, sp_s: float):
    z, y, x = wp.tid()
    if solid[z, y, x] != wp.uint8(0):
        ux_o[z, y, x] = 0.0
        uy_o[z, y, x] = 0.0
        uz_o[z, y, x] = 0.0
        for q in range(19):
            fout[q, z, y, x] = wa[q]
        return
    f = vec19()
    for q in range(19):
        sx = x - cxa[q]
        sy = y - cya[q]
        sz = z - cza[q]
        qq = q
        # x faces
        btx = bx0
        if sx >= nx:
            btx = bx1
        bty = by0
        if sy >= ny:
            bty = by1
        btz = bz0
        if sz >= nz:
            btz = bz1
        bb = int(0)
        rx = resolve(sx, nx, btx)
        if rx < 0:
            if btx == 2:
                rx = x
                qq = mxa[qq]
            else:
                bb = 1
        ry = resolve(sy, ny, bty)
        if ry < 0:
            if bty == 2:
                ry = y
                qq = mya[qq]
            else:
                bb = 1
        rz = resolve(sz, nz, btz)
        if rz < 0:
            if btz == 2:
                rz = z
                qq = mza[qq]
            else:
                bb = 1
        if bb == 0:
            if solid[rz, ry, rx] != wp.uint8(0):
                bb = 1
        if bb != 0:
            f[q] = fin[oppa[q], z, y, x]
        else:
            f[q] = fin[qq, rz, ry, rx]
    rho = float(0.0)
    jx = float(0.0)
    jy = float(0.0)
    jz = float(0.0)
    for q in range(19):
        rho += f[q]
        jx += f[q] * float(cxa[q])
        jy += f[q] * float(cya[q])
        jz += f[q] * float(cza[q])
    Fx = gfx
    Fy = gfy + buoy * temp[z, y, x]
    Fz = gfz
    ux = (jx + 0.5 * Fx) / rho
    uy = (jy + 0.5 * Fy) / rho
    uz = (jz + 0.5 * Fz) / rho
    eq = int(0)
    if (bx0 == 3 and x == 0) or (bx1 == 3 and x == nx - 1) or (by0 == 3 and y == 0) or (by1 == 3 and y == ny - 1) or (bz0 == 3 and z == 0) or (bz1 == 3 and z == nz - 1):
        ux = uin_x
        uy = uin_y
        uz = uin_z
        eq = 1
    if (bx0 == 4 and x == 0) or (bx1 == 4 and x == nx - 1) or (by0 == 4 and y == 0) or (by1 == 4 and y == ny - 1) or (bz0 == 4 and z == 0) or (bz1 == 4 and z == nz - 1):
        rho = 1.0
        eq = 1
    if eq != 0:
        for q in range(19):
            f[q] = feq3(q, rho, ux, uy, uz, cxa, cya, cza, wa)
    pxx = float(0.0)
    pyy = float(0.0)
    pzz = float(0.0)
    pxy = float(0.0)
    pxz = float(0.0)
    pyz = float(0.0)
    for q in range(19):
        fn = f[q] - feq3(q, rho, ux, uy, uz, cxa, cya, cza, wa)
        cx = float(cxa[q])
        cy = float(cya[q])
        cz = float(cza[q])
        pxx += cx * cx * fn
        pyy += cy * cy * fn
        pzz += cz * cz * fn
        pxy += cx * cy * fn
        pxz += cx * cz * fn
        pyz += cy * cz * fn
    qn = wp.sqrt(pxx * pxx + pyy * pyy + pzz * pzz + 2.0 * (pxy * pxy + pxz * pxz + pyz * pyz))
    tau = 0.5 * (tau0 + wp.sqrt(tau0 * tau0 + 18.0 * 1.41421356 * csmag2 * qn / rho))
    om = 1.0 - 1.0 / tau
    s = float(0.0)
    if sp_axis >= 0:
        coord = x
        n = nx
        if sp_axis == 1:
            coord = y
            n = ny
        if sp_axis == 2:
            coord = z
            n = nz
        if coord > sp_start:
            t = float(coord - sp_start) / float(n - sp_start)
            s = sp_s * t * t
    for q in range(19):
        cx = float(cxa[q])
        cy = float(cya[q])
        cz = float(cza[q])
        fneq = 4.5 * wa[q] * ((cx * cx - 1.0 / 3.0) * pxx + (cy * cy - 1.0 / 3.0) * pyy + (cz * cz - 1.0 / 3.0) * pzz
                              + 2.0 * (cx * cy * pxy + cx * cz * pxz + cy * cz * pyz))
        fe = feq3(q, rho, ux, uy, uz, cxa, cya, cza, wa)
        cu = cx * ux + cy * uy + cz * uz
        fq = (1.0 - 0.5 / tau) * wa[q] * (3.0 * ((cx - ux) * Fx + (cy - uy) * Fy + (cz - uz) * Fz)
                                         + 9.0 * cu * (cx * Fx + cy * Fy + cz * Fz))
        fnew = fe + om * fneq + fq
        if s > 0.0:
            fnew = (1.0 - s) * fnew + s * feq3(q, 1.0, uin_x, uin_y, uin_z, cxa, cya, cza, wa)
        fout[q, z, y, x] = fnew
    ux_o[z, y, x] = ux
    uy_o[z, y, x] = uy
    uz_o[z, y, x] = uz


@wp.func
def wrapc(i: int, n: int, wrap: int) -> int:
    if wrap != 0:
        return (i % n + n) % n
    return wp.clamp(i, 0, n - 1)


@wp.func
def trilin(a: wp.array3d(dtype=float), px: float, py: float, pz: float, nx: int, ny: int, nz: int,
           wx: int, wy: int, wz: int) -> float:
    fx = wp.floor(px)
    fy = wp.floor(py)
    fz = wp.floor(pz)
    tx = px - fx
    ty = py - fy
    tz = pz - fz
    x0 = wrapc(int(fx), nx, wx)
    x1 = wrapc(int(fx) + 1, nx, wx)
    y0 = wrapc(int(fy), ny, wy)
    y1 = wrapc(int(fy) + 1, ny, wy)
    z0 = wrapc(int(fz), nz, wz)
    z1 = wrapc(int(fz) + 1, nz, wz)
    c00 = a[z0, y0, x0] * (1.0 - tx) + a[z0, y0, x1] * tx
    c10 = a[z0, y1, x0] * (1.0 - tx) + a[z0, y1, x1] * tx
    c01 = a[z1, y0, x0] * (1.0 - tx) + a[z1, y0, x1] * tx
    c11 = a[z1, y1, x0] * (1.0 - tx) + a[z1, y1, x1] * tx
    return (c00 * (1.0 - ty) + c10 * ty) * (1.0 - tz) + (c01 * (1.0 - ty) + c11 * ty) * tz


@wp.func
def vel_at(ux: wp.array3d(dtype=float), uy: wp.array3d(dtype=float), uz: wp.array3d(dtype=float),
           bx: float, by: float, bz: float, nx: int, ny: int, nz: int, wx: int, wy: int, wz: int) -> wp.vec3:
    return wp.vec3(trilin(ux, bx, by, bz, nx, ny, nz, wx, wy, wz), trilin(uy, bx, by, bz, nx, ny, nz, wx, wy, wz),
                   trilin(uz, bx, by, bz, nx, ny, nz, wx, wy, wz))


@wp.kernel
def k_sl3(c: wp.array3d(dtype=float), cout: wp.array3d(dtype=float),
          ux: wp.array3d(dtype=float), uy: wp.array3d(dtype=float), uz: wp.array3d(dtype=float),
          nx: int, ny: int, nz: int, r: float, dt: float, wx: int, wy: int, wz: int):
    """Semi-Lagrangian RK2 backtrace on a grid refined by factor r w.r.t. the velocity grid."""
    k, j, i = wp.tid()
    mx = nx * int(r)
    my = ny * int(r)
    mz = nz * int(r)
    # fine cell centre -> base-cell coordinates (cell-centred)
    bx = (float(i) + 0.5) / r - 0.5
    by = (float(j) + 0.5) / r - 0.5
    bz = (float(k) + 0.5) / r - 0.5
    v1 = vel_at(ux, uy, uz, bx, by, bz, nx, ny, nz, wx, wy, wz)
    v2 = vel_at(ux, uy, uz, bx - 0.5 * dt * v1[0], by - 0.5 * dt * v1[1], bz - 0.5 * dt * v1[2], nx, ny, nz, wx, wy, wz)
    sx = (bx - dt * v2[0] + 0.5) * r - 0.5
    sy = (by - dt * v2[1] + 0.5) * r - 0.5
    sz = (bz - dt * v2[2] + 0.5) * r - 0.5
    cout[k, j, i] = trilin(c, sx, sy, sz, mx, my, mz, wx, wy, wz)


@wp.kernel
def k_mc3(c: wp.array3d(dtype=float), cf: wp.array3d(dtype=float), cb: wp.array3d(dtype=float),
          cout: wp.array3d(dtype=float),
          ux: wp.array3d(dtype=float), uy: wp.array3d(dtype=float), uz: wp.array3d(dtype=float),
          nx: int, ny: int, nz: int, r: float, dt: float, wx: int, wy: int, wz: int, keep: float):
    k, j, i = wp.tid()
    mx = nx * int(r)
    my = ny * int(r)
    mz = nz * int(r)
    v = cf[k, j, i] + 0.5 * (c[k, j, i] - cb[k, j, i])
    bx = (float(i) + 0.5) / r - 0.5
    by = (float(j) + 0.5) / r - 0.5
    bz = (float(k) + 0.5) / r - 0.5
    v1 = vel_at(ux, uy, uz, bx, by, bz, nx, ny, nz, wx, wy, wz)
    v2 = vel_at(ux, uy, uz, bx - 0.5 * dt * v1[0], by - 0.5 * dt * v1[1], bz - 0.5 * dt * v1[2], nx, ny, nz, wx, wy, wz)
    sx = (bx - dt * v2[0] + 0.5) * r - 0.5
    sy = (by - dt * v2[1] + 0.5) * r - 0.5
    sz = (bz - dt * v2[2] + 0.5) * r - 0.5
    ix = int(wp.floor(sx))
    iy = int(wp.floor(sy))
    iz = int(wp.floor(sz))
    lo = float(1e9)
    hi = float(-1e9)
    for dz in range(2):
        for dy in range(2):
            for dx in range(2):
                cv = c[wrapc(iz + dz, mz, wz), wrapc(iy + dy, my, wy), wrapc(ix + dx, mx, wx)]
                lo = wp.min(lo, cv)
                hi = wp.max(hi, cv)
    cout[k, j, i] = wp.clamp(v, lo, hi) * keep


@wp.kernel
def k_source3(c: wp.array3d(dtype=float), px: float, py: float, pz: float, rad: float, amount: float, r: float,
              cap: float):
    """Add a soft spherical source (position/radius in base-cell coords) to a grid refined by r."""
    k, j, i = wp.tid()
    bx = (float(i) + 0.5) / r - 0.5
    by = (float(j) + 0.5) / r - 0.5
    bz = (float(k) + 0.5) / r - 0.5
    d2 = (bx - px) * (bx - px) + (by - py) * (by - py) + (bz - pz) * (bz - pz)
    if d2 < 9.0 * rad * rad:
        g = wp.exp(-d2 / (2.0 * rad * rad))
        c[k, j, i] = wp.min(c[k, j, i] + amount * g, cap)


@wp.kernel
def k_vortmag(ux: wp.array3d(dtype=float), uy: wp.array3d(dtype=float), uz: wp.array3d(dtype=float),
              out: wp.array3d(dtype=float), nx: int, ny: int, nz: int):
    z, y, x = wp.tid()
    xp = wp.min(x + 1, nx - 1)
    xm = wp.max(x - 1, 0)
    yp = wp.min(y + 1, ny - 1)
    ym = wp.max(y - 1, 0)
    zp = wp.min(z + 1, nz - 1)
    zm = wp.max(z - 1, 0)
    dwdy = 0.5 * (uz[z, yp, x] - uz[z, ym, x])
    dvdz = 0.5 * (uy[zp, y, x] - uy[zm, y, x])
    dudz = 0.5 * (ux[zp, y, x] - ux[zm, y, x])
    dwdx = 0.5 * (uz[z, y, xp] - uz[z, y, xm])
    dvdx = 0.5 * (uy[z, y, xp] - uy[z, y, xm])
    dudy = 0.5 * (ux[z, yp, x] - ux[z, ym, x])
    ox = dwdy - dvdz
    oy = dudz - dwdx
    oz = dvdx - dudy
    out[z, y, x] = wp.sqrt(ox * ox + oy * oy + oz * oz)


class LBM3D:
    def __init__(self, nx, ny, nz, nu, solid=None, bounds=(0, 0, 1, 4, 0, 0), csmag=0.15, u_init=(0, 0, 0),
                 u_in=(0, 0, 0), sponge=(-1, 0, 0.0), device="cuda:0"):
        self.nx, self.ny, self.nz = nx, ny, nz
        self.d = device
        self.tau0 = 3 * nu + 0.5
        self.csmag2 = csmag * csmag
        self.bounds = [int(b) for b in bounds]
        self.u_in = [float(u) for u in u_in]
        self.sponge = sponge  # (axis, start index, strength)
        mk = lambda a, t: wp.array(a, dtype=t, device=device)
        self.cx = mk([c[0] for c in _C], int)
        self.cy = mk([c[1] for c in _C], int)
        self.cz = mk([c[2] for c in _C], int)
        self.w = mk(_W, float)
        self.opp = mk(_OPP, int)
        self.mx = mk(_MX, int)
        self.my = mk(_MY, int)
        self.mz = mk(_MZ, int)
        if solid is None:
            self.solid = wp.zeros((nz, ny, nx), dtype=wp.uint8, device=device)
        else:
            self.solid = wp.array(solid.astype(np.uint8), dtype=wp.uint8, device=device)
        self.f0 = wp.zeros((19, nz, ny, nx), dtype=float, device=device)
        self.f1 = wp.zeros((19, nz, ny, nx), dtype=float, device=device)
        wp.launch(k_init3, dim=(nz, ny, nx), inputs=[self.f0, self.cx, self.cy, self.cz, self.w, *map(float, u_init)],
                  device=device)
        self.ux = wp.zeros((nz, ny, nx), dtype=float, device=device)
        self.uy = wp.zeros((nz, ny, nx), dtype=float, device=device)
        self.uz = wp.zeros((nz, ny, nx), dtype=float, device=device)
        self.temp = wp.zeros((nz, ny, nx), dtype=float, device=device)
        self.buoy = 0.0
        self.gforce = (0.0, 0.0, 0.0)
        self.t = 0

    @property
    def wrap(self):
        b = self.bounds
        return int(b[0] == 0), int(b[2] == 0), int(b[4] == 0)

    def step(self, n=1):
        b = self.bounds
        sp = self.sponge
        for _ in range(n):
            wp.launch(k_step3, dim=(self.nz, self.ny, self.nx),
                      inputs=[self.f0, self.f1, self.solid, self.ux, self.uy, self.uz, self.temp, float(self.buoy),
                              *map(float, self.gforce), self.cx, self.cy, self.cz, self.w, self.opp, self.mx, self.my,
                              self.mz, self.nx, self.ny, self.nz, self.tau0, self.csmag2, *b, *self.u_in,
                              int(sp[0]), int(sp[1]), float(sp[2])],
                      device=self.d)
            self.f0, self.f1 = self.f1, self.f0
            self.t += 1

    def vorticity_mag(self):
        out = wp.zeros((self.nz, self.ny, self.nx), dtype=float, device=self.d)
        wp.launch(k_vortmag, dim=(self.nz, self.ny, self.nx), inputs=[self.ux, self.uy, self.uz, out, self.nx, self.ny,
                                                                        self.nz], device=self.d)
        return out


class Scalar3D:
    """MacCormack-advected scalar on a grid refined by integer factor r over the LBM grid."""

    def __init__(self, sim: LBM3D, r=1, arr=None):
        self.sim = sim
        self.r = int(r)
        shape = (sim.nz * self.r, sim.ny * self.r, sim.nx * self.r)
        d = sim.d
        self.c = arr if arr is not None else wp.zeros(shape, dtype=float, device=d)
        self.t1 = wp.zeros(shape, dtype=float, device=d)
        self.t2 = wp.zeros(shape, dtype=float, device=d)
        self.dims = shape  # launch as (z, y, x) so x is fastest

    def advect(self, dt, keep=1.0):
        s = self.sim
        wx, wy, wz = s.wrap
        args = (s.ux, s.uy, s.uz, s.nx, s.ny, s.nz, float(self.r))
        wp.launch(k_sl3, dim=self.dims, inputs=[self.c, self.t1, *args, float(dt), wx, wy, wz], device=s.d)
        wp.launch(k_sl3, dim=self.dims, inputs=[self.t1, self.t2, *args, float(-dt), wx, wy, wz], device=s.d)
        # t2 now holds backward estimate; write result into t2's partner buffer
        out = wp.empty_like(self.c) if not hasattr(self, "t3") else self.t3
        self.t3 = out
        wp.launch(k_mc3, dim=self.dims, inputs=[self.c, self.t1, self.t2, out, *args, float(dt), wx, wy, wz, float(keep)],
                  device=s.d)
        self.c, self.t3 = out, self.c

    def add_source(self, p, rad, amount, cap=1e9):
        wp.launch(k_source3, dim=self.dims, inputs=[self.c, float(p[0]), float(p[1]), float(p[2]), float(rad),
                                                    float(amount), float(self.r), float(cap)], device=self.sim.d)


@wp.kernel
def k_init3_field(f: wp.array4d(dtype=float), ux: wp.array3d(dtype=float), uy: wp.array3d(dtype=float),
                  uz: wp.array3d(dtype=float), cxa: wp.array(dtype=int), cya: wp.array(dtype=int),
                  cza: wp.array(dtype=int), wa: wp.array(dtype=float)):
    z, y, x = wp.tid()
    for q in range(19):
        f[q, z, y, x] = feq3(q, 1.0, ux[z, y, x], uy[z, y, x], uz[z, y, x], cxa, cya, cza, wa)


def set_velocity(sim: LBM3D, ux, uy, uz):
    """Re-initialise distributions at equilibrium with a given velocity field ([z,y,x] arrays)."""
    a = [wp.array(np.ascontiguousarray(v, dtype=np.float32), dtype=float, device=sim.d) for v in (ux, uy, uz)]
    wp.launch(k_init3_field, dim=(sim.nz, sim.ny, sim.nx), inputs=[sim.f0, *a, sim.cx, sim.cy, sim.cz, sim.w],
              device=sim.d)


def curl_noise(shape, scale_cells, amp, seed=0, periodic=True):
    """Divergence-free random velocity field (curl of smoothed vector potential); shape=(nz,ny,nx)."""
    rng = np.random.default_rng(seed)
    nz, ny, nx = shape
    kz = np.fft.fftfreq(nz)[:, None, None]
    ky = np.fft.fftfreq(ny)[None, :, None]
    kx = np.fft.fftfreq(nx)[None, None, :]
    k2 = kx ** 2 + ky ** 2 + kz ** 2
    filt = np.exp(-k2 * (scale_cells ** 2) * 2 * np.pi ** 2)
    pots = []
    for _ in range(3):
        n = rng.standard_normal(shape)
        pots.append(np.real(np.fft.ifftn(np.fft.fftn(n) * filt)))
    ax, ay, az = pots
    g = lambda a, ax_: np.gradient(a, axis=ax_)
    ux = g(az, 1) - g(ay, 0)
    uy = g(ax, 0) - g(az, 2)
    uz = g(ay, 2) - g(ax, 1)
    m = np.sqrt(ux ** 2 + uy ** 2 + uz ** 2).std() + 1e-12
    return (ux / m * amp).astype(np.float32), (uy / m * amp).astype(np.float32), (uz / m * amp).astype(np.float32)
