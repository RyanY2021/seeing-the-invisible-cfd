"""V21 — CARS: car-ad wind tunnel. A black car drawn only by sliding strip highlights; v1's smoke streaklines
(cache/car_vdb, 3D LBM) flow over it, lit magenta -> cyan; Clawd stands at the smoke rake. The camera dollies from
the nose along the side to the wake. Eevee.

blender.exe -b --factory-startup --python blender/shot_v21.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import car_common as cc  # noqa: E402
import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 100
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.eevee.volumetric_tile_size = "2"
scn.eevee.volumetric_samples = 128
scn.eevee.volumetric_end = 60.0
scn.frame_start, scn.frame_end = 1, N
sc.world_color(scn, (0.0015, 0.001, 0.003), 1.0)
st.lacquer_floor(size=80, rough=0.1)

body = cc.body_material(color=(0.004, 0.004, 0.005), rough=0.06, coat=1.0)
car, _, wheels = cc.build_car(body_mat=body)
wheels.data.materials[0] = sc.principled("Tyre", base=(0.006, 0.006, 0.007), rough=0.6)[0]

VDB = sc.ROOT / "cache" / "car_vdb"
vol = bpy.data.volumes.new("Smoke")
vol.filepath = str(VDB / "car_0000.vdb")
vol.is_sequence = True
vol.frame_duration = 200
vol.frame_start = 1
vol.frame_offset = -17          # scene frame 216 -> file 0199 (the sim has 0000-0200)
vol.sequence_mode = "EXTEND"
smoke = bpy.data.objects.new("Smoke", vol)
sc.link(smoke)
smoke.scale = (0.015, 0.015, 0.015)
smoke.location = (-1.0, -1.5, 0.0)
m, nt, out = sc.new_material("SmokeMat")
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "density"
attr.attribute_type = "GEOMETRY"
add1 = nt.nodes.new("ShaderNodeMath")
add1.operation = "ADD"
add1.inputs[1].default_value = 1.0
nt.links.new(attr.outputs["Fac"], add1.inputs[0])
sat = nt.nodes.new("ShaderNodeMath")
sat.operation = "DIVIDE"
nt.links.new(attr.outputs["Fac"], sat.inputs[0])
nt.links.new(add1.outputs[0], sat.inputs[1])
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = 30.0
nt.links.new(sat.outputs[0], mul.inputs[0])
pv = nt.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Color"].default_value = (0.95, 0.95, 0.97, 1)
pv.inputs["Anisotropy"].default_value = 0.45
nt.links.new(mul.outputs[0], pv.inputs["Density"])
# a faint emission tinted along the tunnel (magenta at the rake -> cyan in the wake) keeps the streaks neon
geo = nt.nodes.new("ShaderNodeNewGeometry")
sx = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(geo.outputs["Position"], sx.inputs[0])
mr = nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = -0.5
mr.inputs["From Max"].default_value = 6.0
nt.links.new(sx.outputs["X"], mr.inputs["Value"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (*st.MAGENTA, 1)
ramp.color_ramp.elements[1].color = (*st.CYAN, 1)
nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], pv.inputs["Emission Color"])
emm = nt.nodes.new("ShaderNodeMath")
emm.operation = "MULTIPLY"
emm.inputs[1].default_value = 1.2
nt.links.new(sat.outputs[0], emm.inputs[0])
nt.links.new(emm.outputs[0], pv.inputs["Emission Strength"])
nt.links.new(pv.outputs[0], out.inputs["Volume"])
smoke.data.materials.append(m)

rk_m, _, _ = sc.principled("Rake", base=(0.05, 0.05, 0.055), rough=0.3, metal=0.9)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.014, depth=1.86, location=(-0.78, 0.0, 0.93))
bpy.context.active_object.data.materials.append(rk_m)

# sliding strip highlights: three long softboxes glide along the car (the 'car-ad' reveal)
for i, y in enumerate((-1.1, 0.0, 1.1)):
    lt = st.strip_softbox((2.25, y, 3.2), size=(3.0, 0.12), energy=180.0, target=(2.25, y, 0), name=f"Over{i}",
                          visible=False)
    for f, x in ((1, -3.0 + i), (N, 7.5 + i)):
        lt.location.x = x
        lt.keyframe_insert("location", frame=f)
kick = st.strip_softbox((2.25, -4.0, 0.9), size=(9.0, 0.08), energy=50.0, color=(0.9, 0.95, 1.0), target=(2.25, 0, 0.55),
                        name="Kicker", visible=False)
sm1 = sc.add_light("SmokeMag", "SPOT", (0.6, 3.6, 4.0), 2600, color=st.MAGENTA, size=0.4, target=(1.8, 0, 1.0),
                   spot_size=math.radians(55), blend=0.5)
sm2 = sc.add_light("SmokeCyan", "SPOT", (5.6, 3.2, 3.6), 2400, color=st.CYAN, size=0.4, target=(5.2, 0, 0.9),
                   spot_size=math.radians(55), blend=0.5)
for lt in (sm1, sm2):
    lt.data.specular_factor = 0.0
st.neon_tube([(-6, 7, 0.02), (14, 7, 0.02)], st.VIOLET, 20.0, radius=0.03, name="FloorNeon", light_energy=150)

# Clawd at the rake
cl = clawd.Clawd("Clawd", unit=0.045, location=(-1.55, -0.9, 0.0), rotation_z=math.radians(-40))
ck = sc.add_light("ClawdKey", "AREA", (-3.0, -3.0, 1.6), 60.0, color=(1.0, 0.8, 0.7), size=0.8, target=(-1.55, -0.9, 0.3))
ck.data.specular_factor = 0.0
cl.look(1, 1, 1)
cl.arm(1, "R", 30)
cl.say(30, "less drag!", 36)
cl.look(90, 1, 0)
cl.blink(120)
cl.breathe(1, N, 24, 0.03)

# exclude the car and Clawd from the smoke lights (car-ad control)
not_smoke = bpy.data.collections.new("NotLitBySmokeLights")
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith(("Car", "Clawd", "Cylinder")):
        not_smoke.objects.link(o)
for o in not_smoke.collection_objects:
    o.light_linking.link_state = "EXCLUDE"
for lt in (sm1, sm2):
    lt.light_linking.receiver_collection = not_smoke

cam = sc.add_camera(lens=35.0, dof=8.0, clip=(0.05, 300))
tgt = sc.target_empty("T", (0, 0, 0.7))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
for f, loc, t in ((1, (-3.6, -3.4, 0.55), (-0.6, 0.0, 0.75)), (100, (-1.0, -5.2, 0.7), (1.8, 0.0, 0.8)),
                  (N, (3.6, -6.2, 0.9), (5.0, 0.0, 0.85))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V21")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V21_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
