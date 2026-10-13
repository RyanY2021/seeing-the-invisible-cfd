"""V19 — turbulence models as camera settings: in the neon studio a big glass display shows turbulent flow; Clawd
with a little pixel camera snaps it three times — each snap ejects an acrylic polaroid that flies into a row:
RANS (the average), LES (big swirls), DNS (every swirl), each with a neon label. Eevee.

blender.exe -b --factory-startup --python blender/shot_v19.py -- <test|render> <first> <last> [samples]
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
FIRST = int(A[1]) if len(A) > 1 else 400
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 10 * 48 + 24
TEX = sc.ROOT / "cache" / "v2" / "v19"
FONT = str(sc.ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
SNAPS = [168, 264, 360]                                  # bars 99.5, 101.5, 103.5
SPEC = [("rans", "RANS", "the average", st.MAGENTA), ("les", "LES", "big swirls; small ones estimated", st.LIME),
        ("dns", "DNS", "every swirl (tiny problems only)", st.CYAN)]

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.01, floor_rough=0.08, tubes=None, lights=False)
scn.eevee.use_raytracing = False    # screen-space reflections smeared the neon labels into streaks
sc.add_light("RimMag", "SPOT", (-0.7, 0.3, 0.5), 18.0, color=st.MAGENTA, size=0.05, target=(-0.2, 0, 0.1),
             spot_size=math.radians(50), blend=0.7)
sc.add_light("RimCyan", "SPOT", (0.7, 0.3, 0.5), 18.0, color=st.CYAN, size=0.05, target=(0.2, 0, 0.1),
             spot_size=math.radians(50), blend=0.7)
key = sc.add_light("Key", "AREA", (-0.2, -0.6, 0.5), 8.0, color=(1, 0.88, 0.8), size=0.5, target=(0, -0.1, 0.05))
ck = sc.add_light("ClawdKey", "AREA", (-0.45, -0.6, 0.25), 6.0, color=(1, 0.84, 0.74), size=0.3, target=(-0.28, -0.2, 0.03))
ck.data.specular_factor = 0.0
key.data.specular_factor = 0.0


def image_mat(name, path, strength=1.0):
    m, nt, out = sc.new_material(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path))
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0, 0, 0, 1)
    p.inputs["Roughness"].default_value = 0.08
    p.inputs["Coat Weight"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = strength
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- the big display behind (live = DNS picture)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.25, 0.20), rotation=(math.pi / 2, 0, 0))
big = bpy.context.active_object
big.scale = (0.48, 0.36, 1)
big.data.materials.append(image_mat("Big", TEX / "dns.exr", 0.9))
st.neon_tube([(-0.245, 0.249, 0.018), (0.245, 0.249, 0.018), (0.245, 0.249, 0.382), (-0.245, 0.249, 0.382),
              (-0.245, 0.249, 0.018)], st.VIOLET, 10.0, radius=0.0015, light=False, name="BigFrame")

# ---------------------------------------------------------------- polaroids
SLOTS = [Vector((-0.17, -0.05, 0.13)), Vector((0.0, -0.05, 0.13)), Vector((0.17, -0.05, 0.13))]
pol_mat = sc.principled("PolaroidFrame", base=(0.025, 0.022, 0.035), rough=0.2, coat=1.0)[0]
polaroids = []
for i, (key_, lab, sub, col) in enumerate(SPEC):
    root = bpy.data.objects.new(f"Pol_{key_}", None)
    sc.link(root)
    bpy.ops.mesh.primitive_cube_add(size=1)
    fr = bpy.context.active_object
    fr.scale = (0.14, 0.004, 0.125)
    fr.location = (0, 0, -0.008)
    fr.data.materials.append(pol_mat)
    fr.parent = root
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.0021, 0.0), rotation=(math.pi / 2, 0, 0))
    im = bpy.context.active_object
    im.scale = (0.124, 0.093, 1)
    im.data.materials.append(image_mat(f"Img_{key_}", TEX / f"{key_}.exr", 1.0))
    im.parent = root
    labs = st.neon_text([lab], FONT, 0.016, (0, -0.003, -0.058), col, strength=12.0, board=False,
                        name=f"L_{key_}", light_energy=0.0, per_word=False)
    subs = st.neon_text([sub], FONT, 0.0078, (0, -0.003, -0.082), (0.95, 0.92, 1.0), strength=4.0, board=False,
                        name=f"S_{key_}", light_energy=0.0, per_word=False)
    for o in labs + subs:
        o.parent = root
    t = SNAPS[i]
    cam_pos = Vector((-0.25, -0.20, 0.06))
    for f, loc, s, rz in ((1, cam_pos, 0.0, 0.0), (t, cam_pos, 0.0, 0.0), (t + 4, cam_pos + Vector((0.02, 0, 0.03)), 0.4, 25),
                          (t + 16, (cam_pos + SLOTS[i]) / 2 + Vector((0, -0.05, 0.08)), 1.1, -10),
                          (t + 26, SLOTS[i], 1.0, 0), (N, SLOTS[i] + Vector((0, 0, 0.004)), 1.0, 0)):
        root.location = loc
        root.keyframe_insert("location", frame=f)
        root.scale = (s, s, s)
        root.keyframe_insert("scale", frame=f)
        root.rotation_euler = (0, 0, math.radians(rz))
        root.keyframe_insert("rotation_euler", frame=f)
    polaroids.append(root)

# ---------------------------------------------------------------- Clawd with a pixel camera
U = 0.0042
cl = clawd.Clawd("Clawd", unit=U, location=(-0.36, -0.20, 0), rotation_z=math.radians(150))
bpy.ops.mesh.primitive_cube_add(size=1)
camb = bpy.context.active_object
camb.scale = (5, 3, 3.5)
camb.data.materials.append(sc.principled("CamBody", base=(0.02, 0.02, 0.025), rough=0.25, coat=1.0)[0])
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.2, depth=1.6, location=(0, -2.2, 0), rotation=(math.pi / 2, 0, 0))
lens = bpy.context.active_object
lens.data.materials.append(sc.principled("Lens", base=(0.05, 0.08, 0.15), rough=0.05, metal=0.6, coat=1.0)[0])
lens.parent = camb
camb.parent = cl.body
camb.location = (8.5, -1.0, 4.0)
flash = bpy.data.lights.new("Flash", "POINT")
flash.color = (1, 1, 1)
flash.shadow_soft_size = 0.02
fo = bpy.data.objects.new("Flash", flash)
fo.parent = camb
fo.location = (0, -4, 1)
sc.link(fo)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
for f, e in ((1, 0.0),) + tuple(x for t in SNAPS for x in ((t, 0.0), (t + 1, 40.0), (t + 3, 0.0))):
    flash.energy = e
    flash.keyframe_insert("energy", frame=f)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
cl.walk(10, 70, (-0.36, -0.20, 0), (-0.27, -0.20, 0), step=3)
cl.look(72, 1, 1)
for t in SNAPS:
    cl.squash_to(t - 3, 1.0)
    cl.squash_to(t, 0.9)
    cl.squash_to(t + 5, 1.0)
    cl.cues.append((t, "shutter"))
    cl.look(t + 8, 1, 0)
    cl.look(t + 40, 1, 1)
cl.turn(SNAPS[-1] + 40, math.radians(150))
cl.turn(SNAPS[-1] + 54, math.radians(20))
cl.look(SNAPS[-1] + 54, 0, 0)
cl.hop(SNAPS[-1] + 70, SNAPS[-1] + 82, (-0.27, -0.20, 0), (-0.27, -0.20, 0), height=0.02)

cam = sc.add_camera(lens=40.0, dof=14.0, clip=(0.01, 50))
tgt = sc.target_empty("T", (-0.1, 0, 0.12))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
for f, loc, t in ((1, (-0.42, -0.85, 0.15), (-0.20, 0.0, 0.07)), (150, (-0.30, -0.82, 0.17), (-0.13, 0.0, 0.10)),
                  (SNAPS[-1], (-0.05, -0.72, 0.16), (0.0, -0.05, 0.12)), (N, (0.0, -0.62, 0.15), (0.0, -0.05, 0.11))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V19")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V19_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
