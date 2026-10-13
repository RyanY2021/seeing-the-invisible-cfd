"""V12 — "can a computer solve it?": a glossy retro monitor on the neon table shows the cell world (scanlines);
Clawd walks up and hops INTO the screen (shrinks into it with a flash); the camera pushes in until the screen fills
the frame (the edit pixel-dissolves into V13). Eevee.

blender.exe -b --factory-startup --python blender/shot_v12.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 150
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24
SCREEN_IMG = sc.ROOT / "cache" / "lookdev_v2" / "cellworld_eevee.png"
SW, SH = 0.24, 0.135                     # screen size (16:9)
SZ = 0.03 + SH / 2                       # screen centre height
JUMP = (150, 168)                        # Clawd hops into the screen

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.08, tubes=None)
st.neon_tube([(-0.7, 0.6, 0.0), (-0.7, 0.6, 0.42)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.35, 0.7, 0.30), (0.9, 0.7, 0.30)], st.CYAN, 30.0, name="NeonB")
ck = sc.add_light("ClawdKey", "AREA", (-0.30, -0.55, 0.30), 9.0, color=(1.0, 0.84, 0.74), size=0.4,
                  target=(-0.16, -0.14, 0.03))
ck.data.specular_factor = 0.0

# ---------------------------------------------------------------- the monitor
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.06, SZ))
body = bpy.context.active_object
body.scale = (SW + 0.04, 0.12, SH + 0.05)
bpy.ops.object.transform_apply(scale=True)
bv = body.modifiers.new("b", "BEVEL")
bv.width = 0.012
bv.segments = 6
body.data.materials.append(sc.principled("MonitorBody", base=(0.008, 0.006, 0.012), rough=0.15, coat=1.0)[0])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.0002, SZ), rotation=(math.pi / 2, 0, 0))
scr = bpy.context.active_object
scr.scale = (SW, SH, 1)
m, nt, out = sc.new_material("Screen")
tc = nt.nodes.new("ShaderNodeTexCoord")
tex0 = nt.nodes.new("ShaderNodeTexImage")              # the cell world, empty ...
tex0.image = bpy.data.images.load(str(SCREEN_IMG).replace("cellworld_eevee", "cellworld_eevee_noclawd"))
tex1 = nt.nodes.new("ShaderNodeTexImage")              # ... and with Clawd in it, once it has hopped in
tex1.image = bpy.data.images.load(str(SCREEN_IMG))
for t_ in (tex0, tex1):
    nt.links.new(tc.outputs["UV"], t_.inputs["Vector"])
swap = nt.nodes.new("ShaderNodeValue")
for f_, v_ in ((1, 0.0), (JUMP[1], 0.0), (JUMP[1] + 1, 1.0)):
    swap.outputs[0].default_value = v_
    swap.outputs[0].keyframe_insert("default_value", frame=f_)
tex = nt.nodes.new("ShaderNodeMix")
tex.data_type = "RGBA"
nt.links.new(swap.outputs[0], tex.inputs["Factor"])
nt.links.new(tex0.outputs["Color"], tex.inputs["A"])
nt.links.new(tex1.outputs["Color"], tex.inputs["B"])
# scanlines: brightness x (0.8 + 0.2 sin(v * 2pi * 180))
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["UV"], sep.inputs[0])
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = 2 * math.pi * 180
nt.links.new(sep.outputs["Y"], mul.inputs[0])
sn = nt.nodes.new("ShaderNodeMath")
sn.operation = "SINE"
nt.links.new(mul.outputs[0], sn.inputs[0])
sl = nt.nodes.new("ShaderNodeMath")
sl.operation = "MULTIPLY_ADD"
sl.inputs[1].default_value = 0.18
sl.inputs[2].default_value = 0.82
nt.links.new(sn.outputs[0], sl.inputs[0])
flash = nt.nodes.new("ShaderNodeValue")
flash.outputs[0].default_value = 1.0
fl = nt.nodes.new("ShaderNodeMath")
fl.operation = "MULTIPLY"
nt.links.new(sl.outputs[0], fl.inputs[0])
nt.links.new(flash.outputs[0], fl.inputs[1])
em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(tex.outputs["Result"], em.inputs["Color"])
fs = nt.nodes.new("ShaderNodeMath")
fs.operation = "MULTIPLY"
fs.inputs[1].default_value = 1.4
nt.links.new(fl.outputs[0], fs.inputs[0])
nt.links.new(fs.outputs[0], em.inputs["Strength"])
gl = nt.nodes.new("ShaderNodeBsdfGlossy")
gl.inputs["Roughness"].default_value = 0.05
gl.inputs["Color"].default_value = (0.08, 0.08, 0.1, 1)
ad = nt.nodes.new("ShaderNodeAddShader")
nt.links.new(em.outputs[0], ad.inputs[0])
nt.links.new(gl.outputs[0], ad.inputs[1])
nt.links.new(ad.outputs[0], out.inputs["Surface"])
scr.data.materials.append(m)
for f, v in ((1, 1.0), (JUMP[1] - 2, 1.0), (JUMP[1] + 1, 4.0), (JUMP[1] + 10, 1.2), (N, 1.2)):
    flash.outputs[0].default_value = v
    flash.outputs[0].keyframe_insert("default_value", frame=f)
st.neon_tube([(-SW / 2 - 0.012, -0.002, 0.018), (SW / 2 + 0.012, -0.002, 0.018)], st.CYAN, 10.0, radius=0.0012,
             light=False, name="MonitorLED")

# ---------------------------------------------------------------- Clawd: question, walk up, hop into the screen
U = 0.0042
cl = clawd.Clawd("Clawd", unit=U, location=(-0.30, -0.16, 0), rotation_z=math.radians(-25))
cl.say(4, "can a computer solve it?", 46)
cl.look(1, 1, 0)
cl.blink(52)
cl.walk(70, 130, (-0.30, -0.16, 0), (-0.02, -0.12, 0), step=3)
cl.turn(130, math.radians(-25))
cl.turn(140, math.radians(180))                 # faces the screen
cl.squash_to(144, 1.0)
cl.squash_to(JUMP[0], 0.75)
cl.place(JUMP[0], (-0.02, -0.12, 0))
cl.squash_to(JUMP[0] + 3, 1.2)
cl.place((JUMP[0] + JUMP[1]) // 2, (-0.01, -0.06, SZ + 0.03))
cl.place(JUMP[1], (0.0, 0.01, SZ - 0.02))
cl.cues.append((JUMP[0], "hop"))
cl.cues.append((JUMP[1], "zap"))
for f, s in ((1, 1.0), (JUMP[1] - 4, 1.0), (JUMP[1], 0.0)):     # shrinks into the screen
    cl.root.scale = (U * s, U * s, U * s)
    cl.root.keyframe_insert("scale", frame=f)

cam = sc.add_camera(lens=45.0, dof=16.0, clip=(0.005, 50))
tgt = sc.target_empty("T", (0, 0, SZ))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = scr
for f, loc, t in ((1, (-0.30, -0.70, 0.17), (-0.08, 0, 0.06)), (130, (-0.12, -0.55, 0.14), (-0.02, 0, SZ)),
                  (JUMP[1], (-0.02, -0.40, SZ + 0.03), (0, 0, SZ)), (N, (0.0, -0.165, SZ), (0, 0, SZ))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V12")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V12_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
