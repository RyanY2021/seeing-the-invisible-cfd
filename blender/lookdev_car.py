"""Look-dev: 'car-ad' wind tunnel — black car drawn by strip-light highlights, neon-lit smoke streaks, Clawd.
blender.exe -b --factory-startup --python blender/lookdev_car.py -- [frame] [samples]
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
FRAME = int(A[0]) if A else 150
SAMPLES = int(A[1]) if len(A) > 1 else 96

scn = sc.reset_scene()
st.setup_render(scn, "cycles", SAMPLES)
scn.cycles.volume_step_rate = 1.0
sc.world_color(scn, (0.0015, 0.001, 0.003), 1.0)
st.lacquer_floor(size=80, rough=0.12)

body = cc.body_material(color=(0.004, 0.004, 0.005), rough=0.06, coat=1.0)
car, _, _ = cc.build_car(body_mat=body)

# smoke streaks (v1 sim), white smoke coloured by the lights
VDB = sc.ROOT / "cache" / "car_vdb"
vol = bpy.data.volumes.new("Smoke")
vol.filepath = str(VDB / "car_0000.vdb")
vol.is_sequence = True
vol.frame_duration = 200
vol.frame_start = 1
vol.frame_offset = -1
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
nt.links.new(pv.outputs[0], out.inputs["Volume"])
smoke.data.materials.append(m)

# rake
rk_m, _, _ = sc.principled("Rake", base=(0.05, 0.05, 0.055), rough=0.3, metal=0.9)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.014, depth=1.86, location=(-0.78, 0.0, 0.93))
bpy.context.active_object.data.materials.append(rk_m)

# light: long overhead strips (only seen in reflections), low side kicker line, coloured smoke rims
for i, y in enumerate((-1.1, 0.0, 1.1)):
    st.strip_softbox((2.25, y, 3.2), size=(7.0, 0.12), energy=260.0, target=(2.25, y, 0), name=f"Over{i}",
                     visible=False)
st.strip_softbox((2.25, -4.0, 0.9), size=(9.0, 0.08), energy=70.0, color=(0.9, 0.95, 1.0), target=(2.25, 0, 0.55),
                 name="Kicker", visible=False)
sm1 = sc.add_light("SmokeMag", "SPOT", (0.6, 3.6, 4.0), 3200, color=st.MAGENTA, size=0.4, target=(1.8, 0, 1.0),
                   spot_size=math.radians(55), blend=0.5)
sm2 = sc.add_light("SmokeCyan", "SPOT", (5.6, 3.2, 3.6), 3000, color=st.CYAN, size=0.4, target=(5.2, 0, 0.9),
                   spot_size=math.radians(55), blend=0.5)
# light linking: the strong smoke lights only light the smoke (car-ad control: the car is drawn by the strips)
LINK_EXCLUDE = []      # filled below once Clawd exists
st.neon_tube([(-6, 7, 0.02), (14, 7, 0.02)], st.VIOLET, 25.0, radius=0.03, name="FloorNeon", light_energy=200)
st.add_haze(0.0010, size=30, center=(3, 0, 4))

cl = clawd.Clawd("Clawd", unit=0.045, location=(-1.55, -1.25, 0.0), rotation_z=math.radians(-50))
cl.look(10, 1, 1)
cl.arm(10, "R", 70)
sc.add_light("ClawdKey", "AREA", (-3.0, -3.0, 1.6), 60.0, color=(1.0, 0.8, 0.7), size=0.8, target=(-1.55, -1.25, 0.3))

not_smoke = bpy.data.collections.new("NotLitBySmokeLights")
for o in bpy.data.objects:
    if o.type == "MESH" and (o.name.startswith(("Car", "Clawd", "Cylinder"))):
        not_smoke.objects.link(o)
for o in not_smoke.collection_objects if hasattr(not_smoke, "collection_objects") else []:
    o.light_linking.link_state = "EXCLUDE"
for lt in (sm1, sm2):
    lt.light_linking.receiver_collection = not_smoke
print("excluded from smoke lights:", [o.name for o in not_smoke.objects])

cam = sc.add_camera(lens=40.0, dof=4.0, clip=(0.05, 300))
cam.location = (-5.0, -5.6, 0.75)
tgt = sc.target_empty("T", (1.6, 0.0, 0.75))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
scn.frame_set(FRAME)
scn.render.filepath = str(sc.ROOT / "cache" / "lookdev_v2" / f"car_{FRAME:04d}.exr")
bpy.ops.render.render(write_still=True)
