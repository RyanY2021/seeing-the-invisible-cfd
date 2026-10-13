"""V08 — rule 3, MOMENTUM: Clawd hops onto a little air cannon; the thump launches a smoke ring that glides across
the neon table on its own momentum (cache/v08_vdb from sim_v08_ring.py). Cycles.

blender.exe -b --factory-startup --python blender/shot_v08.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 100
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 48
N = 4 * 48 + 24
DX = 0.0015
HOLE_X, CY, CZ = 26, 72, 72
AX = (-0.17, 0.0, 0.06)                          # world position of the cannon mouth centre
X0, Y0, Z0 = AX[0] - HOLE_X * DX, AX[1] - CZ * DX, AX[2] - CY * DX

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.eevee.volumetric_tile_size = "2"
scn.eevee.volumetric_samples = 128
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.008, floor_rough=0.1, tubes=None, lights=False)
st.neon_tube([(-0.7, 0.7, 0.0), (-0.7, 0.7, 0.45)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.25, 0.8, 0.30), (0.85, 0.8, 0.30)], st.CYAN, 30.0, name="NeonB")
sc.add_light("RimMag", "SPOT", (-0.3, 0.45, 0.35), 60.0, color=st.MAGENTA, size=0.05, target=(0.0, 0, 0.06),
             spot_size=math.radians(50), blend=0.6)
sc.add_light("RimCyan", "SPOT", (0.45, 0.4, 0.30), 55.0, color=st.CYAN, size=0.05, target=(0.1, 0, 0.06),
             spot_size=math.radians(50), blend=0.6)
st.strip_softbox((-0.15, -0.4, 0.3), size=(0.4, 0.05), energy=4.0, color=(1.0, 0.85, 0.75), target=(-0.2, 0, 0.08),
                 name="Key", visible=False)

# ---------------------------------------------------------------- smoke ring VDB
vol = bpy.data.volumes.new("Ring")
vol.filepath = str(sc.ROOT / "cache" / "v08_vdb" / "ring_0000.vdb")
vol.is_sequence = True
vol.frame_duration = N
vol.frame_start = 1
vol.frame_offset = -1
ring = bpy.data.objects.new("Ring", vol)
sc.link(ring)
ring.scale = (DX / 2,) * 3
ring.location = (X0, Y0, Z0)
m, nt, out = sc.new_material("RingMat")
at = nt.nodes.new("ShaderNodeAttribute")
at.attribute_name = "density"
at.attribute_type = "GEOMETRY"
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = 45.0
nt.links.new(at.outputs["Fac"], mul.inputs[0])
pv = nt.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Color"].default_value = (0.92, 0.92, 0.96, 1)
pv.inputs["Anisotropy"].default_value = 0.5
nt.links.new(mul.outputs[0], pv.inputs["Density"])
nt.links.new(pv.outputs[0], out.inputs["Volume"])
ring.data.materials.append(m)

# ---------------------------------------------------------------- the air cannon: black box, round mouth with a neon rim
S = 0.09
bpy.ops.mesh.primitive_cube_add(size=1, location=(AX[0] - S / 2, AX[1], AX[2]))
box = bpy.context.active_object
box.scale = (S, S, AX[2] * 2)
bpy.ops.object.transform_apply(scale=True)
bv = box.modifiers.new("b", "BEVEL")
bv.width = 0.004
bv.segments = 3
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=15 * DX, depth=0.03, location=(AX[0], AX[1], AX[2]),
                                    rotation=(0, math.pi / 2, 0))
hole = bpy.context.active_object
bo = box.modifiers.new("hole", "BOOLEAN")
bo.object = hole
bo.operation = "DIFFERENCE"
hole.hide_render = True
box.data.materials.append(sc.principled("Cannon", base=(0.008, 0.008, 0.012), rough=0.15, coat=1.0)[0])
st.neon_tube([(AX[0] + 0.001, AX[1] + 16.5 * DX * math.cos(t), AX[2] + 16.5 * DX * math.sin(t))
              for t in [2 * math.pi * k / 48 for k in range(49)]], st.MAGENTA, 20.0, radius=0.0012, light=False,
             name="MouthRing")
# a drum skin on the back (what Clawd thumps)
top_z = AX[2] * 2

# ---------------------------------------------------------------- Clawd: hops onto the cannon -> THUMP -> watches the ring
U = 0.0042
cx = AX[0] - S / 2
cl = clawd.Clawd("Clawd", unit=U, location=(cx - 0.12, -0.01, 0), rotation_z=math.radians(10))
cl.walk(2, 16, (cx - 0.12, -0.01, 0), (cx - 0.07, -0.01, 0))
cl.hop(20, 31, (cx - 0.07, -0.01, 0), (cx, -0.005, top_z), height=0.05, anticip=4)    # lands at frame 31 = fire
cl.cues.append((31, "thump"))
cl.turn(36, math.radians(-25))
cl.look(36, 1, 0)
cl.look(70, 1, -1)
cl.surprise(84)
cl.say(84, "it keeps going!", 44)
cl.turn(110, math.radians(0))
cl.look(112, 0, -1)
cl.hop(116, 127, (cx, -0.005, top_z), (cx, -0.005, top_z), height=0.035, anticip=4)    # second thump at 127
cl.cues.append((127, "thump"))
cl.turn(134, math.radians(-25))
cl.look(134, 1, 0)
cl.blink(170)
cl.breathe(140, N, 24, 0.03)

cam = sc.add_camera(lens=40.0, dof=11.0, clip=(0.01, 50))
tgt = sc.target_empty("T", (-0.1, 0, 0.06))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
for f, loc, t in ((1, (-0.20, -0.52, 0.15), (-0.17, 0, 0.08)), (40, (-0.12, -0.54, 0.14), (-0.10, 0, 0.07)),
                  (N, (0.08, -0.55, 0.12), (0.06, 0, 0.06))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V08")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V08_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
