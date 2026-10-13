"""V09 — rule 4, CONSERVATION: a glowing hose squirts a jet of water; Clawd hops onto the nozzle and squashes it
to half its opening — the same number of droplets per second now leave twice as fast and fly much further.
Eevee.

blender.exe -b --factory-startup --python blender/shot_v09.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import streaks as sk  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 160
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24
WATER = (0.35, 0.85, 1.0)

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.06, tubes=None)
st.neon_tube([(-0.7, 0.7, 0.0), (-0.7, 0.7, 0.4)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.25, 0.8, 0.28), (0.85, 0.8, 0.28)], st.CYAN, 30.0, name="NeonB")
st.strip_softbox((-0.05, -0.4, 0.3), size=(0.4, 0.05), energy=7.0, color=(1.0, 0.85, 0.75), target=(-0.05, 0, 0.03),
                 name="Key", visible=False)

NOZ = np.array([-0.05, 0.0, 0.032])          # nozzle exit
LAND = 100                                   # Clawd lands on the nozzle (bar 40.08)
G = 1.2                                      # cartoon gravity (m/s^2) so the arcs read at table scale
ANG = math.radians(14)

# ---------------------------------------------------------------- hose (glowing translucent tube) + nozzle
cu = bpy.data.curves.new("Hose", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 0.008
cu.bevel_resolution = 6
sp = cu.splines.new("BEZIER")
pts = [(-0.75, 0.25, 0.008), (-0.40, 0.12, 0.008), (-0.16, -0.01, 0.012), (-0.075, 0.0, 0.03)]
sp.bezier_points.add(len(pts) - 1)
for bp, p in zip(sp.bezier_points, pts):
    bp.co = p
    bp.handle_left_type = bp.handle_right_type = "AUTO"
hose = bpy.data.objects.new("Hose", cu)
sc.link(hose)
m, nt, out = sc.new_material("HoseMat")
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Base Color"].default_value = (0.05, 0.25, 0.4, 1)
p.inputs["Roughness"].default_value = 0.25
p.inputs["Coat Weight"].default_value = 1.0
p.inputs["Emission Color"].default_value = (*WATER, 1)
p.inputs["Emission Strength"].default_value = 0.6
lw = nt.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.4
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = (*WATER, 1)
mr = nt.nodes.new("ShaderNodeMath")
mr.operation = "MULTIPLY"
mr.inputs[1].default_value = 3.0
nt.links.new(lw.outputs["Facing"], mr.inputs[0])
nt.links.new(mr.outputs[0], em.inputs["Strength"])
ad = nt.nodes.new("ShaderNodeAddShader")
nt.links.new(p.outputs[0], ad.inputs[0])
nt.links.new(em.outputs[0], ad.inputs[1])
nt.links.new(ad.outputs[0], out.inputs["Surface"])
hose.data.materials.append(m)
# nozzle: a short metal cylinder; its tip flattens when Clawd lands on it
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.0085, depth=0.03, location=(NOZ[0] - 0.012, 0, NOZ[2]),
                                    rotation=(0, math.pi / 2 - ANG, 0))
noz = bpy.context.active_object
noz.name = "Nozzle"
bpy.ops.object.shade_smooth()
noz.data.materials.append(sc.principled("NozzleMat", base=(0.75, 0.72, 0.7), rough=0.2, metal=1.0)[0])
for f, sz in ((1, 1.0), (LAND - 1, 1.0), (LAND + 2, 0.45), (LAND + 6, 0.55), (N, 0.55)):
    noz.scale = (1.0, 1.0 / max(sz, 0.5) ** 0.3, 1.0)
    noz.scale = (sz ** 0.0, 1.0 / sz ** 0.5 if sz < 1 else 1.0, 1.0)
    noz.scale = (1.0, 1.25 if sz < 1 else 1.0, sz)
    noz.keyframe_insert("scale", frame=f)
bpy.ops.mesh.primitive_cube_add(size=1, location=(NOZ[0] - 0.02, 0, 0.012))
stand = bpy.context.active_object
stand.scale = (0.02, 0.025, 0.024)
stand.data.materials.append(sc.principled("Stand", base=(0.01, 0.01, 0.012), rough=0.2, coat=1.0)[0])

# ---------------------------------------------------------------- the jet: a constant number of droplets per second
RATE = 3                                    # droplets per frame (never changes: nothing appears or vanishes)


def speed(t_frame):
    k = np.clip((t_frame - LAND) / 4.0, 0, 1)
    return 0.33 * (1 + k)                    # half the opening -> twice the speed


pool = []                                    # (birth frame, sub-frame offset, exit speed, lateral jitter)
rng = np.random.default_rng(2)
for f in range(-30, N + 2):
    for j in range(RATE):
        tb = f + j / RATE
        pool.append((tb, speed(tb), rng.normal(0, 0.0012), rng.normal(0, 0.0012)))
pool = np.array(pool)
nd = len(pool)


def pos(t_frame):
    """positions of all droplets at time t (frames); dead/unborn ones parked below the floor"""
    age = (t_frame - pool[:, 0]) / 24.0
    v = pool[:, 1]
    x = NOZ[0] + v * math.cos(ANG) * age
    y = pool[:, 2] + pool[:, 3] * age * 20
    z = NOZ[2] + v * math.sin(ANG) * age - 0.5 * G * age ** 2
    p = np.stack([x, y, z], -1)
    dead = (age < 0) | (z < 0.0005)
    p[dead] = (0, 0, -1)
    return p, dead


heads = np.zeros((N + 1, nd, 3), np.float32)
tails = np.zeros_like(heads)
for f in range(N + 1):
    h, dead = pos(f)
    t_, _ = pos(f - 0.45)
    t_[dead] = h[dead]
    t_[(t_[:, 2] < 0) & ~dead] = h[(t_[:, 2] < 0) & ~dead]
    heads[f], tails[f] = h, t_
cam = sc.add_camera(lens=45.0, dof=22.0, clip=(0.01, 50))
cols = np.tile(np.array(WATER, np.float32), (nd, 1)) * rng.uniform(0.8, 1.2, (nd, 1)).astype(np.float32)
jet = sk.Streaks("Jet", heads, tails, sk.streak_material("JetMat", strength=9.0), width=0.0042, colors=cols, cam=cam)
sk.register()

# ---------------------------------------------------------------- Clawd: walks up, eyes the jet, hops on the nozzle
U = 0.0042
cl = clawd.Clawd("Clawd", unit=U, location=(-0.30, -0.05, 0), rotation_z=math.radians(20))
cl.walk(14, 50, (-0.30, -0.05, 0), (-0.13, -0.05, 0))
cl.look(52, 1, 0)
cl.blink(66)
cl.hop(LAND - 12, LAND, (-0.13, -0.05, 0), (NOZ[0] - 0.012, -0.004, NOZ[2] + 0.004), height=0.03, anticip=5)
cl.cues.append((LAND, "squash"))
cl.turn(LAND + 6, math.radians(-20))
cl.look(LAND + 8, 1, -1)
cl.surprise(LAND + 14)
cl.say(LAND + 16, "zoom!", 30)
cl.breathe(LAND + 30, N, 24, 0.03)

tgt = sc.target_empty("T", (0.04, 0, 0.03))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
for f, loc, t in ((1, (-0.04, -0.62, 0.14), (-0.02, 0, 0.035)), (LAND, (0.02, -0.66, 0.13), (0.05, 0, 0.035)),
                  (N, (0.07, -0.70, 0.13), (0.08, 0, 0.035))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V09")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V09_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
