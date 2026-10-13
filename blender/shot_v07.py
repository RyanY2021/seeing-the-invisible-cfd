"""V07 — rule 2, VISCOSITY: a deck of lime edge-lit acrylic plates; Clawd pulls the top plate, and each plate
below is dragged along by the one above — later and slower (1D momentum diffusion between the layers). Neon
arrows on the front edges draw the velocity profile. Eevee.

blender.exe -b --factory-startup --python blender/shot_v07.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import clawd  # noqa: E402
import props  # noqa: E402
import rules_props as rp  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 150
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.06, tubes=None)
st.neon_tube([(-0.6, 0.7, 0.0), (-0.6, 0.7, 0.4)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.3, 0.8, 0.26), (0.8, 0.8, 0.26)], st.CYAN, 30.0, name="NeonB")
st.strip_softbox((0.1, -0.4, 0.3), size=(0.4, 0.05), energy=7.0, color=(1.0, 0.85, 0.75), target=(0.05, 0, 0.04),
                 name="Key", visible=False)

NL = 8                                   # plates (0 = bottom, glued to the table)
L, Dp, T = 0.18, 0.10, 0.0062
F0, F1 = 40, 150                         # Clawd pulls between these frames
PULL = 0.065

# ---------------------------------------------------------------- 1D momentum diffusion between the layers
dt = 1 / 24
sub = 20
Dn = 9.0                                 # layer-to-layer coupling (1/s): how strongly neighbours drag each other
u = np.zeros(NL)
disp = np.zeros((N + 2, NL))
vel = np.zeros((N + 2, NL))


def top_speed(f):
    """Clawd's pull: smooth ramp up, steady, ramp down"""
    x = (f - F0) / (F1 - F0)
    if x <= 0 or x >= 1:
        return 0.0
    return PULL / (F1 - F0) * 24 * 1.5 * (1 - (2 * x - 1) ** 2)


d = np.zeros(NL)
for f in range(1, N + 2):
    for _ in range(sub):
        u[-1] = top_speed(f)
        u[0] = 0.0
        lap = np.zeros(NL)
        lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
        u[1:-1] += Dn * lap[1:-1] * dt / sub
        d += u * dt / sub
    disp[f] = d
    vel[f] = u

# ---------------------------------------------------------------- the plates + velocity arrows
plates, arrows = [], []
for k in range(NL):
    ob = props.acrylic_block((0, 0, T * (k + 0.5)), (L, Dp, T - 0.0006), edge_color=st.LIME, edge_strength=1.3,
                             name=f"Plate{k}", tint=(0.85, 1.0, 0.7))
    plates.append(ob)
    if k > 0:
        a = rp.arrow(f"V{k}", (0.85, 1.0, 0.55), length=0.06, radius=0.0016, strength=9.0)
        a.location = (-0.03, -Dp / 2 - 0.012, T * (k + 0.5))
        arrows.append((k, a))
# tab on the top plate for Clawd to pull
bpy.ops.mesh.primitive_cube_add(size=1, location=(L / 2 + 0.008, 0, T * (NL - 0.5)))
tab = bpy.context.active_object
tab.scale = (0.016, 0.03, T * 0.8)
tab.data.materials.append(sc.principled("Tab", base=(0.012, 0.012, 0.016), rough=0.2, coat=1.0)[0])
vmax = np.abs(vel).max()
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
for f in range(1, N + 1):
    for k, ob in enumerate(plates):
        ob.location = (disp[f, k], 0, T * (k + 0.5))
        ob.keyframe_insert("location", frame=f)
    tab.location = (L / 2 + 0.008 + disp[f, -1], 0, T * (NL - 0.5))
    tab.keyframe_insert("location", frame=f)
    for k, a in arrows:
        s = max(vel[f, k] / vmax, 0.0)
        a.scale = (max(s * 1.2, 1e-3), 1, 1)
        a.keyframe_insert("scale", frame=f)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"

# ---------------------------------------------------------------- Clawd: walks up, grabs the tab, walks backwards pulling
U = 0.0042
y_c = -0.0
x_grab = L / 2 + 0.016 + 6 * U + 0.002
cl = clawd.Clawd("Clawd", unit=U, location=(0.36, y_c, 0), rotation_z=0)
cl.walk(4, 34, (0.36, y_c, 0), (x_grab, y_c, 0))
cl.look(30, -1, 0)
cl.arm(34, "L", 0)
cl.arm(40, "L", 20)
cl.tilt(36, 0)
cl.tilt(44, 12)                             # leans back, pulling
cl.walk(F0, F1, (x_grab, y_c, 0), (x_grab + disp[F1, -1], y_c, 0), step=6)
cl.tilt(F1 + 4, 0)
cl.arm(F1 + 4, "L", 0)
cl.look(F1 + 6, -1, -1)
cl.say(F1 + 10, "sticky!", 34)
cl.breathe(F1 + 10, N, 24, 0.03)

cam = sc.add_camera(lens=50.0, dof=22.0, clip=(0.01, 50))
tgt = sc.target_empty("T", (0.06, 0, 0.03))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = plates[NL // 2]
for f, loc, t in ((1, (0.02, -0.80, 0.20), (0.07, 0, 0.035)), (F0, (0.04, -0.74, 0.17), (0.07, 0, 0.035)),
                  (N, (0.08, -0.66, 0.14), (0.08, 0, 0.035))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V07")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V07_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
