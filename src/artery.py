"""S14 — carotid-like artery bifurcation: vessel mesh (SDF + marching cubes), streamlines and red-blood-cell paths.

Units: 1 = 4 mm. CCA along +z up to the bifurcation at the origin; ICA (with carotid bulb) to -x, ECA to +x.
  python artery.py -> cache/artery/vessel.ply, flow.npz (streamlines + RBC positions/orientations per frame)
"""
import numpy as np

from car_sdf import grid_eval, smin, write_ply
from common import cache_dir

import sys
NFR = int(sys.argv[1]) if len(sys.argv) > 1 else 190
OUTNAME = sys.argv[2] if len(sys.argv) > 2 else "artery"
FPS = 24


def bezier(p0, p1, p2, p3, n=80):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


CCA = bezier(np.array([0.3, 0, -9.0]), np.array([0.2, 0, -6]), np.array([0, 0, -3]), np.array([0, 0, 0.0]), 60)
ICA = bezier(np.array([0, 0, 0.0]), np.array([-0.6, 0.0, 1.6]), np.array([-1.9, 0.3, 4.2]), np.array([-2.2, 0.6, 9.0]), 80)
ECA = bezier(np.array([0, 0, 0.0]), np.array([0.7, 0.0, 1.4]), np.array([1.8, -0.2, 4.0]), np.array([2.6, -0.4, 9.0]), 80)


def radius_cca(u):
    return 1.0 + 0.0 * u


def radius_ica(u):  # carotid bulb near the origin of the ICA
    return 0.78 + 0.40 * np.exp(-((u - 0.16) / 0.11) ** 2) + 0.12 * (1 - u) * 0.3


def radius_eca(u):
    return 0.66 + 0.08 * (1 - u)


BRANCHES = [(CCA, radius_cca), (ICA, radius_ica), (ECA, radius_eca)]


def tube_sdf(pts, rfun, x, y, z):
    P = np.stack([x, y, z], -1)
    best = np.full(x.shape, 1e9)
    n = len(pts)
    for i in range(n - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        q = a + t[..., None] * ab
        d = np.linalg.norm(P - q, axis=-1) - rfun((i + t) / (n - 1))
        best = np.minimum(best, d)
    return best


def vessel_sdf(x, y, z):
    d = tube_sdf(CCA[::2], radius_cca, x, y, z)
    d = smin(d, tube_sdf(ICA[::2], radius_ica, x, y, z), 0.45)
    d = smin(d, tube_sdf(ECA[::2], radius_eca, x, y, z), 0.35)
    return d


def frames_along(path):
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    up = np.array([0.0, 1.0, 0.0])
    nrm = np.cross(t, up)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    bin_ = np.cross(t, nrm)
    return t, nrm, bin_


def resample(path, n):
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    ss = np.linspace(0, s[-1], n)
    return np.stack([np.interp(ss, s, path[:, k]) for k in range(3)], -1), s[-1]


def main():
    from skimage.measure import marching_cubes

    out = cache_dir(OUTNAME)
    h = 0.06
    vol, (xs, ys, zs) = grid_eval(vessel_sdf, (-3.8, -1.8, -9.2), (4.2, 2.2, 9.2), h)
    v, f, n, _ = marching_cubes(vol, 0.0, spacing=(h, h, h))
    v = v + np.array([xs[0], ys[0], zs[0]])
    write_ply(out / "vessel.ply", v, f[:, ::-1])
    print("vessel", len(v), len(f))

    rng = np.random.default_rng(3)
    # full paths: CCA + branch
    routes = []
    for br, rf in ((ICA, radius_ica), (ECA, radius_eca)):
        full = np.concatenate([CCA, br[1:]])
        rr = np.concatenate([radius_cca(np.linspace(0, 1, len(CCA))), rf(np.linspace(0, 1, len(br)))[1:]])
        fp, L = resample(full, 400)
        rr = np.interp(np.linspace(0, 1, 400), np.linspace(0, 1, len(rr)), rr)
        routes.append((fp, rr, L))
    # streamlines: seeds on a disc; x<0 -> ICA, x>0 -> ECA (flow split ~ 70/30 by area)
    stream = []
    for k in range(70):
        rho = np.sqrt(rng.uniform(0.02, 0.72))
        th = rng.uniform(0, 2 * np.pi)
        ri = 0 if np.cos(th) < 0.35 else 1
        fp, rr, L = routes[ri]
        t, nr, bn = frames_along(fp)
        off = (rho * rr)[:, None] * (np.cos(th) * nr + np.sin(th) * bn)
        stream.append(((fp + off).astype(np.float32), float(1 - rho * rho), ri))
    # red blood cells on random streamline-like paths, pulsatile advance
    NR = 700
    rbc_route = rng.integers(0, 2, NR)
    rbc_rho = np.sqrt(rng.uniform(0.0, 0.8, NR))
    rbc_th = rng.uniform(0, 2 * np.pi, NR)
    rbc_route = np.where(np.cos(rbc_th) < 0.35, 0, 1)
    s0 = rng.uniform(0, 1, NR)
    tt = np.arange(NFR) / FPS
    hz = 72 / 60.0
    # displacement (in path fraction): integral of U(t) = U0 * (0.55 + 0.45*max(sin)^2 ...) -> pulsatile
    ph = 2 * np.pi * hz * tt
    pulse = 0.45 + 0.9 * np.clip(np.sin(ph), 0, None) ** 2
    disp = np.cumsum(pulse) / FPS * 0.085
    pos = np.zeros((NFR, NR, 3), np.float32)
    rot = np.zeros((NFR, NR, 3), np.float32)
    spin = rng.uniform(-2, 2, (NR, 3))
    rot0 = rng.uniform(0, 2 * np.pi, (NR, 3))
    route_data = []
    for fp, rr, L in routes:
        t_, nr_, bn_ = frames_along(fp)
        route_data.append((fp, rr, nr_, bn_))
    for i in range(NR):
        fp, rr, nr_, bn_ = route_data[rbc_route[i]]
        sp = 1.0 - rbc_rho[i] ** 2  # parabolic profile
        s = (s0[i] + sp * disp) % 1.0
        idx = np.clip((s * 399).astype(int), 0, 399)
        off = (rbc_rho[i] * 0.92 * rr[idx])[:, None] * (np.cos(rbc_th[i]) * nr_[idx] + np.sin(rbc_th[i]) * bn_[idx])
        pos[:, i] = fp[idx] + off
        rot[:, i] = rot0[i] + spin[i] * tt[:, None]
    np.savez(out / "flow.npz", pos=pos, rot=rot,
             streams=np.stack([s[0] for s in stream]), speed=np.array([s[1] for s in stream]),
             pulse=pulse.astype(np.float32))
    print("flow saved")


if __name__ == "__main__":
    main()
