"""Moving rigid body for the 3D LBM (lbm3d.py): a box that pushes the fluid along with it.

Cells inside the (smooth-edged) box are relaxed towards equilibrium at the body velocity every step
(a direct-forcing / Brinkman-penalisation immersed body). Scalars (smoke, heat) are cleared inside the body.
Box given in base-lattice coordinates (x, y=up, z=depth), velocity in lattice units per step.
"""
import warp as wp

from lbm3d import feq3


@wp.func
def box_weight(px: float, py: float, pz: float, cx: float, cy: float, cz: float, hx: float, hy: float, hz: float,
               ramp: float) -> float:
    dx = wp.abs(px - cx) - hx
    dy = wp.abs(py - cy) - hy
    dz = wp.abs(pz - cz) - hz
    d = wp.max(dx, wp.max(dy, dz))          # box SDF (inside < 0), good enough near the surface
    return wp.clamp(0.5 - d / ramp, 0.0, 1.0)


@wp.kernel
def k_body(f: wp.array4d(dtype=float), cxa: wp.array(dtype=int), cya: wp.array(dtype=int), cza: wp.array(dtype=int),
           wa: wp.array(dtype=float), cx: float, cy: float, cz: float, hx: float, hy: float, hz: float,
           ux: float, uy: float, uz: float, ramp: float, x0: int, y0: int, z0: int):
    k, j, i = wp.tid()
    x = i + x0
    y = j + y0
    z = k + z0
    if x < 0 or y < 0 or z < 0 or x >= f.shape[3] or y >= f.shape[2] or z >= f.shape[1]:
        return
    a = box_weight(float(x), float(y), float(z), cx, cy, cz, hx, hy, hz, ramp)
    if a <= 0.0:
        return
    rho = float(0.0)
    for q in range(19):
        rho += f[q, z, y, x]
    for q in range(19):
        f[q, z, y, x] = (1.0 - a) * f[q, z, y, x] + a * feq3(q, rho, ux, uy, uz, cxa, cya, cza, wa)


@wp.kernel
def k_clear(c: wp.array3d(dtype=float), r: float, cx: float, cy: float, cz: float, hx: float, hy: float, hz: float,
            ramp: float, x0: int, y0: int, z0: int):
    k, j, i = wp.tid()
    x = i + x0
    y = j + y0
    z = k + z0
    if x < 0 or y < 0 or z < 0 or x >= c.shape[2] or y >= c.shape[1] or z >= c.shape[0]:
        return
    a = box_weight((float(x) + 0.5) / r - 0.5, (float(y) + 0.5) / r - 0.5, (float(z) + 0.5) / r - 0.5,
                   cx, cy, cz, hx, hy, hz, ramp)
    if a > 0.0:
        c[z, y, x] = c[z, y, x] * (1.0 - a)


def apply_body(sim, centre, half, vel, ramp=1.5, scalars=()):
    """centre/half in base lattice (x, up, depth); vel in lattice units/step; scalars: Scalar3D objects to clear"""
    cx, cy, cz = centre
    hx, hy, hz = half
    pad = 3
    x0, x1 = int(cx - hx - pad), int(cx + hx + pad) + 1
    y0, y1 = int(cy - hy - pad), int(cy + hy + pad) + 1
    z0, z1 = int(cz - hz - pad), int(cz + hz + pad) + 1
    if x1 < 0 or y1 < 0 or z1 < 0 or x0 >= sim.nx or y0 >= sim.ny or z0 >= sim.nz:
        return
    wp.launch(k_body, dim=(z1 - z0, y1 - y0, x1 - x0),
              inputs=[sim.f0, sim.cx, sim.cy, sim.cz, sim.w, float(cx), float(cy), float(cz), float(hx), float(hy),
                      float(hz), float(vel[0]), float(vel[1]), float(vel[2]), float(ramp), x0, y0, z0], device=sim.d)
    for s in scalars:
        r = s.r
        wp.launch(k_clear, dim=((z1 - z0) * r, (y1 - y0) * r, (x1 - x0) * r),
                  inputs=[s.c, float(r), float(cx), float(cy), float(cz), float(hx), float(hy), float(hz), float(ramp),
                          x0 * r, y0 * r, z0 * r], device=sim.d)
