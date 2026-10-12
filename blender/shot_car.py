"""S11 — clay car in a wind tunnel with smoke streaklines (VDB from sim_car.py).

blender.exe -b --factory-startup --python blender/shot_car.py -- <mode> <first> <last> [pct] [samples] [vdb_force] [dens]
  mode: S11 (final frames -> renders/S11), test (-> cache/lookdev)
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import car_common as cc  # noqa: E402
import scene_common as sc  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
PCT = int(A[3]) if len(A) > 3 else 100
SAMPLES = int(A[4]) if len(A) > 4 else 64
VDB_FORCE = int(A[5]) if len(A) > 5 else -1
DENS = float(A[6]) if len(A) > 6 else 60.0
NFR = 200

scn = sc.reset_scene()
sc.setup_cycles(scn, samples=SAMPLES, bounces=(4, 1, 2), adaptive=0.02)
scn.render.resolution_percentage = PCT
if hasattr(scn.cycles, "volume_step_rate"):
    scn.cycles.volume_step_rate = 1.0
sc.world_color(scn, (0.004, 0.0045, 0.005), 1.0)

# ---------------------------------------------------------------- car
root, body, wheels = cc.build_car()

# ---------------------------------------------------------------- smoke
VDB = sc.ROOT / "cache" / "car_vdb"
vol = bpy.data.volumes.new("Smoke")
vol.filepath = str(VDB / "car_0000.vdb")
vol.is_sequence = True
vol.frame_duration = NFR
vol.frame_start = 1
vol.frame_offset = -1
vol.sequence_mode = "CLIP"
smoke = bpy.data.objects.new("Smoke", vol)
sc.link(smoke)
smoke.scale = (0.015, 0.015, 0.015)
smoke.location = (-1.0, -1.5, 0.0)
m, nt, out = sc.new_material("SmokeMat")
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "density"
attr.attribute_type = "GEOMETRY"
sat = nt.nodes.new("ShaderNodeMath")  # soft saturation keeps dense knots from turning to solid white
sat.operation = "DIVIDE"
add1 = nt.nodes.new("ShaderNodeMath")
add1.operation = "ADD"
add1.inputs[1].default_value = 1.0
nt.links.new(attr.outputs["Fac"], add1.inputs[0])
nt.links.new(attr.outputs["Fac"], sat.inputs[0])
nt.links.new(add1.outputs[0], sat.inputs[1])
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = DENS
nt.links.new(sat.outputs[0], mul.inputs[0])
pv = nt.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Color"].default_value = (0.9, 0.92, 0.95, 1)
pv.inputs["Anisotropy"].default_value = 0.35
nt.links.new(mul.outputs[0], pv.inputs["Density"])
nt.links.new(pv.outputs[0], out.inputs["Volume"])
smoke.data.materials.append(m)

# ---------------------------------------------------------------- tunnel
bpy.ops.mesh.primitive_plane_add(size=60, location=(3, 0, 0))
floor = bpy.context.active_object
m, nt, out = sc.new_material("Floor")
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Roughness"].default_value = 0.32
tc = nt.nodes.new("ShaderNodeTexCoord")
# turntable ring + faint panel seams
vl = nt.nodes.new("ShaderNodeVectorMath")
vl.operation = "DISTANCE"
vl.inputs[1].default_value = (2.25, 0, 0)
nt.links.new(tc.outputs["Object"], vl.inputs[0])
ring = nt.nodes.new("ShaderNodeMapRange")
ring.inputs["From Min"].default_value = 3.0
ring.inputs["From Max"].default_value = 3.02
ring.interpolation_type = "SMOOTHSTEP"
nt.links.new(vl.outputs["Value"], ring.inputs["Value"])
ring2 = nt.nodes.new("ShaderNodeMapRange")
ring2.inputs["From Min"].default_value = 3.05
ring2.inputs["From Max"].default_value = 3.03
ring2.interpolation_type = "SMOOTHSTEP"
nt.links.new(vl.outputs["Value"], ring2.inputs["Value"])
rmin = nt.nodes.new("ShaderNodeMath")
rmin.operation = "MINIMUM"
nt.links.new(ring.outputs["Result"], rmin.inputs[0])
nt.links.new(ring2.outputs["Result"], rmin.inputs[1])
noise = nt.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 3.0
nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
colmix = nt.nodes.new("ShaderNodeMix")
colmix.data_type = "RGBA"
colmix.inputs["A"].default_value = (0.030, 0.031, 0.034, 1)
colmix.inputs["B"].default_value = (0.20, 0.20, 0.21, 1)
nt.links.new(rmin.outputs[0], colmix.inputs["Factor"])
nmix = nt.nodes.new("ShaderNodeMix")
nmix.data_type = "RGBA"
nmix.blend_type = "MULTIPLY"
nmix.inputs["Factor"].default_value = 0.25
nt.links.new(colmix.outputs["Result"], nmix.inputs["A"])
nt.links.new(noise.outputs["Color"], nmix.inputs["B"])
nt.links.new(nmix.outputs["Result"], p.inputs["Base Color"])
nt.links.new(p.outputs[0], out.inputs["Surface"])
floor.data.materials.append(m)

wall_m, _, _ = sc.principled("Wall", base=(0.02, 0.021, 0.024), rough=0.8)
for y in (-6.5, 6.5):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(3, y, 2.5), rotation=(math.pi / 2, 0, 0))
    w = bpy.context.active_object
    w.scale = (40, 5, 1)
    w.data.materials.append(wall_m)
bpy.ops.mesh.primitive_plane_add(size=1, location=(3, 0, 5.0))
ceil = bpy.context.active_object
ceil.scale = (40, 13, 1)
ceil.data.materials.append(wall_m)
# ceiling light strips along the flow
strip = sc.emission_mat("Strip", (1.0, 0.97, 0.93), 6.0)
for y in (-2.4, -0.8, 0.8, 2.4):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(2.25, y, 4.95))
    s_ = bpy.context.active_object
    s_.scale = (9.0, 0.22, 1)
    s_.rotation_euler[0] = math.pi
    s_.data.materials.append(strip)

# smoke rake: struts + nozzles (dark anodised metal)
rk_m, _, _ = sc.principled("Rake", base=(0.05, 0.05, 0.055), rough=0.35, metal=0.8)
for yl, z0, z1 in ((0.0, 0.0, 1.82), (-0.62, 0.0, 1.20), (0.62, 0.0, 1.20)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.014, depth=z1 - z0, location=(-0.78, yl, (z0 + z1) / 2))
    bpy.context.active_object.data.materials.append(rk_m)
import numpy as np  # noqa: E402

for zu in np.arange(0.22, 1.75, 0.075):
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.004, depth=0.23, location=(-0.665, 0.0, zu),
                                        rotation=(0, math.pi / 2, 0))
    bpy.context.active_object.data.materials.append(rk_m)
for yl in (-0.62, 0.62):
    for zu in np.arange(0.30, 1.20, 0.15):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.004, depth=0.23, location=(-0.665, yl, zu),
                                            rotation=(0, math.pi / 2, 0))
        bpy.context.active_object.data.materials.append(rk_m)

# lights for the smoke (strong, from above/behind the plane of the rake)
sc.add_light("SmokeKeyA", "SPOT", (1.0, 3.5, 4.2), 2600, color=(0.95, 0.97, 1.0), size=0.4, target=(2.0, 0, 0.9),
             spot_size=math.radians(55), blend=0.5)
sc.add_light("SmokeKeyB", "SPOT", (5.5, 3.2, 3.8), 2200, color=(1.0, 0.95, 0.9), size=0.4, target=(5.0, 0, 0.8),
             spot_size=math.radians(55), blend=0.5)
sc.add_light("CarFill", "AREA", (2.25, -5.0, 2.2), 260, color=(0.85, 0.9, 1.0), size=3.0, target=(2.25, 0, 0.6))

# ---------------------------------------------------------------- camera
cam = sc.add_camera(lens=40.0, dof=5.6, clip=(0.05, 200))
tgt = sc.target_empty("CamTarget", (2.0, 0, 0.75))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt


def key(f, cl, tl):
    cam.location = cl
    cam.keyframe_insert("location", frame=f)
    tgt.location = tl
    tgt.keyframe_insert("location", frame=f)


key(1, (0.2, -6.4, 1.05), (2.0, 0.0, 0.80))
key(NFR, (3.4, -6.9, 1.20), (3.6, 0.0, 0.80))
for o in (cam, tgt):
    sc.smooth_keys(o)
scn.frame_start, scn.frame_end = 1, NFR

if MODE == "test":
    outd = sc.ROOT / "cache" / "lookdev"
    outd.mkdir(parents=True, exist_ok=True)
    f = FIRST
    if VDB_FORCE >= 0:
        vol.frame_start = f
        vol.frame_duration = 1
        vol.frame_offset = VDB_FORCE - 1
    scn.frame_set(f)
    scn.render.filepath = str(outd / f"car_scene_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "car_tunnel.blend"))
else:
    sc.render_frames(scn, sc.ROOT / "renders" / "S11", FIRST, LAST)
