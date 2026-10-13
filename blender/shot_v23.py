"""V23 — WEATHER: the night-side Earth with real GFS surface winds (2026-10-12/13) as neon streaks (calm = cyan,
strong = magenta), pink city lights, violet atmosphere; Clawd drifts past like a satellite and points at the
storm. (Based on v1 shot_earth.py; streaks from src/shot_s13_wind.py 216 wind_tex_v2.) Eevee.

blender.exe -b --factory-startup --python blender/shot_v23.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as stu  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
PCT = 100
NFR = 4 * 48 + 24
FPS = 24

scn = sc.reset_scene()
stu.setup_render(scn, "eevee", SAMPLES)
scn.eevee.use_raytracing = False
scn.frame_start, scn.frame_end = 1, NFR

# world: black with faint stars
w = bpy.data.worlds.new("World")
scn.world = w
w.use_nodes = True
wn = w.node_tree
bg = wn.nodes.get("Background")
tcw = wn.nodes.new("ShaderNodeTexCoord")
vor = wn.nodes.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 420.0
wn.links.new(tcw.outputs["Generated"], vor.inputs["Vector"])
st = wn.nodes.new("ShaderNodeMapRange")
st.inputs["From Min"].default_value = 0.03
st.inputs["From Max"].default_value = 0.0
st.inputs["To Max"].default_value = 0.6
wn.links.new(vor.outputs["Distance"], st.inputs["Value"])
bg.inputs["Color"].default_value = (1, 1, 1, 1)
wn.links.new(st.outputs["Result"], bg.inputs["Strength"])

_lat, _lon = math.radians(33.0), math.radians(-35.0)
_d = Vector((math.cos(_lat) * math.cos(_lon), math.cos(_lat) * math.sin(_lon), math.sin(_lat)))
_side = _d.cross(Vector((0, 0, 1))).normalized()
SUN_DIR = (-0.55 * _d + 0.8 * _side + 0.25 * Vector((0, 0, 1))).normalized()  # mostly behind: night side faces us
sun_d = bpy.data.lights.new("Sun", "SUN")
sun_d.energy = 5.0
sun_d.color = (1.0, 0.97, 0.92)
sun = bpy.data.objects.new("Sun", sun_d)
sc.link(sun)
sun.rotation_euler = (-SUN_DIR).to_track_quat("-Z", "Y").to_euler()


def latlon_uv(nt, offset_u=0.5):
    """u = lon/2pi + offset, v = lat/pi + 0.5 from object-space position on the unit sphere."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Object"], nrm.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nrm.outputs[0], sep.inputs[0])
    lon = nt.nodes.new("ShaderNodeMath")
    lon.operation = "ARCTAN2"
    nt.links.new(sep.outputs["Y"], lon.inputs[0])
    nt.links.new(sep.outputs["X"], lon.inputs[1])
    u = nt.nodes.new("ShaderNodeMath")
    u.operation = "MULTIPLY_ADD"
    u.inputs[1].default_value = 1 / (2 * math.pi)
    u.inputs[2].default_value = offset_u
    nt.links.new(lon.outputs[0], u.inputs[0])
    uw = nt.nodes.new("ShaderNodeMath")
    uw.operation = "FRACT"
    nt.links.new(u.outputs[0], uw.inputs[0])
    lat = nt.nodes.new("ShaderNodeMath")
    lat.operation = "ARCSINE"
    nt.links.new(sep.outputs["Z"], lat.inputs[0])
    v = nt.nodes.new("ShaderNodeMath")
    v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = 1 / math.pi
    v.inputs[2].default_value = 0.5
    nt.links.new(lat.outputs[0], v.inputs[0])
    uv = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(uw.outputs[0], uv.inputs["X"])
    nt.links.new(v.outputs[0], uv.inputs["Y"])
    return uv


def night_mask(nt):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = tuple(SUN_DIR)
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = 0.08
    mr.inputs["From Max"].default_value = -0.18
    nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
    return mr


def tex(nt, path, uv, colorspace="sRGB", seq=False):
    t = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(str(path))
    img.colorspace_settings.name = colorspace
    if seq:
        img.source = "SEQUENCE"
        t.image_user.frame_duration = NFR
        t.image_user.frame_start = 1
        t.image_user.frame_offset = -1
        t.image_user.use_auto_refresh = True
    t.image = img
    t.interpolation = "Cubic"
    nt.links.new(uv.outputs[0], t.inputs["Vector"])
    return t


EARTH = sc.ROOT / "assets" / "earth"
earth_root = bpy.data.objects.new("EarthRoot", None)
sc.link(earth_root)


def sphere(name, r, segs=256):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=segs // 2)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.parent = earth_root
    return o


# surface
earth = sphere("Earth", 1.0)
m, nt, out = sc.new_material("EarthSurface")
uv = latlon_uv(nt, 0.5)
day = tex(nt, EARTH / "bluemarble_5400.jpg", uv)
nightt = tex(nt, EARTH / "blackmarble_3600.jpg", uv)
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
nt.links.new(day.outputs["Color"], p.inputs["Base Color"])
sepc = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(day.outputs["Color"], sepc.inputs[0])
wm = nt.nodes.new("ShaderNodeMath")  # water mask: blue > red
wm.operation = "SUBTRACT"
nt.links.new(sepc.outputs[2], wm.inputs[0])
nt.links.new(sepc.outputs[0], wm.inputs[1])
wr = nt.nodes.new("ShaderNodeMapRange")
wr.inputs["From Min"].default_value = 0.0
wr.inputs["From Max"].default_value = 0.08
wr.inputs["To Min"].default_value = 0.85
wr.inputs["To Max"].default_value = 0.32
nt.links.new(wm.outputs[0], wr.inputs["Value"])
nt.links.new(wr.outputs["Result"], p.inputs["Roughness"])
nm = night_mask(nt)
em = nt.nodes.new("ShaderNodeMath")
em.operation = "MULTIPLY"
sepn = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(nightt.outputs["Color"], sepn.inputs[0])
lumpow = nt.nodes.new("ShaderNodeMath")
lumpow.operation = "POWER"
lumpow.inputs[1].default_value = 2.2
nt.links.new(sepn.outputs[0], lumpow.inputs[0])
nt.links.new(lumpow.outputs[0], em.inputs[0])
nt.links.new(nm.outputs["Result"], em.inputs[1])
p.inputs["Emission Color"].default_value = (1.0, 0.42, 0.62, 1)
emk = nt.nodes.new("ShaderNodeMath")
emk.operation = "MULTIPLY"
emk.inputs[1].default_value = 6.0
nt.links.new(em.outputs[0], emk.inputs[0])
nt.links.new(emk.outputs[0], p.inputs["Emission Strength"])
nt.links.new(p.outputs[0], out.inputs["Surface"])
earth.data.materials.append(m)

# clouds
clouds = sphere("Clouds", 1.006)
m, nt, out = sc.new_material("Clouds")
uv = latlon_uv(nt, 0.5)
ct = tex(nt, EARTH / "clouds_2048.jpg", uv, "Non-Color")
sepc = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(ct.outputs["Color"], sepc.inputs[0])
ca = nt.nodes.new("ShaderNodeMapRange")
ca.inputs["From Min"].default_value = 0.12
ca.inputs["From Max"].default_value = 0.9
ca.inputs["To Max"].default_value = 0.45
nt.links.new(sepc.outputs[0], ca.inputs["Value"])
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Base Color"].default_value = (0.95, 0.95, 0.96, 1)
p.inputs["Roughness"].default_value = 0.9
nt.links.new(ca.outputs["Result"], p.inputs["Alpha"])
nt.links.new(p.outputs[0], out.inputs["Surface"])
clouds.data.materials.append(m)

# wind streaks (emissive overlay)
wind = sphere("Wind", 1.010)
m, nt, out = sc.new_material("Wind")
uv = latlon_uv(nt, 0.0)
wt = tex(nt, sc.ROOT / "cache" / "wind_tex_v2" / "0000.png", uv, "sRGB", seq=True)
wt.interpolation = "Linear"
e = nt.nodes.new("ShaderNodeEmission")
nt.links.new(wt.outputs["Color"], e.inputs["Color"])
nm = night_mask(nt)
sk = nt.nodes.new("ShaderNodeMapRange")  # a little brighter on the night side
sk.inputs["To Min"].default_value = 2.2
sk.inputs["To Max"].default_value = 3.2
nt.links.new(nm.outputs["Result"], sk.inputs["Value"])
nt.links.new(sk.outputs["Result"], e.inputs["Strength"])
trn = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(wt.outputs["Alpha"], mix.inputs["Fac"])
nt.links.new(trn.outputs[0], mix.inputs[1])
nt.links.new(e.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs["Surface"])
wind.data.materials.append(m)

# atmosphere limb glow
atm = sphere("Atmosphere", 1.04, 128)
m, nt, out = sc.new_material("Atmosphere")
lw = nt.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.5
pw = nt.nodes.new("ShaderNodeMath")
pw.operation = "POWER"
pw.inputs[1].default_value = 3.0
nt.links.new(lw.outputs["Facing"], pw.inputs[0])
geo = nt.nodes.new("ShaderNodeNewGeometry")
dot = nt.nodes.new("ShaderNodeVectorMath")
dot.operation = "DOT_PRODUCT"
dot.inputs[1].default_value = tuple(SUN_DIR)
nt.links.new(geo.outputs["Normal"], dot.inputs[0])
dl = nt.nodes.new("ShaderNodeMapRange")
dl.inputs["From Min"].default_value = -0.3
dl.inputs["From Max"].default_value = 0.6
dl.inputs["To Min"].default_value = 0.05
nt.links.new(dot.outputs["Value"], dl.inputs["Value"])
mm = nt.nodes.new("ShaderNodeMath")
mm.operation = "MULTIPLY"
nt.links.new(pw.outputs[0], mm.inputs[0])
nt.links.new(dl.outputs["Result"], mm.inputs[1])
mk = nt.nodes.new("ShaderNodeMath")
mk.operation = "MULTIPLY"
mk.inputs[1].default_value = 9.0
nt.links.new(mm.outputs[0], mk.inputs[0])
ea = nt.nodes.new("ShaderNodeEmission")
ea.inputs["Color"].default_value = (0.55, 0.22, 1.0, 1)
nt.links.new(mk.outputs[0], ea.inputs["Strength"])
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
ad = nt.nodes.new("ShaderNodeAddShader")
nt.links.new(tr.outputs[0], ad.inputs[0])
nt.links.new(ea.outputs[0], ad.inputs[1])
nt.links.new(ad.outputs[0], out.inputs["Surface"])
atm.data.materials.append(m)

# orientation: slow spin (Earth rotates eastward -> positive about +Z)
for f, ang in ((1, 0.0), (NFR, math.radians(5.0))):
    earth_root.rotation_euler = (0, 0, ang)
    earth_root.keyframe_insert("rotation_euler", frame=f)
sc.smooth_keys(earth_root, interp="LINEAR")

# camera looking at lat 33N, lon 35W
lat, lon = math.radians(33.0), math.radians(-35.0)
d = Vector((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)))
cam = sc.add_camera(lens=50.0, clip=(0.01, 100))
cam.data.shift_x = -0.14                     # globe right of centre: room for the lower-left title
tgt = sc.target_empty("CamTarget", (0, 0, 0))
sc.track_to(cam, tgt)
side = d.cross(Vector((0, 0, 1))).normalized()
for f, dist, off in ((1, 5.45, 0.10), (NFR, 5.0, -0.02)):
    cam.location = d * dist + side * off
    cam.keyframe_insert("location", frame=f)
    tgt.location = side * (off * 0.4) + Vector((0, 0, -0.03))
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

# ---------------------------------------------------------------- Clawd drifts by like a satellite and points
cl = clawd.Clawd("Clawd", unit=0.011, location=(0, 0, 0), rotation_z=0)
p0 = _d * 2.35 + _side * 0.55 + Vector((0, 0, 0.18))
p1 = _d * 2.45 + _side * 0.25 + Vector((0, 0, 0.12))
for f, pp in ((1, p0), (NFR, p1)):
    cl.root.location = pp
    cl.root.keyframe_insert("location", frame=f)
look_q = _d.to_track_quat("-Y", "Z").to_euler()        # front (-Y) faces the camera
for f, extra in ((1, 0.0), (NFR, 0.35)):
    cl.root.rotation_euler = (look_q.x + 0.12, look_q.y, look_q.z + extra)
    cl.root.keyframe_insert("rotation_euler", frame=f)
cl.arm(1, "L", 40)
cl.arm(1, "R", 40)
cl.look(1, -1, -1)
cl.arm(70, "R", 40)
cl.arm(80, "R", 85)
cl.say(84, "storm ahead!", 40)
cl.arm(150, "R", 85)
cl.arm(162, "R", 40)
ck = bpy.data.lights.new("ClawdKey", "POINT")
ck.energy = 12.0
ck.color = (1.0, 0.85, 0.75)
ck.shadow_soft_size = 0.05
cko = bpy.data.objects.new("ClawdKey", ck)
sc.link(cko)
cko.location = p0 + _d * 0.6 - _side * 0.2
linked = bpy.data.collections.new("ClawdOnly")
for o in cl.parts:
    if o.type == "MESH":
        linked.objects.link(o)
cko.light_linking.receiver_collection = linked

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V23")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, NFR)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V23_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
