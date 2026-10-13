"""V17 — resolution & cost: three glass displays in the cell world play the same Clawd-flow at 128x48, 512x192 and
2048x768 cells (coarse ones as chunky pixels). The camera dollies from coarse to fine; Clawd walks along and ends
up fanning a glowing-hot chip ("phew!"). Eevee.

blender.exe -b --factory-startup --python blender/shot_v17.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import cellworld as cw  # noqa: E402
import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 150
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 6 * 48 + 24
TEX = sc.ROOT / "cache" / "v2" / "v17_tex"
FONT = str(sc.ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
PW, PH = 4.8, 1.8
PZ = 0.45 + PH / 2
XS = {16: -6.0, 4: 0.0, 1: 6.0}
LABEL = {16: "128 × 48 cells", 4: "512 × 192 cells", 1: "2048 × 768 cells"}

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
cw.build_world(scn, sun=(0, 260, 24), sun_r=44, sky_strength=0.4, grid_strength=3.0)
sc.add_light("RimMag", "AREA", (-9, 3, 4), 1500.0, color=st.MAGENTA, size=3.0, target=(-4, 0, 1.2))
sc.add_light("RimCyan", "AREA", (10, 3, 4), 1500.0, color=st.CYAN, size=3.0, target=(4, 0, 1.2))


def display(div, x):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, 0, PZ), rotation=(math.pi / 2, 0, 0))
    d = bpy.context.active_object
    d.scale = (PW, PH, 1)
    m, nt, out = sc.new_material(f"Disp{div}")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(str(TEX / f"r{div}" / "0001.exr"))
    img.source = "SEQUENCE"
    tex.image = img
    tex.image_user.frame_duration = N
    tex.image_user.frame_start = 1
    tex.image_user.use_auto_refresh = True
    tex.interpolation = "Closest" if div > 1 else "Cubic"
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0, 0, 0, 1)
    p.inputs["Roughness"].default_value = 0.05
    p.inputs["Coat Weight"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = 1.0
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    d.data.materials.append(m)
    fr = 0.04
    for (dx, dz, sx, sz) in ((0, PH / 2 + fr / 2, PW + 2 * fr, fr), (0, -PH / 2 - fr / 2, PW + 2 * fr, fr),
                             (-PW / 2 - fr / 2, 0, fr, PH), (PW / 2 + fr / 2, 0, fr, PH)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + dx, 0.0, PZ + dz))
        b = bpy.context.active_object
        b.scale = (sx, 0.05, sz)
        b.data.materials.append(sc.emission_mat(f"Frame{div}", st.CYAN if div == 1 else st.VIOLET, 4.0))
    st.neon_text([LABEL[div]], FONT, 0.16, (x, -0.1, 0.12), st.CYAN if div == 1 else st.MAGENTA, strength=14.0,
                 board=False, name=f"Lab{div}", light_energy=0.0, per_word=False)


for div, x in XS.items():
    display(div, x)

# the chip: a 'GPU' that heats up as the grid gets finer
CHIP = (XS[1] + PW / 2 + 1.0, -0.6, 0.0)
bpy.ops.mesh.primitive_cube_add(size=1, location=(CHIP[0], CHIP[1], 0.09))
chip = bpy.context.active_object
chip.scale = (0.9, 0.9, 0.18)
m, nt, out = sc.new_material("Chip")
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1)
p.inputs["Roughness"].default_value = 0.3
p.inputs["Coat Weight"].default_value = 0.8
p.inputs["Emission Color"].default_value = (1.0, 0.35, 0.08, 1)
heat = p.inputs["Emission Strength"]
for f, v in ((1, 0.0), (150, 0.0), (200, 1.0), (250, 3.5), (N, 5.0)):
    heat.default_value = v
    heat.keyframe_insert("default_value", frame=f)
nt.links.new(p.outputs[0], out.inputs["Surface"])
chip.data.materials.append(m)
for k in range(8):                                   # gold pins
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(CHIP[0] - 0.39 + 0.11 * k, CHIP[1] + side * 0.48, 0.03))
        pin = bpy.context.active_object
        pin.scale = (0.05, 0.08, 0.03)
        pin.data.materials.append(sc.principled("Gold", base=(1.0, 0.7, 0.25), rough=0.25, metal=1.0)[0])
glow = bpy.data.lights.new("ChipGlow", "POINT")
glow.color = (1.0, 0.4, 0.1)
glow.shadow_soft_size = 0.5
glow.specular_factor = 0.0
gl = bpy.data.objects.new("ChipGlow", glow)
gl.location = (CHIP[0], CHIP[1], 0.6)
sc.link(gl)
for f, v in ((1, 0.0), (150, 0.0), (250, 400.0), (N, 600.0)):
    glow.energy = v
    glow.keyframe_insert("energy", frame=f)

# Clawd walks along under the displays, stops by the chip and fans it
U = 0.055
cl = clawd.Clawd("Clawd", unit=U, location=(XS[16] - 1.5, -1.4, 0), rotation_z=math.radians(-10))
cl.walk(10, 230, (XS[16] - 1.5, -1.4, 0), (CHIP[0] - 1.0, -1.4, 0), step=6)
cl.look(10, 0, 1)
cl.look(120, 1, 1)
cl.look(230, 1, -1)
cl.turn(236, math.radians(30))
cl.surprise(240)
cl.wave(246, N, "R", period=6, amp=70)             # fanning the hot chip
cl.say(250, "phew!", 40)
ck = sc.add_light("ClawdKey", "AREA", (0, 0, 0), 150.0, color=(1.0, 0.85, 0.75), size=20.0)   # size in Clawd units
ck.data.specular_factor = 0.0
ck.parent = cl.root                                  # the key light travels with Clawd
ck.location = (-20.0, -30.0, 30.0)                   # in Clawd units (root is scaled by U)
ck.rotation_euler = (math.radians(50), 0, math.radians(-35))

cam = sc.add_camera(lens=32.0, dof=None, clip=(0.05, 2000))
tgt = sc.target_empty("T", (XS[16], 0, PZ))
sc.track_to(cam, tgt)
for f, loc, t in ((1, (XS[16] - 1.5, -5.6, 1.7), (XS[16], 0, PZ - 0.1)),
                  (110, (XS[4] - 1.0, -5.8, 1.7), (XS[4], 0, PZ - 0.1)),
                  (210, (XS[1] - 0.5, -6.0, 1.7), (XS[1] + 0.4, 0, PZ - 0.2)),
                  (N, (XS[1] + 1.4, -6.6, 1.6), (XS[1] + 1.6, 0, 0.9))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V17")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V17_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
