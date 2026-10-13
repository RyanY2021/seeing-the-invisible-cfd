"""V13 — STEP 1, cells: in the cell world, space around the black car dices itself into edge-lit acrylic cells,
one refinement level per half bar (big cubes first, then splitting finer and finer near the body). The camera
orbits; Clawd watches — and bursts into its own voxels for a moment ("I'm made of cells too!"). Eevee.
Writes renders/V13/hud.json (cell count per frame) for the compositor's pixel counter.

blender.exe -b --factory-startup --python blender/shot_v13.py -- <test|render> <first> <last> [samples]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import car_common as cc  # noqa: E402
import cellworld as cw  # noqa: E402
import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 200
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 6 * 48 + 24
T_LEVEL = [30, 54, 78, 102, 126, 150]            # each level appears on a half-bar
EXPLODE = 196

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
cw.build_world(scn)

d = np.load(sc.ROOT / "cache" / "v2" / "octree_car.npz")
nodes, cells = d["nodes"], d["cells"]
is_split = np.zeros(len(nodes), bool)
par = nodes[:, 5].astype(int)
is_split[par[par >= 0]] = True
leaf_keys = {tuple(np.round(c[:4], 4)) for c in cells}
is_leaf = np.array([tuple(np.round(n[:4], 4)) in leaf_keys for n in nodes])
levels = nodes[:, 4].astype(int)
count = {}
for L in range(6):
    split = nodes[(levels == L) & is_split]
    leaf = nodes[(levels == L) & is_leaf & ~is_split]
    for kind, arr in (("split", split), ("leaf", leaf)):
        if len(arr) == 0:
            continue
        ob = cw.cells_mesh(arr[:, :5], name=f"Cells_{kind}{L}")
        m = cw.acrylic_cell_material(f"CellMat_{kind}{L}", edge_strength=2.6, face_alpha=0.016)
        ob.data.materials.append(m)
        t0 = T_LEVEL[L]
        cw.key_vis(m, 1, 0.0)
        cw.key_vis(m, t0 - 1, 0.0)
        cw.key_vis(m, t0 + 2, 2.4)              # flash on arrival
        cw.key_vis(m, t0 + 10, 1.0)
        if kind == "split":
            t1 = T_LEVEL[L + 1]
            cw.key_vis(m, t1, 1.0)
            cw.key_vis(m, t1 + 4, 0.0)          # splits into its children
# visible cell count per frame (for the HUD)
hud = {}
for f in range(1, N + 1):
    Lc = max([L for L in range(6) if T_LEVEL[L] <= f], default=-1)
    if Lc < 0:
        hud[f] = 0
        continue
    n_leaf = int(((levels <= Lc) & is_leaf & ~is_split).sum())
    n_split = int(((levels == Lc) & is_split).sum())
    hud[f] = n_leaf + n_split

body = cc.body_material(color=(0.006, 0.006, 0.008), rough=0.1, coat=1.0)
car, _, _ = cc.build_car(body_mat=body)
st.strip_softbox((2.2, 0.0, 4.5), size=(6.0, 0.25), energy=900.0, target=(2.2, 0, 0), name="TopStrip", visible=False)
sc.add_light("RimMag", "AREA", (-4, 3, 2.5), 1500.0, color=st.MAGENTA, size=2.0, target=(2, 0, 0.6))
rc = sc.add_light("RimCyan", "AREA", (9, -2, 2.0), 1500.0, color=st.CYAN, size=2.0, target=(2, 0, 0.6))
rc.visible_glossy = False
sc.add_light("ClawdKey", "AREA", (-3.5, -5.0, 2.5), 250.0, color=(1.0, 0.8, 0.7), size=1.5, target=(-1.6, -2.2, 0.4))

U = 0.07
cl = clawd.Clawd("Clawd", unit=U, location=(-1.7, -2.3, 0.0), rotation_z=math.radians(-30))
sk = clawd.add_explode(cl, amount=0.55)
clawd.explode_key(cl, sk, 1, 0.0)
cl.look(1, 1, 1)
for L, t in enumerate(T_LEVEL):
    cl.squash_to(t - 1, 1.0)
    cl.squash_to(t + 1, 0.92)                  # flinches a little with every split
    cl.squash_to(t + 6, 1.0)
cl.look(160, 0, 0)
cl.look(176, 0, -1)                             # looks down at itself ...
cl.say(EXPLODE - 6, "I'm made of cells too!", 60)
clawd.explode_key(cl, sk, EXPLODE - 1, 0.0)
clawd.explode_key(cl, sk, EXPLODE + 5, 1.0)     # ... and bursts into voxels
clawd.explode_key(cl, sk, EXPLODE + 16, 1.0)
clawd.explode_key(cl, sk, EXPLODE + 24, 0.0)
cl.cues.append((EXPLODE + 5, "burst"))
cl.look(EXPLODE + 30, 1, 1)
cl.hop(EXPLODE + 34, EXPLODE + 46, (-1.7, -2.3, 0), (-1.7, -2.3, 0), height=0.25)
cl.breathe(EXPLODE + 50, N, 24, 0.03)

cam = sc.add_camera(lens=32.0, dof=None, clip=(0.05, 2000))
tgt = sc.target_empty("T", (2.0, 0.6, 1.0))
sc.track_to(cam, tgt)
for f, ang, dist, h in ((1, -150, 11.5, 2.6), (150, -128, 10.5, 2.4), (N, -108, 9.5, 2.0)):
    a = math.radians(ang)
    cam.location = (2.2 + dist * math.cos(a) * 0.75, dist * math.sin(a), h)
    cam.keyframe_insert("location", frame=f)
sc.smooth_keys(cam)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V13")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
    (out / "hud.json").write_text(json.dumps({"label": "CELLS · DEMO", "values": hud}))
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V13_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
