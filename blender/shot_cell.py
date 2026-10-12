"""S05 — one finite-volume cell: fluid streams through, flux arrows on its faces, its content rises and falls.

"What flows in - what flows out = what changes" (caption added in the compositor).
blender.exe -b --factory-startup --python blender/shot_cell.py -- <mode> <first> <last> [pct]
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
NFR = 252
FPS = 24

scn = sc.reset_scene()
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
scn.render.resolution_percentage = PCT
scn.render.fps = FPS
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_depth = "16"
scn.render.image_settings.color_mode = "RGB"
for attr, val in (("taa_render_samples", 64), ("use_raytracing", True)):
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
sc.world_color(scn, (0.004, 0.005, 0.008), 1.0)

# ---------------------------------------------------------------- lattice of cells (faint), central cell bright
def wire_box(name, center, size, mat, thick):
    bpy.ops.mesh.primitive_cube_add(size=size, location=center)
    o = bpy.context.active_object
    o.name = name
    wf = o.modifiers.new("wf", "WIREFRAME")
    wf.thickness = thick
    wf.use_relative_offset = False
    o.data.materials.append(mat)
    return o


faint = sc.emission_mat("LatticeFaint", (0.25, 0.55, 1.0), 0.5)
for ix in range(-2, 3):
    for iy in range(-1, 2):
        for iz in range(-1, 2):
            if (ix, iy, iz) == (0, 0, 0):
                continue
            d = math.sqrt(ix * ix + iy * iy + iz * iz)
            wire_box(f"cell_{ix}_{iy}_{iz}", (ix, iy, iz), 1.0, faint, 0.006 / (0.6 + 0.4 * d))
bright = sc.emission_mat("CellEdge", (0.75, 0.93, 1.0), 6.0)
wire_box("Cell", (0, 0, 0), 1.0, bright, 0.012)

# glassy faces + inner 'content' whose brightness follows the balance (in > out -> fills up)
bpy.ops.mesh.primitive_cube_add(size=0.995)
glass = bpy.context.active_object
gm, gnt, gout = sc.new_material("CellGlass")
gp = gnt.nodes.new("ShaderNodeBsdfPrincipled")
gp.inputs["Base Color"].default_value = (0.6, 0.8, 1.0, 1)
gp.inputs["Roughness"].default_value = 0.08
gp.inputs["Alpha"].default_value = 0.10
gp.inputs["Emission Color"].default_value = (0.25, 0.6, 1.0, 1)
fillv = gnt.nodes.new("ShaderNodeValue")
# content level over time: fills while inflow > outflow (0-4.5 s), drains when outflow wins (4.5-8.5 s)
keys = [(1, 0.15), (24, 0.15), (108, 1.0), (130, 1.0), (204, 0.25), (NFR, 0.25)]
for f, v in keys:
    fillv.outputs[0].default_value = v
    fillv.outputs[0].keyframe_insert("default_value", frame=f)
gnt.links.new(fillv.outputs[0], gp.inputs["Emission Strength"])
gnt.links.new(gp.outputs[0], gout.inputs["Surface"])
try:
    gm.surface_render_method = "BLENDED"
except Exception:
    pass
glass.data.materials.append(gm)


# ---------------------------------------------------------------- flux arrows on the faces
def arrow(name, color, strength):
    m = sc.emission_mat(name + "M", color, strength)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.035, depth=0.55, location=(0, 0, 0.275))
    shaft = bpy.context.active_object
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.09, radius2=0.0, depth=0.2, location=(0, 0, 0.65))
    head = bpy.context.active_object
    for o in (shaft, head):
        o.data.materials.append(m)
    root = bpy.data.objects.new(name, None)
    sc.link(root)
    shaft.parent = root
    head.parent = root
    return root


IN_C, OUT_C = (1.0, 0.62, 0.22), (0.35, 0.78, 1.0)
arrows = []
# (name, colour, base position, rotation, scale keys)
specs = [
    ("in_left", IN_C, (-1.25, 0, 0), (0, math.pi / 2, 0), [(1, 0.0), (20, 1.25), (108, 1.25), (140, 0.8), (NFR, 0.8)]),
    ("out_right", OUT_C, (0.5, 0, 0), (0, math.pi / 2, 0), [(1, 0.0), (26, 0.75), (108, 0.75), (140, 1.3), (NFR, 1.3)]),
    ("in_bottom", IN_C, (0, 0, -1.2), (0, 0, 0), [(1, 0.0), (32, 0.55), (108, 0.55), (140, 0.4), (NFR, 0.4)]),
    ("out_top", OUT_C, (0, 0, 0.5), (0, 0, 0), [(1, 0.0), (38, 0.45), (108, 0.45), (140, 0.65), (NFR, 0.65)]),
    ("in_front", IN_C, (0, -1.15, 0), (-math.pi / 2, 0, 0), [(1, 0.0), (44, 0.35), (NFR, 0.35)]),
    ("out_back", OUT_C, (0, 0.5, 0), (-math.pi / 2, 0, 0), [(1, 0.0), (50, 0.38), (NFR, 0.38)]),
]
for name, col, loc, rot, sk in specs:
    a = arrow(name, col, 2.0)
    a.location = loc
    a.rotation_euler = rot
    for f, v in sk:
        a.scale = (max(v, 0.001),) * 3
        a.keyframe_insert("scale", frame=f)
    sc.smooth_keys(a)

# ---------------------------------------------------------------- fluid parcels streaming through the lattice
NP = 800
rng = np.random.default_rng(5)
P0 = np.stack([rng.uniform(-2.5, 2.5, NP), rng.uniform(-1.5, 1.5, NP), rng.uniform(-1.5, 1.5, NP)], -1)
pm = bpy.data.meshes.new("parcels")
pm.vertices.add(NP)
po = bpy.data.objects.new("parcels", pm)
sc.link(po)
bpy.ops.mesh.primitive_ico_sphere_add(radius=0.010, subdivisions=2)
dot = bpy.context.active_object
dot.data.materials.append(sc.emission_mat("Parcel", (0.55, 0.78, 1.0), 1.8))
dot.parent = po
po.instance_type = "VERTS"


def parcels(scene, *_):
    t = (scene.frame_current - 1) / FPS
    x0, y0, z0 = P0[:, 0], P0[:, 1], P0[:, 2]
    u = 0.42 * (1 + 0.15 * z0)  # gentle shear
    x = (x0 + u * t + 2.5) % 5.0 - 2.5
    z = z0 + 0.08 * np.sin(1.3 * x + y0)
    y = y0 + 0.05 * np.cos(1.1 * x)
    pm.vertices.foreach_set("co", np.stack([x, y, z], -1).astype(np.float32).ravel())
    pm.update()


bpy.app.handlers.frame_change_pre.append(parcels)

# ---------------------------------------------------------------- camera: slow push into the cell
cam = sc.add_camera(lens=40.0, dof=2.8, clip=(0.05, 100))
tgt = sc.target_empty("CamTarget", (0, 0, 0))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
for f, cl in ((1, (-3.2, -5.4, 2.4)), (NFR, (-1.9, -3.4, 1.35))):
    cam.location = cl
    cam.keyframe_insert("location", frame=f)
sc.smooth_keys(cam)

if MODE == "test":
    outd = sc.ROOT / "cache" / "lookdev"
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) or 1)):
        scn.frame_set(f)
        parcels(scn)
        scn.render.filepath = str(outd / f"cell_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    sc.render_frames(scn, sc.ROOT / "renders" / "S05", FIRST, LAST)
