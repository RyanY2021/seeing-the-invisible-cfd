"""V04 — "why does it matter?": five holographic acrylic cards pop up around Clawd on the downbeats
(wing, car, offshore wind, globe, heart), each with neon line art and glowing dashes streaming along real
potential-flow streamlines (src/cards_v04.py). Eevee.

blender.exe -b --factory-startup --python blender/shot_v04.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 300
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 8 * 48 + 24
CARDS = sc.ROOT / "cache" / "v2" / "cards"

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.12)
st.strip_softbox((-0.25, -0.35, 0.22), size=(0.3, 0.05), energy=6.0, color=(1.0, 0.82, 0.72), target=(0, 0, 0.03),
                 name="ClawdKey", visible=False)

# a scene clock for the shaders (seconds)
clock = bpy.data.objects.new("Clock", None)
sc.link(clock)
clock["t"] = 0.0
fc = clock.driver_add('["t"]')
fc.driver.expression = "frame / 24.0"


def card_material(name, color):
    """icon (emission, alpha) + flowing dashes along the streamlines (R mask, G arclength)"""
    m, nt, out = sc.new_material(name)
    m.surface_render_method = "BLENDED"
    uv = nt.nodes.new("ShaderNodeTexCoord")
    icon = nt.nodes.new("ShaderNodeTexImage")
    icon.image = bpy.data.images.load(str(CARDS / f"{name}_icon.png"))
    flow = nt.nodes.new("ShaderNodeTexImage")
    flow.image = bpy.data.images.load(str(CARDS / f"{name}_flow.png"))
    flow.image.colorspace_settings.name = "Non-Color"
    flow.interpolation = "Linear"
    for t in (icon, flow):
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(flow.outputs["Color"], sep.inputs[0])
    # dash = bright head moving along each line: frac(param*K - t*speed) close to 1
    tv = nt.nodes.new("ShaderNodeAttribute")
    tv.attribute_type = "OBJECT"
    tv.attribute_name = "t"
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 6.0
    nt.links.new(sep.outputs["Green"], k.inputs[0])
    sp = nt.nodes.new("ShaderNodeMath")
    sp.operation = "MULTIPLY"
    sp.inputs[1].default_value = 1.6
    nt.links.new(tv.outputs["Fac"], sp.inputs[0])
    off = nt.nodes.new("ShaderNodeMath")
    off.operation = "MULTIPLY"
    off.inputs[1].default_value = 0.37
    nt.links.new(sep.outputs["Blue"], off.inputs[0])            # per-line phase
    a1 = nt.nodes.new("ShaderNodeMath")
    a1.operation = "SUBTRACT"
    nt.links.new(k.outputs[0], a1.inputs[0])
    nt.links.new(sp.outputs[0], a1.inputs[1])
    a2 = nt.nodes.new("ShaderNodeMath")
    a2.operation = "ADD"
    nt.links.new(a1.outputs[0], a2.inputs[0])
    nt.links.new(off.outputs[0], a2.inputs[1])
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    nt.links.new(a2.outputs[0], fr.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 6.0
    nt.links.new(fr.outputs[0], pw.inputs[0])
    gain = nt.nodes.new("ShaderNodeValue")
    gain.name = "FlowGain"
    gain.outputs[0].default_value = 1.0
    d1 = nt.nodes.new("ShaderNodeMath")
    d1.operation = "MULTIPLY_ADD"
    d1.inputs[1].default_value = 3.0
    d1.inputs[2].default_value = 0.18
    nt.links.new(pw.outputs[0], d1.inputs[0])
    d2 = nt.nodes.new("ShaderNodeMath")
    d2.operation = "MULTIPLY"
    nt.links.new(d1.outputs[0], d2.inputs[0])
    nt.links.new(sep.outputs["Red"], d2.inputs[1])
    d3 = nt.nodes.new("ShaderNodeMath")
    d3.operation = "MULTIPLY"
    nt.links.new(d2.outputs[0], d3.inputs[0])
    nt.links.new(gain.outputs[0], d3.inputs[1])
    flow_em = nt.nodes.new("ShaderNodeEmission")
    flow_em.inputs["Color"].default_value = (0.85, 0.95, 1.0, 1)
    fs = nt.nodes.new("ShaderNodeMath")
    fs.operation = "MULTIPLY"
    fs.inputs[1].default_value = 6.0
    nt.links.new(d3.outputs[0], fs.inputs[0])
    nt.links.new(fs.outputs[0], flow_em.inputs["Strength"])
    icon_em = nt.nodes.new("ShaderNodeEmission")
    icon_em.inputs["Strength"].default_value = 5.0
    nt.links.new(icon.outputs["Color"], icon_em.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(icon_em.outputs[0], add.inputs[0])
    nt.links.new(flow_em.outputs[0], add.inputs[1])
    # alpha = max(icon alpha, flow mask)
    am = nt.nodes.new("ShaderNodeMath")
    am.operation = "MAXIMUM"
    nt.links.new(icon.outputs["Alpha"], am.inputs[0])
    nt.links.new(d2.outputs[0], am.inputs[1])
    amc = nt.nodes.new("ShaderNodeMath")
    amc.operation = "MINIMUM"
    amc.inputs[1].default_value = 1.0
    nt.links.new(am.outputs[0], amc.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(amc.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(add.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m, gain


def slab_material(color):
    """frosted holographic acrylic: dark tinted, iridescent edges, partly see-through"""
    m, nt, out = sc.new_material("CardSlab")
    m.surface_render_method = "BLENDED"
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.02, 0.015, 0.05, 1)
    p.inputs["Roughness"].default_value = 0.22
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.03
    p.inputs["Thin Film Thickness"].default_value = 520.0
    p.inputs["Thin Film IOR"].default_value = 1.5
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    rim = nt.nodes.new("ShaderNodeEmission")
    rim.inputs["Color"].default_value = (*color, 1)
    rs = nt.nodes.new("ShaderNodeMath")
    rs.operation = "MULTIPLY"
    rs.inputs[1].default_value = 0.9
    nt.links.new(lw.outputs["Fresnel"], rs.inputs[0])
    nt.links.new(rs.outputs[0], rim.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(p.outputs[0], add.inputs[0])
    nt.links.new(rim.outputs[0], add.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.87
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(add.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


SPECS = [("wing", st.MAGENTA), ("car", st.CYAN), ("offshore", st.PEACH), ("globe", st.LIME), ("heart", (1.0, 0.2, 0.25))]
CW, CHh = 0.12, 0.075
R = 0.17
cards = []
for i, (name, col) in enumerate(SPECS):
    ang = math.radians(-66 + 33 * i)                  # a floating arc above and around Clawd
    pos = Vector((R * math.sin(ang), R * math.cos(ang) * 0.35 + 0.035, 0.105 + 0.03 * math.cos(1.7 * i) + 0.02 * math.cos(ang)))
    root = bpy.data.objects.new(f"Card_{name}", None)
    sc.link(root)
    root.location = pos
    root.rotation_euler = (math.radians(4), 0, -ang * 0.85)
    bpy.ops.mesh.primitive_cube_add(size=1)
    slab = bpy.context.active_object
    slab.scale = (CW, 0.004, CHh)
    bpy.ops.object.transform_apply(scale=True)
    bv = slab.modifiers.new("b", "BEVEL")
    bv.width = 0.006
    bv.segments = 4
    slab.data.materials.append(slab_material(col))
    slab.parent = root
    bpy.ops.mesh.primitive_plane_add(size=1)
    face = bpy.context.active_object
    face.scale = (CW * 0.94, CHh * 0.94, 1)
    face.rotation_euler = (math.pi / 2, 0, 0)
    face.location = (0, -0.0028, 0)
    mat, gain = card_material(name, col)
    face.data.materials.append(mat)
    face.parent = root
    face["t"] = 0.0
    d = face.driver_add('["t"]')
    d.driver.expression = "frame / 24.0"
    # pop on the downbeat of bar 15 + i  (shot frame 48*(1+i)+1): scale 0 -> 1.15 -> 1, spin in
    f0 = 48 * (1 + i) + 1
    for f, s, spin in ((1, 0.0, 90), (f0 - 1, 0.0, 90), (f0 + 4, 1.15, -8), (f0 + 8, 0.96, 3), (f0 + 12, 1.0, 0)):
        root.scale = (s, s, s)
        root.keyframe_insert("scale", frame=f)
        root.rotation_euler = (math.radians(4), 0, -ang * 0.85 + math.radians(spin))
        root.keyframe_insert("rotation_euler", frame=f)
    # gentle hover
    for k, f in enumerate(range(f0 + 12, N + 24, 24)):
        root.location = pos + Vector((0, 0, 0.004 * math.sin(k * 1.3 + i)))
        root.keyframe_insert("location", frame=f)
    # flow brightens on the last caption ("we must see the flow before it is built")
    for f, g in ((1, 1.0), (5.6 * 48, 1.0), (5.6 * 48 + 12, 2.6), (N, 2.6)):
        gain.outputs[0].default_value = g
        gain.outputs[0].keyframe_insert("default_value", frame=f)
    cards.append(root)

cl = clawd.Clawd("Clawd", unit=0.005, location=(0, -0.02, 0), rotation_z=0)
cl.say(6, "why care?", 40)
cl.look(1, 0, 1)
for i in range(5):
    f0 = 48 * (1 + i) + 1
    ang = -66 + 33 * i
    cl.turn(f0 - 6, math.radians(ang * 0.35))
    cl.look(f0 - 6, -1 if ang < 0 else (1 if ang > 0 else 0), 1)
    cl.squash_to(f0 - 2, 1.0)
    cl.squash_to(f0, 0.86)                 # little bounce on each beat
    cl.squash_to(f0 + 4, 1.08)
    cl.squash_to(f0 + 9, 1.0)
cl.turn(5 * 48 + 30, 0)
cl.look(5 * 48 + 30, 0, 0)
cl.blink(5 * 48 + 44)
cl.hop(6 * 48 + 2, 6 * 48 + 16, (0, -0.02, 0), (0, -0.02, 0), height=0.03)
cl.breathe(6 * 48 + 20, N, 24, 0.03)

cam = sc.add_camera(lens=40.0, dof=22.0, clip=(0.02, 50))
tgt = sc.target_empty("T", (0, 0.03, 0.075))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = cl.root
for f, ang, dist, z in ((1, -22, 0.50, 0.06), (200, -5, 0.48, 0.07), (N, 14, 0.42, 0.065)):
    a = math.radians(ang)
    cam.location = (dist * math.sin(a), -dist * math.cos(a), z)
    cam.keyframe_insert("location", frame=f)
sc.smooth_keys(cam)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V04")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    p = out / (f"V04_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if p.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
if MODE == "test":
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "v04.blend"))
