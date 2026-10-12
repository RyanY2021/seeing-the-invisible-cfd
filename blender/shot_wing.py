"""S10 — a light aircraft punches through a smoke curtain; its wing-tip vortices wind the smoke into spirals.

blender.exe -b --factory-startup --python blender/shot_wing.py -- <mode> <first> <last> [pct] [samples]
  mode: S10 (renders/S10) or test (cache/lookdev)
Smoke cross-section sequence: cache/wing_tex/####.png from src/sim_wing.py (Krasny vortex-sheet roll-up).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import scene_common as sc  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
PCT = int(A[3]) if len(A) > 3 else 100
SAMPLES = int(A[4]) if len(A) > 4 else 64
DENS = float(A[5]) if len(A) > 5 else 3.6
NFR = 196
ALT = 9.0
SEMI = 6.0
YR = (-2.6, 2.6)
ZR = (-1.6, 1.0)
U = 16.7  # m/s (slow-motion feel)
X0 = -20.0

scn = sc.reset_scene()
sc.setup_cycles(scn, samples=SAMPLES, bounces=(6, 2, 2), adaptive=0.02)
scn.render.resolution_percentage = PCT
scn.render.use_motion_blur = True
scn.render.motion_blur_shutter = 0.5
if hasattr(scn.cycles, "volume_step_rate"):
    scn.cycles.volume_step_rate = 1.0

# ---------------------------------------------------------------- sky (HDRI rotated so the sun is front-left)
SUN_AZ, SUN_EL = 62.0, 47.9
HDRI_SUN_AZ = -36.0
w = bpy.data.worlds.new("World")
scn.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes.get("Background")
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(str(sc.ROOT / "assets" / "hdri" / "kloofendal_48d_partly_cloudy.hdr"))
tc = nt.nodes.new("ShaderNodeTexCoord")
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Rotation"].default_value = (0, 0, math.radians(HDRI_SUN_AZ - SUN_AZ))
nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0
sun_d = bpy.data.lights.new("Sun", "SUN")
sun_d.energy = 3.2
sun_d.angle = math.radians(1.2)
sun_d.color = (1.0, 0.96, 0.9)
sun = bpy.data.objects.new("Sun", sun_d)
sc.link(sun)
az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
from mathutils import Vector  # noqa: E402

sdir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
sun.rotation_euler = (-sdir).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- aircraft
def import_ply(path, name):
    bpy.ops.wm.ply_import(filepath=str(path))
    o = bpy.context.selected_objects[0]
    o.name = name
    bpy.ops.object.shade_smooth()
    return o


body = import_ply(sc.ROOT / "cache" / "plane" / "plane_body.ply", "PlaneBody")
canopy = import_ply(sc.ROOT / "cache" / "plane" / "plane_canopy.ply", "Canopy")
m, nt2, out = sc.new_material("Paint")
p = nt2.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Roughness"].default_value = 0.28
p.inputs["Coat Weight"].default_value = 0.4
tco = nt2.nodes.new("ShaderNodeTexCoord")
sep = nt2.nodes.new("ShaderNodeSeparateXYZ")
nt2.links.new(tco.outputs["Object"], sep.inputs[0])
# red cheat-line on the fuselage + red wing tips
stripe = nt2.nodes.new("ShaderNodeMapRange")
stripe.inputs["From Min"].default_value = 0.30
stripe.inputs["From Max"].default_value = 0.33
nt2.links.new(sep.outputs["Z"], stripe.inputs["Value"])
stripe2 = nt2.nodes.new("ShaderNodeMapRange")
stripe2.inputs["From Min"].default_value = 0.45
stripe2.inputs["From Max"].default_value = 0.42
nt2.links.new(sep.outputs["Z"], stripe2.inputs["Value"])
smin_ = nt2.nodes.new("ShaderNodeMath")
smin_.operation = "MINIMUM"
nt2.links.new(stripe.outputs["Result"], smin_.inputs[0])
nt2.links.new(stripe2.outputs["Result"], smin_.inputs[1])
ay = nt2.nodes.new("ShaderNodeMath")
ay.operation = "ABSOLUTE"
nt2.links.new(sep.outputs["Y"], ay.inputs[0])
fus = nt2.nodes.new("ShaderNodeMapRange")
fus.inputs["From Min"].default_value = 0.75
fus.inputs["From Max"].default_value = 0.65
nt2.links.new(ay.outputs[0], fus.inputs["Value"])
tipr = nt2.nodes.new("ShaderNodeMapRange")
tipr.inputs["From Min"].default_value = 5.55
tipr.inputs["From Max"].default_value = 5.6
nt2.links.new(ay.outputs[0], tipr.inputs["Value"])
s_on = nt2.nodes.new("ShaderNodeMath")
s_on.operation = "MULTIPLY"
nt2.links.new(smin_.outputs[0], s_on.inputs[0])
nt2.links.new(fus.outputs["Result"], s_on.inputs[1])
red_on = nt2.nodes.new("ShaderNodeMath")
red_on.operation = "MAXIMUM"
nt2.links.new(s_on.outputs[0], red_on.inputs[0])
nt2.links.new(tipr.outputs["Result"], red_on.inputs[1])
colm = nt2.nodes.new("ShaderNodeMix")
colm.data_type = "RGBA"
colm.inputs["A"].default_value = (0.82, 0.82, 0.80, 1)
colm.inputs["B"].default_value = (0.55, 0.04, 0.03, 1)
nt2.links.new(red_on.outputs[0], colm.inputs["Factor"])
nt2.links.new(colm.outputs["Result"], p.inputs["Base Color"])
nt2.links.new(p.outputs[0], out.inputs["Surface"])
body.data.materials.append(m)
gm, _, _ = sc.principled("CanopyGlass", base=(0.02, 0.025, 0.03), rough=0.05, coat=1.0, spec=0.9)
canopy.data.materials.append(gm)
# spinning propeller disc (motion-blurred blades read as a faint disc)
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.95, depth=0.01, location=(3.42, 0, 0.18),
                                    rotation=(0, math.pi / 2, 0))
prop = bpy.context.active_object
pm, pnt, pp = sc.principled("PropDisc", base=(0.03, 0.03, 0.03), rough=0.5, alpha=0.18)
prop.data.materials.append(pm)
plane = bpy.data.objects.new("Plane", None)
sc.link(plane)
for o in (body, canopy, prop):
    o.parent = plane
for f in (1, NFR):
    t = (f - 1) / 24.0
    plane.location = (X0 + U * t, 0.0, ALT + 0.15 * t)
    plane.keyframe_insert("location", frame=f)
sc.smooth_keys(plane, interp="LINEAR")
plane.rotation_euler = (math.radians(1.5), math.radians(-1.5), 0)
# nav lights (port red / starboard green), small emissive spheres
for yy, col in ((5.95, (1, 0.05, 0.02)), (-5.95, (0.05, 1, 0.2))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(0.1, yy, 0.42))
    o = bpy.context.active_object
    o.data.materials.append(sc.emission_mat(f"Nav{yy}", col, 40.0))
    o.parent = plane

# ---------------------------------------------------------------- smoke curtain
ymin, ymax = YR[0] * SEMI, YR[1] * SEMI
zmin, zmax = ALT + ZR[0] * SEMI, ALT + ZR[1] * SEMI
bpy.ops.mesh.primitive_cube_add(location=(1.8, 0.5 * (ymin + ymax), 0.5 * (zmin + zmax)))
cur = bpy.context.active_object
cur.name = "Curtain"
cur.scale = (2.2, 0.5 * (ymax - ymin), 0.5 * (zmax - zmin))
m, nt3, out = sc.new_material("CurtainSmoke")
tcc = nt3.nodes.new("ShaderNodeTexCoord")
sp3 = nt3.nodes.new("ShaderNodeSeparateXYZ")
nt3.links.new(tcc.outputs["Object"], sp3.inputs[0])
uu = nt3.nodes.new("ShaderNodeMapRange")
uu.inputs["From Min"].default_value = -1
uu.inputs["From Max"].default_value = 1
uu.clamp = False
nt3.links.new(sp3.outputs["Y"], uu.inputs["Value"])
vv = nt3.nodes.new("ShaderNodeMapRange")
vv.inputs["From Min"].default_value = -1
vv.inputs["From Max"].default_value = 1
vv.clamp = False
nt3.links.new(sp3.outputs["Z"], vv.inputs["Value"])
uv = nt3.nodes.new("ShaderNodeCombineXYZ")
nt3.links.new(uu.outputs["Result"], uv.inputs["X"])
nt3.links.new(vv.outputs["Result"], uv.inputs["Y"])
img = nt3.nodes.new("ShaderNodeTexImage")
im = bpy.data.images.load(str(sc.ROOT / "cache" / "wing_tex" / "0000.png"))
im.source = "SEQUENCE"
im.colorspace_settings.name = "Non-Color"
img.image = im
img.interpolation = "Cubic"
img.extension = "CLIP"
img.image_user.frame_duration = NFR
img.image_user.frame_start = 1
img.image_user.frame_offset = -1
img.image_user.use_auto_refresh = True
nt3.links.new(uv.outputs[0], img.inputs["Vector"])
# slab profile across the thickness + 3D billowy noise
ax = nt3.nodes.new("ShaderNodeMath")
ax.operation = "ABSOLUTE"
nt3.links.new(sp3.outputs["X"], ax.inputs[0])
prof = nt3.nodes.new("ShaderNodeMapRange")
prof.interpolation_type = "SMOOTHSTEP"
prof.inputs["From Min"].default_value = 1.0
prof.inputs["From Max"].default_value = 0.35
nt3.links.new(ax.outputs[0], prof.inputs["Value"])
geo = nt3.nodes.new("ShaderNodeNewGeometry")
nz = nt3.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 0.35
nz.inputs["Detail"].default_value = 6.0
nz.inputs["Roughness"].default_value = 0.55
nt3.links.new(geo.outputs["Position"], nz.inputs["Vector"])
nzr = nt3.nodes.new("ShaderNodeMapRange")
nzr.inputs["From Min"].default_value = 0.3
nzr.inputs["From Max"].default_value = 0.7
nzr.inputs["To Min"].default_value = 0.45
nzr.inputs["To Max"].default_value = 1.25
nt3.links.new(nz.outputs["Fac"], nzr.inputs["Value"])
# organic envelope: smoke rises from generators on the ground, thinning and fraying with height
gz = nt3.nodes.new("ShaderNodeSeparateXYZ")
nt3.links.new(geo.outputs["Position"], gz.inputs[0])
en = nt3.nodes.new("ShaderNodeTexNoise")
en.inputs["Scale"].default_value = 0.09
en.inputs["Detail"].default_value = 4.0
nt3.links.new(geo.outputs["Position"], en.inputs["Vector"])
enm = nt3.nodes.new("ShaderNodeMath")
enm.operation = "MULTIPLY_ADD"
enm.inputs[1].default_value = 9.0
enm.inputs[2].default_value = -4.5
nt3.links.new(en.outputs["Fac"], enm.inputs[0])
zp = nt3.nodes.new("ShaderNodeMath")
zp.operation = "ADD"
nt3.links.new(gz.outputs["Z"], zp.inputs[0])
nt3.links.new(enm.outputs[0], zp.inputs[1])
top = nt3.nodes.new("ShaderNodeMapRange")
top.interpolation_type = "SMOOTHSTEP"
top.inputs["From Min"].default_value = 15.5
top.inputs["From Max"].default_value = 6.0
top.inputs["To Min"].default_value = 0.0
top.inputs["To Max"].default_value = 1.0
nt3.links.new(zp.outputs[0], top.inputs["Value"])
ayy = nt3.nodes.new("ShaderNodeMath")
ayy.operation = "ABSOLUTE"
nt3.links.new(gz.outputs["Y"], ayy.inputs[0])
yp = nt3.nodes.new("ShaderNodeMath")
yp.operation = "ADD"
nt3.links.new(ayy.outputs[0], yp.inputs[0])
nt3.links.new(enm.outputs[0], yp.inputs[1])
side = nt3.nodes.new("ShaderNodeMapRange")
side.interpolation_type = "SMOOTHSTEP"
side.inputs["From Min"].default_value = 15.0
side.inputs["From Max"].default_value = 9.0
nt3.links.new(yp.outputs[0], side.inputs["Value"])
bot = nt3.nodes.new("ShaderNodeMapRange")
bot.interpolation_type = "SMOOTHSTEP"
bot.inputs["From Min"].default_value = -3.5
bot.inputs["From Max"].default_value = 3.5
nt3.links.new(zp.outputs[0], bot.inputs["Value"])
gf0 = nt3.nodes.new("ShaderNodeMath")
gf0.operation = "MULTIPLY"
nt3.links.new(top.outputs["Result"], gf0.inputs[0])
nt3.links.new(side.outputs["Result"], gf0.inputs[1])
gf = nt3.nodes.new("ShaderNodeMath")
gf.operation = "MULTIPLY"
nt3.links.new(gf0.outputs[0], gf.inputs[0])
nt3.links.new(bot.outputs["Result"], gf.inputs[1])
gf.outputs[0].name = "Result"
m1 = nt3.nodes.new("ShaderNodeMath")
m1.operation = "MULTIPLY"
nt3.links.new(img.outputs["Color"], m1.inputs[0])
nt3.links.new(prof.outputs["Result"], m1.inputs[1])
m2 = nt3.nodes.new("ShaderNodeMath")
m2.operation = "MULTIPLY"
nt3.links.new(m1.outputs[0], m2.inputs[0])
nt3.links.new(nzr.outputs["Result"], m2.inputs[1])
m3 = nt3.nodes.new("ShaderNodeMath")
m3.operation = "MULTIPLY"
nt3.links.new(m2.outputs[0], m3.inputs[0])
nt3.links.new(gf.outputs[0], m3.inputs[1])
m4 = nt3.nodes.new("ShaderNodeMath")
m4.operation = "MULTIPLY"
m4.inputs[1].default_value = DENS
nt3.links.new(m3.outputs[0], m4.inputs[0])
pv = nt3.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Color"].default_value = (0.95, 0.30, 0.16, 1)
pv.inputs["Anisotropy"].default_value = 0.3
nt3.links.new(m4.outputs[0], pv.inputs["Density"])
nt3.links.new(pv.outputs[0], out.inputs["Volume"])
cur.data.materials.append(m)

# ---------------------------------------------------------------- camera
cam = sc.add_camera(lens=30.0, clip=(0.1, 2000))
tgt = sc.target_empty("CamTarget", (0, 0, 7.0))
sc.track_to(cam, tgt)
for f, cl, tl in ((1, (-33.0, -3.5, 7.0), (0, 0.5, 8.4)), (NFR, (-29.5, -2.5, 6.8), (0, 0.3, 7.4))):
    cam.location = cl
    cam.keyframe_insert("location", frame=f)
    tgt.location = tl
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)
scn.frame_start, scn.frame_end = 1, NFR

if MODE == "test":
    outd = sc.ROOT / "cache" / "lookdev"
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3 or 1)):
        scn.frame_set(f)
        scn.render.filepath = str(outd / f"wing_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "wing.blend"))
else:
    sc.render_frames(scn, sc.ROOT / "renders" / "S10", FIRST, LAST)
