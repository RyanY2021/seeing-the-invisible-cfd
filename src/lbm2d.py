"""2D lattice-Boltzmann solver (D2Q9, regularised BGK + Smagorinsky) on the GPU with NVIDIA Warp.

Also provides smoke-particle streaklines (advected with the simulated velocity) and a passive-scalar
MacCormack advector, used for the "real wind-tunnel smoke" look.

Layout: distributions f[q, y, x] (float32), velocity ux[y, x], uy[y, x].
"""
from __future__ import annotations

import math

import numpy as np

from common import init_warp

wp = init_warp()

vec9 = wp.types.vector(length=9, dtype=wp.float32)

_CX = [0, 1, 0, -1, 0, 1, -1, -1, 1]
_CY = [0, 0, 1, 0, -1, 1, 1, -1, -1]
_W = [4.0 / 9, 1.0 / 9, 1.0 / 9, 1.0 / 9, 1.0 / 9, 1.0 / 36, 1.0 / 36, 1.0 / 36, 1.0 / 36]
_OPP = [0, 3, 4, 1, 2, 7, 8, 5, 6]
_MIRY = [0, 1, 4, 3, 2, 8, 7, 6, 5]  # same cx, flipped cy (free-slip walls)


@wp.func
def feq_q(q: int, rho: float, ux: float, uy: float, cxa: wp.array(dtype=int), cya: wp.array(dtype=int),
          wa: wp.array(dtype=float)) -> float:
    cu = float(cxa[q]) * ux + float(cya[q]) * uy
    uu = ux * ux + uy * uy
    return wa[q] * rho * (1.0 + 3.0 * cu + 4.5 * cu * cu - 1.5 * uu)


@wp.kernel
def k_init(f: wp.array3d(dtype=float), ux0: wp.array2d(dtype=float), uy0: wp.array2d(dtype=float),
           cxa: wp.array(dtype=int), cya: wp.array(dtype=int), wa: wp.array(dtype=float)):
    y, x = wp.tid()
    for q in range(9):
        f[q, y, x] = feq_q(q, 1.0, ux0[y, x], uy0[y, x], cxa, cya, wa)


@wp.kernel
def k_step(fin: wp.array3d(dtype=float), fout: wp.array3d(dtype=float), solid: wp.array2d(dtype=wp.uint8),
           ux_o: wp.array2d(dtype=float), uy_o: wp.array2d(dtype=float),
           cxa: wp.array(dtype=int), cya: wp.array(dtype=int), wa: wp.array(dtype=float),
           oppa: wp.array(dtype=int), mirya: wp.array(dtype=int),
           nx: int, ny: int, tau0: float, csmag2: float,
           inlet: int, u_in: float, v_in: float, periodic_x: int, periodic_y: int,
           sponge_x0: int, sponge_s: float, fx: float, fy: float):
    y, x = wp.tid()
    if solid[y, x] != wp.uint8(0):
        ux_o[y, x] = 0.0
        uy_o[y, x] = 0.0
        for q in range(9):
            fout[q, y, x] = wa[q]
        return
    f = vec9()
    for q in range(9):
        sx = x - cxa[q]
        sy = y - cya[q]
        qq = q
        if periodic_x != 0:
            sx = (sx + nx) % nx
        else:
            sx = wp.clamp(sx, 0, nx - 1)
        if periodic_y != 0:
            sy = (sy + ny) % ny
        else:
            if sy < 0 or sy >= ny:
                # free-slip: specular reflection from the wall
                sy = y
                qq = mirya[q]
        if solid[sy, sx] != wp.uint8(0):
            f[q] = fin[oppa[q], y, x]
        else:
            f[q] = fin[qq, sy, sx]
    rho = float(0.0)
    jx = float(0.0)
    jy = float(0.0)
    for q in range(9):
        rho += f[q]
        jx += f[q] * float(cxa[q])
        jy += f[q] * float(cya[q])
    ux = (jx + 0.5 * fx) / rho
    uy = (jy + 0.5 * fy) / rho
    if inlet != 0 and x == 0:
        ux = u_in
        uy = v_in
        for q in range(9):
            f[q] = feq_q(q, rho, ux, uy, cxa, cya, wa)
    # non-equilibrium momentum flux
    pxx = float(0.0)
    pyy = float(0.0)
    pxy = float(0.0)
    for q in range(9):
        fn = f[q] - feq_q(q, rho, ux, uy, cxa, cya, wa)
        cx = float(cxa[q])
        cy = float(cya[q])
        pxx += cx * cx * fn
        pyy += cy * cy * fn
        pxy += cx * cy * fn
    qn = wp.sqrt(pxx * pxx + pyy * pyy + 2.0 * pxy * pxy)
    tau = 0.5 * (tau0 + wp.sqrt(tau0 * tau0 + 18.0 * 1.41421356 * csmag2 * qn / rho))
    om = 1.0 - 1.0 / tau
    s = float(0.0)
    if x > sponge_x0 and sponge_x0 > 0:
        t = float(x - sponge_x0) / float(nx - sponge_x0)
        s = sponge_s * t * t
    for q in range(9):
        cx = float(cxa[q])
        cy = float(cya[q])
        # regularised non-equilibrium part (2nd-order Hermite projection)
        fneq = 4.5 * wa[q] * ((cx * cx - 1.0 / 3.0) * pxx + (cy * cy - 1.0 / 3.0) * pyy + 2.0 * cx * cy * pxy)
        fe = feq_q(q, rho, ux, uy, cxa, cya, wa)
        fnew = fe + om * fneq
        if fx != 0.0 or fy != 0.0:
            # Guo forcing
            cu = cx * ux + cy * uy
            fq = (1.0 - 0.5 / tau) * wa[q] * (3.0 * ((cx - ux) * fx + (cy - uy) * fy) + 9.0 * cu * (cx * fx + cy * fy))
            fnew += fq
        if s > 0.0:
            fnew = (1.0 - s) * fnew + s * feq_q(q, 1.0, u_in, v_in, cxa, cya, wa)
        fout[q, y, x] = fnew
    ux_o[y, x] = ux
    uy_o[y, x] = uy


@wp.func
def sample_bilinear(a: wp.array2d(dtype=float), px: float, py: float, nx: int, ny: int, wrapx: int, wrapy: int) -> float:
    fx = wp.floor(px)
    fy = wp.floor(py)
    tx = px - fx
    ty = py - fy
    x0 = int(fx)
    y0 = int(fy)
    x1 = x0 + 1
    y1 = y0 + 1
    if wrapx != 0:
        x0 = (x0 % nx + nx) % nx
        x1 = (x1 % nx + nx) % nx
    else:
        x0 = wp.clamp(x0, 0, nx - 1)
        x1 = wp.clamp(x1, 0, nx - 1)
    if wrapy != 0:
        y0 = (y0 % ny + ny) % ny
        y1 = (y1 % ny + ny) % ny
    else:
        y0 = wp.clamp(y0, 0, ny - 1)
        y1 = wp.clamp(y1, 0, ny - 1)
    a00 = a[y0, x0]
    a10 = a[y0, x1]
    a01 = a[y1, x0]
    a11 = a[y1, x1]
    return (a00 * (1.0 - tx) + a10 * tx) * (1.0 - ty) + (a01 * (1.0 - tx) + a11 * tx) * ty


@wp.kernel
def k_advect_particles(pos: wp.array(dtype=wp.vec2), age: wp.array(dtype=float),
                       ux: wp.array2d(dtype=float), uy: wp.array2d(dtype=float), solid: wp.array2d(dtype=wp.uint8),
                       nx: int, ny: int, dt: float, wrapx: int, wrapy: int,
                       diff0: float, diff_age: float, seed: int, kill_x: float):
    i = wp.tid()
    a = age[i]
    if a < 0.0:
        return
    p = pos[i]
    u1x = sample_bilinear(ux, p[0], p[1], nx, ny, wrapx, wrapy)
    u1y = sample_bilinear(uy, p[0], p[1], nx, ny, wrapx, wrapy)
    mx = p[0] + 0.5 * dt * u1x
    my = p[1] + 0.5 * dt * u1y
    u2x = sample_bilinear(ux, mx, my, nx, ny, wrapx, wrapy)
    u2y = sample_bilinear(uy, mx, my, nx, ny, wrapx, wrapy)
    npx = p[0] + dt * u2x
    npy = p[1] + dt * u2y
    st = wp.rand_init(seed, i)
    d = diff0 + diff_age * a
    sig = wp.sqrt(2.0 * d * dt)
    npx += sig * wp.randn(st)
    npy += sig * wp.randn(st)
    if wrapx != 0:
        npx = npx - float(nx) * wp.floor(npx / float(nx))
    if wrapy != 0:
        npy = npy - float(ny) * wp.floor(npy / float(ny))
    ix = int(npx)
    iy = int(npy)
    if npx < 0.0 or npx >= kill_x or npy < 0.0 or npy >= float(ny) or ix >= nx or iy >= ny:
        age[i] = -1.0
        return
    if solid[iy, ix] != wp.uint8(0):
        # nudge out: keep previous position (sticks to the surface briefly)
        npx = p[0]
        npy = p[1]
    pos[i] = wp.vec2(npx, npy)
    age[i] = a + dt


@wp.kernel
def k_emit(pos: wp.array(dtype=wp.vec2), age: wp.array(dtype=float), src: wp.array(dtype=wp.vec2),
           head: int, nslots: int, jitter: float, seed: int, tag: wp.array(dtype=float), tagv: wp.array(dtype=float)):
    i = wp.tid()
    ns = src.shape[0]
    k = (head + i) % nslots
    s = src[i % ns]
    st = wp.rand_init(seed, i)
    pos[k] = wp.vec2(s[0] + jitter * wp.randn(st), s[1] + jitter * wp.randn(st))
    age[k] = 0.0
    tag[k] = tagv[i % ns]


@wp.kernel
def k_splat(pos: wp.array(dtype=wp.vec2), age: wp.array(dtype=float), tag: wp.array(dtype=float),
            img: wp.array2d(dtype=float), x0: float, y0: float, scale: float, Wd: int, Hd: int,
            decay: float, tagsel: float):
    i = wp.tid()
    a = age[i]
    if a < 0.0:
        return
    if tagsel >= 0.0 and wp.abs(tag[i] - tagsel) > 0.5:
        return
    p = pos[i]
    px = (p[0] - x0) * scale
    py = float(Hd) - 1.0 - (p[1] - y0) * scale
    if px < 0.0 or py < 0.0 or px >= float(Wd - 1) or py >= float(Hd - 1):
        return
    w = wp.exp(-a / decay)
    ix = int(px)
    iy = int(py)
    tx = px - float(ix)
    ty = py - float(iy)
    wp.atomic_add(img, iy, ix, w * (1.0 - tx) * (1.0 - ty))
    wp.atomic_add(img, iy, ix + 1, w * tx * (1.0 - ty))
    wp.atomic_add(img, iy + 1, ix, w * (1.0 - tx) * ty)
    wp.atomic_add(img, iy + 1, ix + 1, w * tx * ty)


@wp.kernel
def k_advect_scalar(c: wp.array2d(dtype=float), cout: wp.array2d(dtype=float), ux: wp.array2d(dtype=float),
                    uy: wp.array2d(dtype=float), nx: int, ny: int, dt: float, wrapx: int, wrapy: int):
    """Semi-Lagrangian backtrace (used twice for MacCormack)."""
    y, x = wp.tid()
    px = float(x) - dt * ux[y, x]
    py = float(y) - dt * uy[y, x]
    # midpoint (RK2) backtrace
    mx = float(x) - 0.5 * dt * ux[y, x]
    my = float(y) - 0.5 * dt * uy[y, x]
    umx = sample_bilinear(ux, mx, my, nx, ny, wrapx, wrapy)
    umy = sample_bilinear(uy, mx, my, nx, ny, wrapx, wrapy)
    px = float(x) - dt * umx
    py = float(y) - dt * umy
    cout[y, x] = sample_bilinear(c, px, py, nx, ny, wrapx, wrapy)


@wp.kernel
def k_maccormack(c: wp.array2d(dtype=float), cf: wp.array2d(dtype=float), cb: wp.array2d(dtype=float),
                 cout: wp.array2d(dtype=float), ux: wp.array2d(dtype=float), uy: wp.array2d(dtype=float),
                 nx: int, ny: int, dt: float, wrapx: int, wrapy: int):
    y, x = wp.tid()
    v = cf[y, x] + 0.5 * (c[y, x] - cb[y, x])
    # clamp to neighbourhood of the backtraced point (limiter)
    mx = float(x) - 0.5 * dt * ux[y, x]
    my = float(y) - 0.5 * dt * uy[y, x]
    umx = sample_bilinear(ux, mx, my, nx, ny, wrapx, wrapy)
    umy = sample_bilinear(uy, mx, my, nx, ny, wrapx, wrapy)
    px = float(x) - dt * umx
    py = float(y) - dt * umy
    ix = int(wp.floor(px))
    iy = int(wp.floor(py))
    lo = float(1e9)
    hi = float(-1e9)
    for j in range(2):
        for i in range(2):
            xx = ix + i
            yy = iy + j
            if wrapx != 0:
                xx = (xx % nx + nx) % nx
            else:
                xx = wp.clamp(xx, 0, nx - 1)
            if wrapy != 0:
                yy = (yy % ny + ny) % ny
            else:
                yy = wp.clamp(yy, 0, ny - 1)
            cv = c[yy, xx]
            lo = wp.min(lo, cv)
            hi = wp.max(hi, cv)
    cout[y, x] = wp.clamp(v, lo, hi)


@wp.kernel
def k_vorticity(ux: wp.array2d(dtype=float), uy: wp.array2d(dtype=float), w: wp.array2d(dtype=float), nx: int, ny: int):
    y, x = wp.tid()
    xp = wp.min(x + 1, nx - 1)
    xm = wp.max(x - 1, 0)
    yp = (y + 1) % ny
    ym = (y - 1 + ny) % ny
    w[y, x] = 0.5 * (uy[y, xp] - uy[y, xm]) - 0.5 * (ux[yp, x] - ux[ym, x])


class LBM2D:
    def __init__(self, nx, ny, nu, solid=None, u_init=None, periodic_x=False, periodic_y=True,
                 inlet=True, csmag=0.12, sponge_frac=0.12, sponge_s=0.05, device="cuda:0"):
        self.nx, self.ny = nx, ny
        self.device = device
        self.tau0 = 3.0 * nu + 0.5
        self.csmag2 = csmag * csmag
        self.periodic_x = int(periodic_x)
        self.periodic_y = int(periodic_y)
        self.inlet = int(inlet)
        self.sponge_x0 = int(nx * (1 - sponge_frac)) if sponge_frac > 0 else 0
        self.sponge_s = sponge_s
        self.cx = wp.array(_CX, dtype=int, device=device)
        self.cy = wp.array(_CY, dtype=int, device=device)
        self.w = wp.array(_W, dtype=float, device=device)
        self.opp = wp.array(_OPP, dtype=int, device=device)
        self.miry = wp.array(_MIRY, dtype=int, device=device)
        if solid is None:
            solid = np.zeros((ny, nx), np.uint8)
        self.solid = wp.array(solid.astype(np.uint8), dtype=wp.uint8, device=device)
        self.f0 = wp.zeros((9, ny, nx), dtype=float, device=device)
        self.f1 = wp.zeros((9, ny, nx), dtype=float, device=device)
        if u_init is None:
            u_init = (np.zeros((ny, nx), np.float32), np.zeros((ny, nx), np.float32))
        self.ux = wp.array(u_init[0].astype(np.float32), dtype=float, device=device)
        self.uy = wp.array(u_init[1].astype(np.float32), dtype=float, device=device)
        wp.launch(k_init, dim=(ny, nx), inputs=[self.f0, self.ux, self.uy, self.cx, self.cy, self.w], device=device)
        self.t = 0
        self.fx = 0.0
        self.fy = 0.0

    def step(self, u_in=0.0, v_in=0.0, n=1):
        for _ in range(n):
            wp.launch(k_step, dim=(self.ny, self.nx),
                      inputs=[self.f0, self.f1, self.solid, self.ux, self.uy, self.cx, self.cy, self.w, self.opp,
                              self.miry, self.nx, self.ny, self.tau0, self.csmag2, self.inlet, float(u_in),
                              float(v_in), self.periodic_x, self.periodic_y, self.sponge_x0, self.sponge_s,
                              float(self.fx), float(self.fy)],
                      device=self.device)
            self.f0, self.f1 = self.f1, self.f0
            self.t += 1

    def vorticity(self):
        w = wp.zeros((self.ny, self.nx), dtype=float, device=self.device)
        wp.launch(k_vorticity, dim=(self.ny, self.nx), inputs=[self.ux, self.uy, w, self.nx, self.ny], device=self.device)
        return w.numpy()


class Particles:
    """Ring-buffer of smoke particles emitted from fixed source points (streaklines)."""

    def __init__(self, nslots, device="cuda:0"):
        self.n = nslots
        self.device = device
        self.pos = wp.zeros(nslots, dtype=wp.vec2, device=device)
        self.age = wp.full(nslots, -1.0, dtype=float, device=device)
        self.tag = wp.zeros(nslots, dtype=float, device=device)
        self.head = 0
        self.seed = 1

    def emit(self, src_xy, per_source=1, jitter=0.3, tags=None):
        src = np.asarray(src_xy, np.float32).reshape(-1, 2)
        if tags is None:
            tags = np.zeros(len(src), np.float32)
        srcw = wp.array(src, dtype=wp.vec2, device=self.device)
        tagw = wp.array(np.asarray(tags, np.float32), dtype=float, device=self.device)
        cnt = len(src) * per_source
        self.seed += 1
        wp.launch(k_emit, dim=cnt, inputs=[self.pos, self.age, srcw, self.head, self.n, jitter, self.seed, self.tag, tagw],
                  device=self.device)
        self.head = (self.head + cnt) % self.n

    def advect(self, sim: LBM2D, dt, diff0=0.0, diff_age=0.0, kill_x=None):
        self.seed += 1
        wp.launch(k_advect_particles, dim=self.n,
                  inputs=[self.pos, self.age, sim.ux, sim.uy, sim.solid, sim.nx, sim.ny, float(dt), sim.periodic_x,
                          sim.periodic_y, float(diff0), float(diff_age), self.seed,
                          float(kill_x if kill_x is not None else sim.nx - 1)],
                  device=self.device)

    def splat(self, x0, y0, scale, Wd, Hd, decay=1e9, tagsel=-1.0):
        img = wp.zeros((Hd, Wd), dtype=float, device=self.device)
        wp.launch(k_splat, dim=self.n, inputs=[self.pos, self.age, self.tag, img, float(x0), float(y0), float(scale), Wd, Hd,
                                               float(decay), float(tagsel)], device=self.device)
        return img.numpy()


class Scalar:
    """Passive scalar advected with MacCormack on the LBM grid."""

    def __init__(self, sim: LBM2D, init):
        self.sim = sim
        d = sim.device
        self.c = wp.array(init.astype(np.float32), dtype=float, device=d)
        self.cf = wp.zeros_like(self.c)
        self.cb = wp.zeros_like(self.c)
        self.co = wp.zeros_like(self.c)

    def advect(self, dt):
        s = self.sim
        neg_ux = s.ux
        wp.launch(k_advect_scalar, dim=(s.ny, s.nx), inputs=[self.c, self.cf, s.ux, s.uy, s.nx, s.ny, float(dt),
                                                               s.periodic_x, s.periodic_y], device=s.device)
        wp.launch(k_advect_scalar, dim=(s.ny, s.nx), inputs=[self.cf, self.cb, s.ux, s.uy, s.nx, s.ny, float(-dt),
                                                               s.periodic_x, s.periodic_y], device=s.device)
        wp.launch(k_maccormack, dim=(s.ny, s.nx), inputs=[self.c, self.cf, self.cb, self.co, s.ux, s.uy, s.nx, s.ny,
                                                            float(dt), s.periodic_x, s.periodic_y], device=s.device)
        self.c, self.co = self.co, self.c

    def numpy(self):
        return self.c.numpy()


def cylinder_mask(nx, ny, cx, cy, r):
    yy, xx = np.mgrid[0:ny, 0:nx]
    return (((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2) <= r * r).astype(np.uint8)
