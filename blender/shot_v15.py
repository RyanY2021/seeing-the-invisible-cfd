"""V15 — STEP 3, time steps: a giant glass display in the cell world plays the 2D simulation of flow past a
Clawd-shaped obstacle (glossy-paint dye, src/tex_v15.py). The camera starts on the pixel-Clawd in the flow and
pulls back to reveal the real Clawd watching its own wake ("that's me!"). Eevee. Writes hud.json (time step).

blender.exe -b --factory-startup --python blender/shot_v15.py -- <test|render> <first> <last> [samples]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import cellworld as cw  # noqa: E402
import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 200
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 8 * 48 + 24
TEX = sc.ROOT / "cache" / "v2" / "v15_tex"
PW, PH = 9.6, 3.6                                  # display size (m), texture aspect 2048:768
PZ = 0.35 + PH / 2

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
cw.build_world(scn, sun=(-160, 240, 26), sun_r=42, sky_strength=0.4, grid_strength=3.0)

# ---------------------------------------------------------------- the display: glossy black glass with the sim behind it
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, PZ), rotation=(math.pi / 2, 0, 0))
disp = bpy.context.active_object
disp.name = "Display"
disp.scale = (PW, PH, 1)
m, nt, out = sc.new_material("DisplayMat")
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.load(str(TEX / "0001.exr"))
img.source = "SEQUENCE"
tex.image = img
tex.image_user.frame_duration = N
tex.image_user.frame_start = 1
tex.image_user.frame_offset = 0
tex.image_user.use_auto_refresh = True
tex.interpolation = "Cubic"
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1)
p.inputs["Roughness"].default_value = 0.05
p.inputs["Coat Weight"].default_value = 1.0
p.inputs["Coat Roughness"].default_value = 0.02
nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
p.inputs["Emission Strength"].default_value = 1.0
nt.links.new(p.outputs[0], out.inputs["Surface"])
disp.data.materials.append(m)
# frame: thin edge-lit acrylic border + two feet
fr = 0.06
for (x, z, sx, sz) in ((0, PZ + PH / 2 + fr / 2, PW + 2 * fr, fr), (0, PZ - PH / 2 - fr / 2, PW + 2 * fr, fr),
                       (-PW / 2 - fr / 2, PZ, fr, PH), (PW / 2 + fr / 2, PZ, fr, PH)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0.0, z))
    b = bpy.context.active_object
    b.scale = (sx, 0.06, sz)
    b.data.materials.append(sc.emission_mat("FrameGlow", st.CYAN, 4.0))
for x in (-PW * 0.35, PW * 0.35):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0.0, 0.18))
    b = bpy.context.active_object
    b.scale = (0.12, 0.5, 0.36)
    b.data.materials.append(sc.principled("Foot", base=(0.01, 0.01, 0.015), rough=0.15, coat=1.0)[0])

# where the pixel-Clawd sits on the display (sim: CX = 0.24 NX, CY = NY/2)
OBST = ((0.24 - 0.5) * PW, -0.02, PZ)

# ---------------------------------------------------------------- Clawd (3D) in front of the display, lower left
U = 0.06
CL = (OBST[0] - 0.4, -1.4, 0.0)
cl = clawd.Clawd("Clawd", unit=U, location=CL, rotation_z=math.radians(150))   # facing the display
cl.look(1, 0, 1)
cl.breathe(1, 110, 24, 0.03)
cl.turn(112, math.radians(150))
cl.turn(124, math.radians(-15))                  # turns to us ...
cl.look(124, 0, 0)
cl.surprise(128)
cl.say(128, "that's me!", 40)
cl.arm(140, "L", 0)
cl.arm(148, "L", 70)                             # ... points at its silhouette in the flow
cl.arm(200, "L", 70)
cl.arm(212, "L", 0)
cl.turn(214, math.radians(-15))
cl.turn(226, math.radians(160))                  # back to watching the swirls
cl.look(226, 1, 1)
cl.breathe(230, N, 24, 0.03)
ck = sc.add_light("ClawdKey", "AREA", (CL[0] - 1.5, CL[1] - 3.0, 2.2), 180.0, color=(1.0, 0.8, 0.7), size=1.5,
                  target=(CL[0], CL[1], 0.4))
ck.data.specular_factor = 0.0
sc.add_light("RimMag", "AREA", (-7, 3, 4), 1500.0, color=st.MAGENTA, size=3.0, target=(0, 0, 1.5))

# ---------------------------------------------------------------- camera: on the pixel-Clawd -> pull back -> drift
cam = sc.add_camera(lens=35.0, dof=None, clip=(0.05, 2000))
tgt = sc.target_empty("T", OBST)
sc.track_to(cam, tgt)
keys = [(1, (OBST[0] + 1.0, -3.4, PZ + 0.1), (OBST[0] + 1.3, 0, PZ)),
        (100, (OBST[0] + 1.4, -4.4, PZ - 0.1), (OBST[0] + 1.5, 0, PZ - 0.2)),
        (160, (OBST[0] + 0.8, -6.5, 1.6), (OBST[0] + 1.6, 0, 1.4)),
        (N, (-0.5, -9.0, 1.9), (0.4, 0, PZ - 0.1))]
for f, loc, t in keys:
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V15")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
    steps = np.load(sc.ROOT / "cache" / "v2" / "v15_r1" / "meta.npz")["steps"]
    hud = {f: int(steps[min(f - 1 + 20, len(steps) - 1)]) for f in range(1, N + 1)}
    (out / "hud.json").write_text(json.dumps({"label": "TIME STEP", "values": hud}))
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V15_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
