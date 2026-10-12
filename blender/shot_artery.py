"""S14 — blood flow through a carotid bifurcation: translucent vessel, speed-coloured streamlines, pulsing RBCs.

blender.exe -b --factory-startup --python blender/shot_artery.py -- <mode> <first> <last> [pct]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import scene_common as sc  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
PCT = int(A[3]) if len(A) > 3 else 100
NFR = 190
FPS = 24
ART = sc.ROOT / "cache" / "artery"
flow = np.load(ART / "flow.npz")
POS, ROT = flow["pos"], flow["rot"]
STREAMS, SPEED = flow["streams"], flow["speed"]

scn = sc.reset_scene()
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
scn.render.resolution_percentage = PCT
scn.render.fps = FPS
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_depth = "16"
scn.render.image_settings.color_mode = "RGB"
for attr, val in (("taa_render_samples", 64), ("use_raytracing", True), ("use_shadows", True)):
    try:
        setattr(scn.eevee, attr, val)
    except Exception:
        pass
try:
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scn.frame_start, scn.frame_end = 1, NFR
sc.world_color(scn, (0.012, 0.002, 0.003), 1.0)

# ---------------------------------------------------------------- vessel
bpy.ops.wm.ply_import(filepath=str(ART / "vessel.ply"))
vessel = bpy.context.selected_objects[0]
bpy.ops.object.shade_smooth()
m, nt, out = sc.new_material("VesselWall")
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Base Color"].default_value = (0.55, 0.06, 0.07, 1)
p.inputs["Roughness"].default_value = 0.25
p.inputs["Coat Weight"].default_value = 0.6
p.inputs["Subsurface Weight"].default_value = 0.4
p.inputs["Subsurface Radius"].default_value = (1.0, 0.25, 0.2)
p.inputs["Emission Color"].default_value = (0.9, 0.2, 0.15, 1)
lw = nt.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.35
fr = nt.nodes.new("ShaderNodeMapRange")
fr.inputs["To Min"].default_value = 0.10
fr.inputs["To Max"].default_value = 0.95
nt.links.new(lw.outputs["Facing"], fr.inputs["Value"])
em = nt.nodes.new("ShaderNodeMath")
em.operation = "MULTIPLY"
em.inputs[1].default_value = 0.6
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


PAL = [(0.10, 0.35, 1.0), (0.15, 0.85, 1.0), (1.0, 0.85, 0.25), (1.0, 0.35, 0.10)]
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
sc.add_light("Key", "AREA", (-6, -14, 6), 900, color=(1.0, 0.9, 0.85), size=8, target=(0, 0, 0))
sc.add_light("Rim", "AREA", (8, 12, 2), 1400, color=(0.7, 0.8, 1.0), size=6, target=(0, 0, 0))
sc.add_light("Under", "AREA", (0, -6, -10), 300, color=(1.0, 0.3, 0.25), size=6, target=(0, 0, -2))
bk = sc.emission_mat("Platelet", (1.0, 0.35, 0.3), 1.2)
rng = np.random.default_rng(9)


cam = sc.add_camera(lens=60.0, dof=2.0, clip=(0.1, 300))
tgt = sc.target_empty("CamTarget", (0, 0, 0.5))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
vessel.parent = ROOTE
pts_obj.parent = ROOTE
ROOTE.rotation_euler = (0, math.radians(-52), 0)
for f, cl, tl in ((1, (-2.5, -17.5, -1.2), (0.6, 0.0, 0.3)), (NFR, (0.5, -16.0, -0.2), (0.9, 0.0, 0.6))):
    cam.location = cl
    cam.keyframe_insert("location", frame=f)
    tgt.location = tl
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

if MODE == "test":
    outd = sc.ROOT / "cache" / "lookdev"
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) or 1)):
        scn.frame_set(f)
        update_points(scn)
        scn.render.filepath = str(outd / f"artery_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "artery.blend"))
else:
    sc.render_frames(scn, sc.ROOT / "renders" / "S14", FIRST, LAST)
