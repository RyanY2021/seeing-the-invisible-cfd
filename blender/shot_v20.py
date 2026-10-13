"""V20 — AIRCRAFT: a black light aircraft (drawn by highlights, magenta neon stripes) streaks over the camera at
night and punches through a smoke curtain on the bar-108 downbeat; its wing-tip vortices wind the smoke into
spirals (Krasny vortex-sheet roll-up, src/sim_wing.py 336 4.0 wing_tex_v2). Clawd rides the near wingtip.
Synthwave sky, sun ahead, grid far below. Cycles.

blender.exe -b --factory-startup --python blender/shot_v20.py -- <test|render> <first> <last> [samples]
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
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 48
PCT = 100
DENS = 1.8
NFR = 6 * 48 + 24
ALT = 9.0
SEMI = 6.0
YR = (-2.6, 2.6)
ZR = (-1.6, 1.0)
U = 16.7  # m/s (slow-motion feel)
X0 = -66.8   # the wing reaches the curtain at t = 4.0 s (frame 97 = bar 108)

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.eevee.volumetric_tile_size = "2"
scn.eevee.volumetric_samples = 128
scn.eevee.volumetric_end = 400.0
scn.render.resolution_percentage = PCT
scn.render.use_motion_blur = True
scn.render.motion_blur_shutter = 0.25
if hasattr(scn.cycles, "volume_step_rate"):
    scn.cycles.volume_step_rate = 1.0

# ---------------------------------------------------------------- sky (HDRI rotated so the sun is front-left)
from mathutils import Vector  # noqa: E402

cw.synth_sky(scn, top=(0.004, 0.002, 0.014), mid=(0.06, 0.008, 0.08), horizon=(0.55, 0.12, 0.2), strength=0.8)
sun_ob = cw.synth_sun(loc=(900, 60, 40), radius=150)
sun_ob.rotation_euler = (math.pi / 2, 0, -math.pi / 2)    # face the camera looking down +x
cw.synth_floor(spacing=6.0, strength=2.0, width=0.08, fade=260.0)
moon = bpy.data.lights.new("Moon", "SUN")
moon.energy = 0.08
moon.color = (0.6, 0.7, 1.0)
mo = bpy.data.objects.new("Moon", moon)
sc.link(mo)
mo.rotation_euler = (math.radians(35), 0, math.radians(-120))
# long strip lights above the flight path: the black paint shows only their reflections ('car-ad' look)
for i, yy in enumerate((-3.0, 0.0, 3.0)):
    st.strip_softbox((-10, yy, 16.0), size=(40.0, 0.6), energy=9000.0, target=(-10, yy, 9), name=f"Strip{i}",
                     visible=False)
# coloured smoke lights: magenta from above-behind, cyan from the side
for nm, loc, col, e in (("SmokeMag", (8, 14, 22), st.MAGENTA, 90000.0), ("SmokeCyan", (6, -22, 10), st.CYAN, 70000.0)):
    lt = sc.add_light(nm, "SPOT", loc, e, color=col, size=2.0, target=(1.8, 0, 8.0), spot_size=math.radians(40), blend=0.5)


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
colm.inputs["A"].default_value = (0.008, 0.008, 0.01, 1)
colm.inputs["B"].default_value = (0.9, 0.05, 0.5, 1)
nt2.links.new(red_on.outputs[0], colm.inputs["Factor"])
nt2.links.new(colm.outputs["Result"], p.inputs["Base Color"])
p.inputs["Emission Color"].default_value = (1.0, 0.09, 0.62, 1)
ems = nt2.nodes.new("ShaderNodeMath")
ems.operation = "MULTIPLY"
ems.inputs[1].default_value = 25.0
nt2.links.new(red_on.outputs[0], ems.inputs[0])
nt2.links.new(ems.outputs[0], p.inputs["Emission Strength"])
p.inputs["Coat Weight"].default_value = 1.0
p.inputs["Roughness"].default_value = 0.12
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
    o.data.materials.append(sc.emission_mat(f"Nav{yy}", col, 400.0))
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
im = bpy.data.images.load(str(sc.ROOT / "cache" / "wing_tex_v2" / "0000.png"))
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
pv.inputs["Color"].default_value = (0.8, 0.8, 0.86, 1)
pv.inputs["Anisotropy"].default_value = 0.3
nt3.links.new(m4.outputs[0], pv.inputs["Density"])
nt3.links.new(pv.outputs[0], out.inputs["Volume"])
cur.data.materials.append(m)

# ---------------------------------------------------------------- camera
cl = clawd.Clawd("Clawd", unit=0.11, location=(0, 0, 0), rotation_z=math.radians(-90))
cl.root.parent = plane
cl.root.location = (0.3, -4.6, 0.45)
ck = bpy.data.lights.new("ClawdLight", "POINT")
ck.energy = 900.0
ck.color = (1.0, 0.85, 0.75)
ck.shadow_soft_size = 0.8
cko = bpy.data.objects.new("ClawdLight", ck)
cko.parent = plane
cko.location = (-2.5, -6.0, 2.0)
sc.link(cko)
linked = bpy.data.collections.new("ClawdOnly")
for o in cl.parts:
    if o.type == "MESH":
        linked.objects.link(o)
cko.light_linking.receiver_collection = linked
cl.arm(1, "L", 70)
cl.arm(1, "R", 70)
cl.squash_to(1, 0.85)
cl.look(1, 0, 1)
cl.say(60, "wheee!", 30)
cl.surprise(97)
cl.look(110, -1, 0)
cl.look(200, -1, -1)
for k, f in enumerate(range(1, NFR, 6)):
    cl.tilt(f, 6 * math.sin(k * 0.9))

# chase camera: locked to the plane, Clawd big on the near wing tip, the curtain rushing up ahead
chase_d = bpy.data.cameras.new("Chase")
chase_d.lens = 28.0
chase_d.clip_start, chase_d.clip_end = 0.1, 3000
chase = bpy.data.objects.new("Chase", chase_d)
sc.link(chase)
chase.parent = plane
chase.location = (-4.2, -7.6, 1.6)
chase.rotation_euler = (math.radians(82), 0, math.radians(-58))
cam = sc.add_camera(lens=30.0, clip=(0.1, 3000))
tgt = sc.target_empty("CamTarget", (0, 0, 7.0))
sc.track_to(cam, tgt)
for f, cl_, tl in ((1, (-36.0, -4.5, 6.8), (0, 0.0, 10.5)), (60, (-33.0, -4.0, 6.9), (0, 0.3, 9.6)),
                   (97, (-30.0, -3.5, 7.0), (0, 0.5, 8.6)), (NFR, (-25.5, -2.5, 6.8), (0, 0.3, 7.6))):
    cam.location = cl_
    cam.keyframe_insert("location", frame=f)
    tgt.location = tl
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)
scn.frame_start, scn.frame_end = 1, NFR
m0 = scn.timeline_markers.new("chase", frame=1)
m0.camera = chase
m1 = scn.timeline_markers.new("wide", frame=97)
m1.camera = cam
scn.camera = chase

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V20")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, NFR)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V20_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
