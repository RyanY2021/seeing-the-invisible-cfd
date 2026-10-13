"""V10 — the Navier-Stokes equations on a black lacquer slab: terms pop in, then light up one by one in the colour
of their rule (momentum cyan, pressure magenta, viscosity lime, outside forces violet, mass peach) and step
forward out of the slab; labels appear under them. Clawd walks along the top edge, looking at each. Eevee.

blender.exe -b --factory-startup --python blender/shot_v10.py -- <test|render> <first> <last> [samples]
"""
import json
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
FIRST = int(A[1]) if len(A) > 1 else 250
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 6 * 48 + 24
EQ = sc.ROOT / "cache" / "v2" / "eq"
META = json.loads((EQ / "layout.json").read_text())
BW, BH = META["board"]
PX = 0.135e-3                       # metres per board pixel
SW, SD, SH = BW * PX * 1.04, 0.025, BH * PX * 1.1
ZC = SH / 2

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.07, tubes=None, lights=False)
sc.add_light("RimMag", "SPOT", (-0.6, 0.4, 0.4), 12.0, color=st.MAGENTA, size=0.05, target=(-0.2, 0, 0.12),
             spot_size=math.radians(45), blend=0.7)
sc.add_light("RimCyan", "SPOT", (0.6, 0.4, 0.4), 12.0, color=st.CYAN, size=0.05, target=(0.2, 0, 0.12),
             spot_size=math.radians(45), blend=0.7)
st.neon_tube([(-0.9, 0.6, 0.0), (-0.9, 0.6, 0.5)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.5, 0.7, 0.36), (1.1, 0.7, 0.36)], st.CYAN, 30.0, name="NeonB")
ck = sc.add_light("ClawdKey", "AREA", (0.0, -0.30, SH + 0.25), 12.0, color=(1.0, 0.85, 0.75), size=0.6,
                  target=(0, 0, SH))
ck.data.shape = "RECTANGLE"
ck.data.size, ck.data.size_y = SW * 1.2, 0.15          # a long soft strip along the slab's top edge
ck.data.specular_factor = 0.0

# ---------------------------------------------------------------- the slab
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, ZC))
slab = bpy.context.active_object
slab.scale = (SW, SD, SH)
bpy.ops.object.transform_apply(scale=True)
bv = slab.modifiers.new("b", "BEVEL")
bv.width = 0.004
bv.segments = 4
m, nt, p = sc.principled("Slab", base=(0.004, 0.004, 0.007), rough=0.12, coat=1.0)
p.inputs["Thin Film Thickness"].default_value = 300.0
slab.data.materials.append(m)
st.neon_tube([(-SW / 2, -SD / 2 - 0.001, 0.004), (SW / 2, -SD / 2 - 0.001, 0.004)], st.VIOLET, 14.0, radius=0.0015,
             light=False, name="SlabFoot")

# ---------------------------------------------------------------- terms
APPEAR = {"momentum": 6, "eq1": 12, "pressure": 16, "plus1": 20, "viscosity": 24, "plus2": 28, "forces": 32,
          "mass": 42}
HIGHLIGHT = {"momentum": 72, "pressure": 112, "viscosity": 150, "forces": 188, "mass": 226}
ALL_ON = 262
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"


def term_plane(key, tex_name, color, appear, highlight, is_label=False):
    cx, cy, w, h = META["layout"][key]
    bpy.ops.mesh.primitive_plane_add(size=1)
    ob = bpy.context.active_object
    ob.name = f"T_{key}"
    ob.scale = (w * PX, h * PX, 1)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    home = ((cx - BW / 2) * PX, -SD / 2 - 0.0015, ZC + (BH / 2 - cy) * PX)
    ob.location = home
    mt, nt, out = sc.new_material(f"M_{key}")
    mt.surface_render_method = "BLENDED"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(EQ / f"{tex_name}.png"))
    col = nt.nodes.new("ShaderNodeRGB")
    strength = nt.nodes.new("ShaderNodeValue")
    vis = nt.nodes.new("ShaderNodeValue")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(col.outputs[0], em.inputs["Color"])
    nt.links.new(strength.outputs[0], em.inputs["Strength"])
    am = nt.nodes.new("ShaderNodeMath")
    am.operation = "MULTIPLY"
    nt.links.new(tex.outputs["Alpha"], am.inputs[0])
    nt.links.new(vis.outputs[0], am.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(am.outputs[0], mx.inputs["Fac"])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(mt)
    white = (1.0, 0.97, 0.94, 1)
    c = (*[v / 255 for v in color], 1)

    def key_(f, rgb, s, v, dy=0.0, sc_=1.0):
        col.outputs[0].default_value = rgb
        col.outputs[0].keyframe_insert("default_value", frame=f)
        strength.outputs[0].default_value = s
        strength.outputs[0].keyframe_insert("default_value", frame=f)
        vis.outputs[0].default_value = v
        vis.outputs[0].keyframe_insert("default_value", frame=f)
        ob.location = (home[0], home[1] - dy, home[2])
        ob.keyframe_insert("location", frame=f)
        ob.scale = (w * PX * sc_, h * PX * sc_, 1)
        ob.keyframe_insert("scale", frame=f)

    if is_label:
        key_(1, c, 1.8, 0.0)
        key_(highlight, c, 1.8, 0.0)
        key_(highlight + 6, c, 1.8, 1.0)
        return ob
    key_(1, white, 1.6, 0.0, 0, 0.6)
    key_(appear, white, 1.6, 0.0, 0, 0.6)
    key_(appear + 4, white, 2.2, 1.0, 0.004, 1.12)
    key_(appear + 8, white, 1.6, 1.0, 0, 1.0)
    if highlight:
        key_(highlight - 1, white, 1.6, 1.0, 0, 1.0)
        key_(highlight + 3, c, 4.5, 1.0, 0.018, 1.08)        # lights up and steps forward
        key_(highlight + 14, c, 2.6, 1.0, 0.012, 1.0)
        key_(ALL_ON - 1, c, 2.2, 1.0, 0.008, 1.0)
        key_(ALL_ON + 4, c, 3.0, 1.0, 0.012, 1.0)
    else:
        key_(ALL_ON, white, 1.6, 1.0, 0, 1.0)
        key_(ALL_ON + 4, white, 3.0, 1.0, 0.006, 1.0)
    return ob


for name, color in META["colors"].items():
    term_plane(name, name, color, APPEAR[name], HIGHLIGHT.get(name))
    if name in HIGHLIGHT:
        term_plane(f"{name}_label", f"{name}_label", color, 0, HIGHLIGHT[name] + 4, is_label=True)

# ---------------------------------------------------------------- Clawd on the top edge
U = 0.004
x_of = {k: (META["layout"][k][0] - BW / 2) * PX for k in HIGHLIGHT}
cl = clawd.Clawd("Clawd", unit=U, location=(-SW / 2 + 0.05, -0.002, SH), rotation_z=0)
cl.look(1, 1, -1)
prev = -SW / 2 + 0.05
for k, f in HIGHLIGHT.items():
    tx = max(min(x_of[k] * 0.85, SW / 2 - 0.05), -SW / 2 + 0.05)
    if abs(tx - prev) > 0.01:
        cl.walk(f - 26, f - 4, (prev, -0.002, SH), (tx, -0.002, SH), step=3)
        prev = tx
    cl.look(f - 2, 0, -1)
    cl.surprise(f + 2)
    cl.cues.append((f, "chime"))
cl.look(ALL_ON, 0, 0)
cl.hop(ALL_ON + 2, ALL_ON + 14, (prev, -0.002, SH), (prev, -0.002, SH), height=0.02)

cam = sc.add_camera(lens=40.0, dof=16.0, clip=(0.01, 50))
tgt = sc.target_empty("T", (0, 0, ZC))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = slab
for f, loc, t in ((1, (-0.10, -1.05, 0.20), (0, 0, ZC)), (70, (-0.05, -0.82, 0.17), (0, 0, ZC + 0.01)),
                  (N, (0.08, -0.74, 0.16), (0.01, 0, ZC + 0.01))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V10")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V10_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
