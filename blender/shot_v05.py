"""V05 — "does air follow rules?": a river of neon streaks flows around a black pillar (potential flow past a
cylinder); Clawd sits on the pillar. One glowing parcel rides the flow, the camera follows it — then time freezes
and the camera circles the parcel ("…and ask: what pushes it?"). Eevee.

blender.exe -b --factory-startup --python blender/shot_v05.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import clawd  # noqa: E402
import rules_props as rp  # noqa: E402
import scene_common as sc  # noqa: E402
import streaks as sk  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 100
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24
FREEZE = int(2.75 * 48)            # bar 24.75: the world stops, the camera keeps moving

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.12, tubes=None)
st.neon_tube([(-0.9, 0.9, 0.0), (-0.9, 0.9, 0.5)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.5, 1.0, 0.32), (1.1, 1.0, 0.32)], st.CYAN, 30.0, name="NeonB")
st.strip_softbox((-0.2, -0.35, 0.3), size=(0.3, 0.05), energy=6.0, color=(1.0, 0.82, 0.72), target=(0, 0, 0.09),
                 name="ClawdKey", visible=False)

# ---------------------------------------------------------------- potential flow past a vertical cylinder
a_r, U = 0.035, 0.075


def vel(p):
    x, y = p[:, 0], p[:, 1]
    r2 = np.maximum(x * x + y * y, a_r * a_r * 1.0001)
    a2 = a_r * a_r
    u = U * (1 - a2 * (x * x - y * y) / r2 ** 2)
    v = -U * 2 * a2 * x * y / r2 ** 2
    return np.stack([u, v, np.zeros_like(u)], -1)


def seed(k, rng):
    return np.stack([rng.uniform(-0.75, -0.55, k), rng.uniform(-0.2, 0.2, k), rng.uniform(0.004, 0.062, k)], -1)   # below the pillar top: Clawd sits above the river


seed.outside = lambda p: (p[:, 0] > 0.75) | (p[:, 0] ** 2 + p[:, 1] ** 2 < a_r ** 2)
rng = np.random.default_rng(5)
n_p = 900
# pre-roll so the river is already full at frame 1
heads, tails = sk.trace(vel, lambda k, r: seed(k, r) + np.stack([r.uniform(0, 1.3, k), np.zeros(k), np.zeros(k)], -1)
                        if k == n_p else seed(k, r), n_p, N + 40, tail_frames=12, rng=rng)
idx = np.minimum(np.arange(N + 1), FREEZE)          # frozen after FREEZE
heads, tails = heads[idx], tails[idx]
cols = np.array([st.CYAN, (0.75, 0.9, 1.0), st.VIOLET, (0.9, 0.95, 1.0)], np.float32)[rng.integers(0, 4, n_p)]
cam = sc.add_camera(lens=40.0, dof=22.0, clip=(0.01, 50))
S = sk.Streaks("Flow", heads, tails, sk.streak_material(strength=7.0), width=0.0013, colors=cols, cam=cam)
sk.register()

# ---------------------------------------------------------------- pillar + Clawd on top
rp.pillar(a_r, 0.07, (0, 0, 0), ring=st.MAGENTA)
cl = clawd.Clawd("Clawd", unit=0.0042, location=(0, 0.004, 0.07), rotation_z=math.radians(-10))
cl.say(6, "does air follow rules?", 52)
cl.look(1, -1, 0)
cl.blink(70)

# ---------------------------------------------------------------- the parcel: follows the flow, then freezes
par = rp.parcel(0.02, st.CYAN, "Parcel")
p = np.array([[-0.62, -0.05, 0.05]])
path = []
for f in range(N + 1):
    path.append(p[0].copy())
    if f < FREEZE:
        for _ in range(4):
            k1 = vel(p)
            k2 = vel(p + 0.5 / 96 * k1)
            p = p + k2 / 96
path = np.array(path)
rp.smooth_path_keys(par, path[1:], range(1, N + 1))
for f in range(1, N + 1, 6):                    # slow tumble while moving
    par.rotation_euler = (0.25 * math.sin(min(f, FREEZE) * 0.05), 0.0, min(f, FREEZE) * 0.012)
    par.keyframe_insert("rotation_euler", frame=f)
# Clawd's eyes follow the parcel past the pillar, then a surprised look when time stops
cl.look(40, -1, 0)
cl.look(78, 0, -1)
cl.look(104, 1, -1)
cl.surprise(FREEZE + 2)
cl.tilt(FREEZE + 4, 8)

# ---------------------------------------------------------------- camera: wide -> follow the parcel -> orbit it
tgt = sc.target_empty("T", (0, 0, 0.04))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = par
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
for f in range(1, N + 1, 4):
    pp = path[min(f, len(path) - 1)]
    w = min(1.0, max(0.0, (f - 30) / 60))
    t = (1 - w) * np.array([-0.05, 0, 0.05]) + w * pp
    tgt.location = tuple(t)
    tgt.keyframe_insert("location", frame=f)
    if f <= FREEZE:
        cam.location = (t[0] - 0.06 + 0.1 * (1 - w), -0.42 + 0.14 * w, 0.12 - 0.03 * w)
    else:
        ang = (f - FREEZE) / (N - FREEZE) * math.radians(75)
        r = 0.28 - 0.06 * (f - FREEZE) / (N - FREEZE)
        cam.location = (pp[0] - r * math.sin(ang) - 0.06 * math.cos(ang), pp[1] - r * math.cos(ang), 0.09 + 0.02 * ang)
    cam.keyframe_insert("location", frame=f)
sc.smooth_keys(cam)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V05")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V05_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
