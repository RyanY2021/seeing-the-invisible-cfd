"""S04 — a computational mesh grows around the clay car (octree levels on two slice planes + surface mesh).

blender.exe -b --factory-startup --python blender/shot_mesh.py -- <mode> <first> <last> [pct]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import car_common as cc  # noqa: E402
import scene_common as sc  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
PCT = int(A[3]) if len(A) > 3 else 100
NFR = 340
FPS = 24

scn = sc.reset_scene()
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
scn.render.resolution_percentage = PCT
scn.render.fps = FPS
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_depth = "16"
scn.render.image_settings.color_mode = "RGB"
ee = scn.eevee
for attr, val in (("taa_render_samples", 64), ("use_raytracing", True), ("use_shadows", True),
                  ("shadow_ray_count", 2), ("use_gtao", True), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
    try:
        setattr(ee, attr, val)
    except Exception:
        pass
try:
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
sc.world_color(scn, (0.006, 0.007, 0.009), 1.0)
scn.frame_start, scn.frame_end = 1, NFR

root, body, wheels = cc.build_car()

# floor: dark, glossy
bpy.ops.mesh.primitive_plane_add(size=80, location=(2.25, 0, 0))
fl = bpy.context.active_object
m, _, _ = sc.principled("StudioFloor", base=(0.012, 0.013, 0.015), rough=0.18)
fl.data.materials.append(m)
sc.add_light("Key", "AREA", (1.5, -2.5, 4.5), 420, color=(1.0, 0.97, 0.94), size=4.0, target=(2.25, 0, 0.5))
sc.add_light("Rim", "AREA", (5.5, 4.0, 2.5), 260, color=(0.8, 0.88, 1.0), size=3.0, target=(2.25, 0, 0.6))
sc.add_light("Front", "AREA", (-4.0, -1.0, 1.6), 90, color=(0.9, 0.95, 1.0), size=2.5, target=(1.0, 0, 0.5))


def keyed_emission(name, color, t_on, peak=6.0, hold=3.2):
    m, nt, out = sc.new_material(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    # distance falloff around the car: the mesh grows out of the body, fading into the dark
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    vd = nt.nodes.new("ShaderNodeVectorMath")
    vd.operation = "DISTANCE"
    vd.inputs[1].default_value = (2.6, 0.0, 0.5)
    nt.links.new(geo.outputs["Position"], vd.inputs[0])
    fall = nt.nodes.new("ShaderNodeMapRange")
    fall.interpolation_type = "SMOOTHSTEP"
    fall.inputs["From Min"].default_value = 7.5
    fall.inputs["From Max"].default_value = 2.5
    nt.links.new(vd.outputs["Value"], fall.inputs["Value"])
    val = nt.nodes.new("ShaderNodeValue")
    for f, v in ((1, 0.0), (int(t_on * FPS), 0.0), (int((t_on + 0.35) * FPS), peak * 1.8), (int((t_on + 1.0) * FPS), peak),
                 (NFR, peak * 0.9)):
        val.outputs[0].default_value = v
        val.outputs[0].keyframe_insert("default_value", frame=max(1, f))
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(val.outputs[0], mul.inputs[0])
    nt.links.new(fall.outputs["Result"], mul.inputs[1])
    nt.links.new(mul.outputs[0], e.inputs["Strength"])
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    return m


cells = np.load(sc.ROOT / "cache" / "car" / "mesh_cells.npz")
REVEAL = [1.0, 2.4, 3.6, 4.7, 5.7, 6.6]
COLS = [(0.10, 0.25, 0.55), (0.14, 0.38, 0.75), (0.18, 0.55, 0.90), (0.26, 0.72, 1.0), (0.45, 0.88, 1.0), (0.75, 0.97, 1.0)]
for plane in ("xz", "xy"):
    arr = cells[plane]
    for L in range(6):
        sel = arr[arr[:, 3] == L]
        if len(sel) == 0:
            continue
        verts, faces = [], []
        for (u, v, h, _) in sel:
            k = len(verts)
            if plane == "xz":
                verts += [(u, 0, v), (u + h, 0, v), (u + h, 0, v + h), (u, 0, v + h)]
            else:
                verts += [(u, v, 0.55), (u + h, v, 0.55), (u + h, v + h, 0.55), (u, v + h, 0.55)]
            faces.append((k, k + 1, k + 2, k + 3))
        me = bpy.data.meshes.new(f"cells_{plane}_{L}")
        me.from_pydata(verts, [], faces)
        o = bpy.data.objects.new(f"cells_{plane}_{L}", me)
        sc.link(o)
        wf = o.modifiers.new("wire", "WIREFRAME")
        wf.thickness = 0.0045 * (0.5 ** L) ** 0.4
        wf.use_even_offset = False
        wf.use_relative_offset = False
        t_on = REVEAL[L] + (0.25 if plane == "xy" else 0.0)
        o.data.materials.append(keyed_emission(f"glow_{plane}_{L}", COLS[L], t_on, peak=1.6 + 1.1 * L))

# surface mesh: decimated copy of the body as glowing triangles, revealed by a front-to-back scan
surf = body.copy()
surf.data = body.data.copy()
sc.link(surf)
surf.parent = root
dec = surf.modifiers.new("dec", "DECIMATE")
dec.ratio = 0.012
wf = surf.modifiers.new("wire", "WIREFRAME")
wf.thickness = 0.0032
wf.use_relative_offset = False
surf.data.materials.clear()
m, nt, out = sc.new_material("SurfMesh")
e = nt.nodes.new("ShaderNodeEmission")
e.inputs["Color"].default_value = (0.95, 0.75, 0.45, 1)
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Object"], sep.inputs[0])
scan = nt.nodes.new("ShaderNodeValue")
for f, v in ((1, -0.6), (int(7.4 * FPS), -0.6), (int(10.2 * FPS), 5.2), (NFR, 5.2)):
    scan.outputs[0].default_value = v
    scan.outputs[0].keyframe_insert("default_value", frame=f)
dx = nt.nodes.new("ShaderNodeMath")
dx.operation = "SUBTRACT"
nt.links.new(scan.outputs[0], dx.inputs[0])
nt.links.new(sep.outputs["X"], dx.inputs[1])
mr = nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = 0.0
mr.inputs["From Max"].default_value = 0.25
nt.links.new(dx.outputs[0], mr.inputs["Value"])
front = nt.nodes.new("ShaderNodeMapRange")  # bright leading edge of the scan
front.inputs["From Min"].default_value = 0.35
front.inputs["From Max"].default_value = 0.0
front.inputs["To Min"].default_value = 1.0
front.inputs["To Max"].default_value = 4.0
nt.links.new(dx.outputs[0], front.inputs["Value"])
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
nt.links.new(mr.outputs["Result"], mul.inputs[0])
nt.links.new(front.outputs["Result"], mul.inputs[1])
mul2 = nt.nodes.new("ShaderNodeMath")
mul2.operation = "MULTIPLY"
mul2.inputs[1].default_value = 1.1
nt.links.new(mul.outputs[0], mul2.inputs[0])
nt.links.new(mul2.outputs[0], e.inputs["Strength"])
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(mr.outputs["Result"], mix.inputs["Fac"])
nt.links.new(tr.outputs[0], mix.inputs[1])
nt.links.new(e.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs["Surface"])
surf.data.materials.append(m)

# camera orbit
pivot = sc.target_empty("Pivot", (2.25, 0, 0.55))
cam = sc.add_camera(lens=35.0, dof=4.0, clip=(0.05, 200))
cam.parent = pivot
r, hgt = 8.2, 2.3
a0 = math.radians(212)
cam.location = (r * math.cos(a0), r * math.sin(a0), hgt)
tg = sc.target_empty("CamTarget", (2.0, 0, 0.45))
sc.track_to(cam, tg)
cam.data.dof.focus_object = tg
for f, ang in ((1, 0.0), (NFR, math.radians(48))):
    pivot.rotation_euler = (0, 0, ang)
    pivot.keyframe_insert("rotation_euler", frame=f)
sc.smooth_keys(pivot)

if MODE == "test":
    outd = sc.ROOT / "cache" / "lookdev"
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3 or 1)):
        scn.frame_set(f)
        scn.render.filepath = str(outd / f"mesh_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "mesh.blend"))
else:
    sc.render_frames(scn, sc.ROOT / "renders" / "S04", FIRST, LAST)
