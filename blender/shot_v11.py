"""V11 — "Easy to write. Almost impossible to solve.": the equation slab (all terms lit) cracks and bursts into
prismatic shards (2D Voronoi pieces, each keeping its piece of the equations via UVs); Clawd drops with them and
lands on the table, dazed. Eevee.

blender.exe -b --factory-startup --python blender/shot_v11.py -- <test|render> <first> <last> [samples]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 30
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 2 * 48 + 24
EQ = sc.ROOT / "cache" / "v2" / "eq"
META = json.loads((EQ / "layout.json").read_text())
BW, BH = META["board"]
PX = 0.135e-3
SW, SD, SH = BW * PX * 1.04, 0.025, BH * PX * 1.1
ZC = SH / 2
BREAK = 14                                    # the slab cracks (bar 48.3)

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.07, tubes=None, lights=False)
st.neon_tube([(-0.9, 0.6, 0.0), (-0.9, 0.6, 0.5)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.5, 0.7, 0.36), (1.1, 0.7, 0.36)], st.CYAN, 30.0, name="NeonB")
sc.add_light("RimMag", "SPOT", (-0.6, 0.4, 0.4), 14.0, color=st.MAGENTA, size=0.05, target=(-0.2, 0, 0.12),
             spot_size=math.radians(45), blend=0.7)
sc.add_light("RimCyan", "SPOT", (0.6, 0.4, 0.4), 14.0, color=st.CYAN, size=0.05, target=(0.2, 0, 0.12),
             spot_size=math.radians(45), blend=0.7)
sc.add_light("Top", "AREA", (0, -0.2, 0.7), 20.0, color=(1, 0.95, 0.95), size=0.6, target=(0, 0, 0.1))

# ---------------------------------------------------------------- Voronoi fracture of the slab face
rng = np.random.default_rng(11)
impact = np.array([-0.02, SH * 0.92])                 # (x, z) where Clawd stands: cracks radiate from here
seeds = []
while len(seeds) < 64:
    p = np.array([rng.uniform(-SW / 2, SW / 2), rng.uniform(0, SH)])
    d = np.linalg.norm(p - impact)
    if rng.random() < np.exp(-d / 0.12) + 0.25:
        seeds.append(p)
seeds = np.array(seeds)


def clip(poly, a, b):
    """keep the half-plane {x : (x - a).n <= 0}, n = b (Sutherland-Hodgman)"""
    out = []
    for i in range(len(poly)):
        P, Q = poly[i], poly[(i + 1) % len(poly)]
        dp, dq = np.dot(P - a, b), np.dot(Q - a, b)
        if dp <= 0:
            out.append(P)
        if dp * dq < 0:
            out.append(P + (Q - P) * dp / (dp - dq))
    return out


cells = []
rect = [np.array(v, float) for v in ((-SW / 2, 0), (SW / 2, 0), (SW / 2, SH), (-SW / 2, SH))]
for i, s in enumerate(seeds):
    poly = rect
    for j, t in enumerate(seeds):
        if i != j:
            poly = clip(poly, (s + t) / 2, t - s)
            if len(poly) < 3:
                break
    if len(poly) >= 3:
        cells.append(np.array(poly))

slab_m, nt, p = sc.principled("Slab", base=(0.004, 0.004, 0.007), rough=0.1, coat=1.0)
p.inputs["Thin Film Thickness"].default_value = 520.0
p.inputs["Thin Film IOR"].default_value = 1.6
face_m, fnt, fout = sc.new_material("Face")
tex = fnt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(str(EQ / "board_full.png"))
pf = fnt.nodes.new("ShaderNodeBsdfPrincipled")
pf.inputs["Base Color"].default_value = (0.004, 0.004, 0.007, 1)
pf.inputs["Roughness"].default_value = 0.1
pf.inputs["Coat Weight"].default_value = 1.0
pf.inputs["Thin Film Thickness"].default_value = 520.0
em = fnt.nodes.new("ShaderNodeEmission")
fnt.links.new(tex.outputs["Color"], em.inputs["Color"])
es = fnt.nodes.new("ShaderNodeMath")
es.operation = "MULTIPLY"
es.inputs[1].default_value = 3.0
fnt.links.new(tex.outputs["Alpha"], es.inputs[0])
fnt.links.new(es.outputs[0], em.inputs["Strength"])
ad = fnt.nodes.new("ShaderNodeAddShader")
fnt.links.new(pf.outputs[0], ad.inputs[0])
fnt.links.new(em.outputs[0], ad.inputs[1])
fnt.links.new(ad.outputs[0], fout.inputs["Surface"])

# board pixel <-> slab coords (the board is centred on the slab face, see shot_v10)
def uv_of(x, z):
    u = (x / PX + BW / 2) / BW
    v = 1 - ((ZC - z) / PX + BH / 2) / BH
    return u, v


shards = []
gap = 0.0006
for ci, poly in enumerate(cells):
    c = poly.mean(0)
    poly = c + (poly - c) * (1 - gap / max(np.linalg.norm(poly - c, axis=1).mean(), 1e-6))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    front = [bm.verts.new((x - c[0], -SD / 2, z - c[1])) for x, z in poly]
    back = [bm.verts.new((x - c[0], SD / 2, z - c[1])) for x, z in poly]
    ff = bm.faces.new(front[::-1])
    bf = bm.faces.new(back)
    for k in range(len(poly)):
        bm.faces.new([front[k], front[(k + 1) % len(poly)], back[(k + 1) % len(poly)], back[k]])
    bm.normal_update()
    for lp in ff.loops:
        x, z = lp.vert.co.x + c[0], lp.vert.co.z + c[1]
        lp[uvl].uv = uv_of(x, z)
    ff.material_index = 1
    me = bpy.data.meshes.new(f"Shard{ci}")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(slab_m)
    me.materials.append(face_m)
    ob = bpy.data.objects.new(f"Shard{ci}", me)
    sc.link(ob)
    ob.location = (c[0], 0, c[1])
    shards.append((ob, c))

# ---------------------------------------------------------------- shard flight: burst from the impact, gravity, floor
G = 0.75                                         # slowed gravity (looks like a slow-motion burst)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
for ob, c in shards:
    d = c - impact
    dist = np.linalg.norm(d) + 1e-3
    dirv = d / dist
    sp = 0.20 * np.exp(-dist / 0.25) + 0.035
    v = np.array([dirv[0] * sp + rng.normal(0, 0.02), -rng.uniform(0.03, 0.12), dirv[1] * sp * 0.5 + rng.uniform(0.03, 0.12)])
    w = rng.normal(0, 2.2, 3)
    pos = np.array([c[0], 0.0, c[1]])
    rot = np.zeros(3)
    delay = int(dist * 25)                       # cracks run outwards from the impact
    t0 = BREAK + delay
    half_h = 0.02
    for f in range(1, N + 1, 2):
        if f <= t0:
            ob.location = (c[0], 0, c[1])
            ob.rotation_euler = (0, 0, 0)
        else:
            t = (f - t0) / 24.0
            p_ = pos + v * t + np.array([0, 0, -0.5 * G * t * t])
            r_ = w * t
            if p_[2] < half_h:                    # landed: slide to a stop, lie flat-ish
                p_[2] = half_h * 0.6
                r_ = r_ * 0.6
            ob.location = tuple(p_)
            ob.rotation_euler = Euler(tuple(r_))
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_euler", frame=f)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"

# ---------------------------------------------------------------- Clawd: standing on top -> falls -> lands dazed
U = 0.004
x0 = impact[0]
cl = clawd.Clawd("Clawd", unit=U, location=(x0, -0.002, SH), rotation_z=0)
cl.look(1, 0, -1)
cl.surprise(BREAK - 4)
cl.say(BREAK - 2, "uh-oh", 24)
cl.place(BREAK + 2, (x0, -0.002, SH))
cl.squash_to(BREAK + 2, 1.0)
cl.squash_to(BREAK + 8, 1.2)
cl.arm(BREAK + 4, "L", 80)
cl.arm(BREAK + 4, "R", 80)
cl.place(BREAK + 46, (x0 + 0.02, -0.06, 0.0))
cl.squash_to(BREAK + 45, 1.15)
cl.squash_to(BREAK + 47, 0.7)
cl.squash_to(BREAK + 52, 1.05)
cl.squash_to(BREAK + 58, 1.0)
cl.arm(BREAK + 48, "L", 0)
cl.arm(BREAK + 48, "R", 0)
cl.cues.append((BREAK + 46, "land"))
for k, f in enumerate(range(BREAK + 56, BREAK + 86, 6)):        # dizzy: eyes look around in a circle
    dx, dz = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 0)][k % 5]
    cl.look(f, dx, dz)
cl.tilt(BREAK + 56, 8)
cl.tilt(BREAK + 68, -8)
cl.tilt(BREAK + 80, 0)
cl.look(BREAK + 88, 0, 0)
cl.blink(BREAK + 96)

cam = sc.add_camera(lens=40.0, dof=14.0, clip=(0.01, 50))
tgt = sc.target_empty("T", (0, 0, ZC))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
for f, loc, t in ((1, (0.08, -0.74, 0.16), (0.01, 0, ZC + 0.01)), (BREAK, (0.07, -0.70, 0.16), (0.0, 0, ZC)),
                  (BREAK + 40, (0.05, -0.74, 0.14), (0.0, -0.02, ZC * 0.8)), (N, (0.02, -0.80, 0.12), (0.0, -0.03, 0.06))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V11")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V11_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
