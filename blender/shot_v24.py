"""V24 — MEDICINE: blood through a carotid bifurcation, neon edition: a translucent vessel with a magenta rim glow,
speed-coloured glowing streamlines, tumbling red cells — and Clawd surfing one of them through the fork.
(Based on v1 shot_artery.py; flow from src/artery.py 312 artery_v2.) Eevee.

blender.exe -b --factory-startup --python blender/shot_v24.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as stu  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
PCT = 100
NFR = 6 * 48 + 24
FPS = 24
ART = sc.ROOT / "cache" / "artery_v2"
flow = np.load(ART / "flow.npz")
POS, ROT = flow["pos"], flow["rot"]
STREAMS, SPEED = flow["streams"], flow["speed"]

scn = sc.reset_scene()
stu.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, NFR
sc.world_color(scn, (0.006, 0.002, 0.014), 1.0)

# ---------------------------------------------------------------- vessel
bpy.ops.wm.ply_import(filepath=str(ART / "vessel.ply"))
vessel = bpy.context.selected_objects[0]
bpy.ops.object.shade_smooth()
m, nt, out = sc.new_material("VesselWall")
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Base Color"].default_value = (0.45, 0.04, 0.16, 1)
p.inputs["Roughness"].default_value = 0.25
p.inputs["Coat Weight"].default_value = 0.6
p.inputs["Subsurface Weight"].default_value = 0.4
p.inputs["Subsurface Radius"].default_value = (1.0, 0.25, 0.2)
p.inputs["Emission Color"].default_value = (1.0, 0.12, 0.55, 1)
lw = nt.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.35
fr = nt.nodes.new("ShaderNodeMapRange")
fr.inputs["To Min"].default_value = 0.05
fr.inputs["To Max"].default_value = 0.9
nt.links.new(lw.outputs["Facing"], fr.inputs["Value"])
em = nt.nodes.new("ShaderNodeMath")
em.operation = "MULTIPLY"
em.inputs[1].default_value = 1.6
nt.links.new(lw.outputs["Facing"], em.inputs[0])
nt.links.new(em.outputs[0], p.inputs["Emission Strength"])
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(fr.outputs["Result"], mix.inputs["Fac"])
nt.links.new(tr.outputs[0], mix.inputs[1])
nt.links.new(p.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs["Surface"])
try:
    m.surface_render_method = "BLENDED"
except Exception:
    pass
vessel.data.materials.append(m)

# ---------------------------------------------------------------- streamlines (speed-coloured, flowing dashes)
def stream_mat(name, col, speed):
    m, nt, out = sc.new_material(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*col, 1)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sz.inputs[0])
    tv = nt.nodes.new("ShaderNodeValue")
    for f, v in ((1, 0.0), (NFR, speed * NFR / FPS * 2.2)):
        tv.outputs[0].default_value = v
        tv.outputs[0].keyframe_insert("default_value", frame=f)
    for fc in (m.node_tree.animation_data.action.fcurves if hasattr(m.node_tree.animation_data.action, "fcurves") else []):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    oinfo = nt.nodes.new("ShaderNodeObjectInfo")
    rph = nt.nodes.new("ShaderNodeMath")
    rph.operation = "MULTIPLY_ADD"
    rph.inputs[1].default_value = 7.0
    nt.links.new(oinfo.outputs["Random"], rph.inputs[0])
    nt.links.new(sz.outputs["Z"], rph.inputs[2])
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    nt.links.new(rph.outputs[0], sub.inputs[0])
    nt.links.new(tv.outputs[0], sub.inputs[1])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.9
    nt.links.new(sub.outputs[0], mul.inputs[0])
    frc = nt.nodes.new("ShaderNodeMath")
    frc.operation = "FRACT"
    nt.links.new(mul.outputs[0], frc.inputs[0])
    dash = nt.nodes.new("ShaderNodeMapRange")
    dash.interpolation_type = "SMOOTHSTEP"
    dash.inputs["From Min"].default_value = 0.35
    dash.inputs["From Max"].default_value = 1.0
    dash.inputs["To Min"].default_value = 0.12
    dash.inputs["To Max"].default_value = 2.4
    nt.links.new(frc.outputs[0], dash.inputs["Value"])
    nt.links.new(dash.outputs["Result"], e.inputs["Strength"])
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    return m


PAL = [(0.35, 0.20, 1.0), (0.10, 0.85, 1.0), (1.0, 0.30, 0.80), (1.0, 0.85, 0.95)]
mats = [stream_mat(f"Stream{i}", c, 0.6 + 0.5 * i) for i, c in enumerate(PAL)]
ROOTE = bpy.data.objects.new("ArteryRoot", None)
sc.link(ROOTE)
for k, (pts, spd) in enumerate(zip(STREAMS[::2], SPEED[::2])):
    cu = bpy.data.curves.new(f"stream{k}", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.013
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    pts = pts[::3]
    sp.points.add(len(pts) - 1)
    for i, q in enumerate(pts):
        sp.points[i].co = (float(q[0]), float(q[1]), float(q[2]), 1.0)
    ob = bpy.data.objects.new(f"stream{k}", cu)
    sc.link(ob)
    ob.data.materials.append(mats[min(3, int(spd * 4))])
    ob.parent = ROOTE

# ---------------------------------------------------------------- red blood cells (GN instancing from per-frame points)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, segments=24, ring_count=12)
rbc = bpy.context.active_object
rbc.name = "RBC"
rbc.scale = (1.0, 1.0, 0.36)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.shade_smooth()
rm, _, rp = sc.principled("RBCmat", base=(0.62, 0.03, 0.03), rough=0.35, coat=0.3)
rp.inputs["Subsurface Weight"].default_value = 0.5
rp.inputs["Base Color"].default_value = (0.78, 0.05, 0.05, 1)
rp.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
rbc.data.materials.append(rm)
rbc.hide_render = True
rbc.location = (0, 0, -50)

pm = bpy.data.meshes.new("RBCpts")
pm.vertices.add(POS.shape[1])
pm.attributes.new("rot", "FLOAT_VECTOR", "POINT")
pts_obj = bpy.data.objects.new("RBCpts", pm)
sc.link(pts_obj)
gn = bpy.data.node_groups.new("RBCinst", "GeometryNodeTree")
try:
    gn.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    gn.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
except Exception:
    gn.inputs.new("NodeSocketGeometry", "Geometry")
    gn.outputs.new("NodeSocketGeometry", "Geometry")
gi = gn.nodes.new("NodeGroupInput")
go = gn.nodes.new("NodeGroupOutput")
m2p = gn.nodes.new("GeometryNodeMeshToPoints")
inst = gn.nodes.new("GeometryNodeInstanceOnPoints")
oi = gn.nodes.new("GeometryNodeObjectInfo")
oi.inputs["Object"].default_value = rbc
na = gn.nodes.new("GeometryNodeInputNamedAttribute")
na.data_type = "FLOAT_VECTOR"
na.inputs["Name"].default_value = "rot"
gn.links.new(gi.outputs[0], m2p.inputs["Mesh"])
gn.links.new(m2p.outputs["Points"], inst.inputs["Points"])
gn.links.new(oi.outputs["Geometry"], inst.inputs["Instance"])
gn.links.new(na.outputs["Attribute"], inst.inputs["Rotation"])
gn.links.new(inst.outputs["Instances"], go.inputs[0])
mod = pts_obj.modifiers.new("inst", "NODES")
mod.node_group = gn


def update_points(scene, *_):
    f = min(max(scene.frame_current - 1, 0), POS.shape[0] - 1)
    pm.vertices.foreach_set("co", POS[f].ravel())
    pm.attributes["rot"].data.foreach_set("vector", ROT[f].ravel())
    pm.update()


bpy.app.handlers.frame_change_pre.append(update_points)

# ---------------------------------------------------------------- lights, bokeh, camera
sc.add_light("Key", "AREA", (-6, -14, 6), 700, color=(1.0, 0.85, 0.85), size=8, target=(0, 0, 0))
sc.add_light("Rim", "AREA", (8, 12, 2), 1800, color=stu.CYAN, size=6, target=(0, 0, 0))
sc.add_light("Under", "AREA", (0, -6, -10), 500, color=stu.MAGENTA, size=6, target=(0, 0, -2))
bk = sc.emission_mat("Platelet", (1.0, 0.35, 0.3), 1.2)
rng = np.random.default_rng(9)


# ---------------------------------------------------------------- Clawd surfs a red cell through the fork
step = np.linalg.norm(np.diff(POS, axis=0), axis=2).max(axis=0)          # per-cell largest jump (respawns)
ok = np.nonzero(step < 0.25)[0]
d_mid = np.linalg.norm(POS[min(170, NFR - 1), ok], axis=1)
IDX = int(ok[np.argmin(d_mid)])
from mathutils import Matrix, Vector  # noqa: E402
R = Matrix.Rotation(math.radians(-52), 3, "Y")
cl = clawd.Clawd("Clawd", unit=0.014, location=(0, 0, 0), rotation_z=math.radians(-20))
world_pos = []
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
for f in range(1, NFR + 1):
    p_ = R @ Vector(POS[min(f - 1, POS.shape[0] - 1), IDX]) + Vector((0, 0, 0.035))
    world_pos.append(p_)
    cl.root.location = p_
    cl.root.keyframe_insert("location", frame=f)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
cl.arm(1, "L", 45)
cl.arm(1, "R", 45)
for k, f in enumerate(range(1, NFR, 8)):                                   # balancing on the cell
    cl.tilt(f, 9 * math.sin(k * 1.1))
cl.say(40, "surf's up!", 36)
cl.surprise(170)
cl.look(1, 1, 0)
ck = bpy.data.lights.new("ClawdKey", "POINT")
ck.energy = 6.0
ck.color = (1.0, 0.85, 0.75)
ck.shadow_soft_size = 0.1
cko = bpy.data.objects.new("ClawdKey", ck)
sc.link(cko)
cko.parent = cl.root
cko.location = (-40, -60, 40)                                              # Clawd units
linked = bpy.data.collections.new("ClawdOnly")
for o in cl.parts:
    if o.type == "MESH":
        linked.objects.link(o)
cko.light_linking.receiver_collection = linked

cam = sc.add_camera(lens=40.0, dof=5.6, clip=(0.02, 300))
tgt = sc.target_empty("CamTarget", (0, 0, 0.5))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = cl.root
vessel.parent = ROOTE
pts_obj.parent = ROOTE
ROOTE.rotation_euler = (0, math.radians(-52), 0)
for f in range(1, NFR + 1, 6):
    w = min(1.0, max(0.0, (f - 190) / (NFR - 190)))
    w = w * w * (3 - 2 * w)
    near = world_pos[f - 1]
    t_ = near * (1 - w) + Vector((0.9, 0.0, 0.6)) * w
    c_ = (near + Vector((-0.45, -1.25, 0.22))) * (1 - w) + Vector((0.5, -16.0, -0.2)) * w
    tgt.location = t_
    tgt.keyframe_insert("location", frame=f)
    cam.location = c_
    cam.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V24")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, NFR)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V24_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    update_points(scn)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
