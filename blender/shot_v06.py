"""V06 — rule 1, PRESSURE: Clawd pushes a plunger into a clear acrylic tube; the jittering fluid beads crowd up
near it (magenta = high pressure) and stay sparse ahead (blue = low); the parcel is shoved towards low pressure,
a neon force arrow growing on it. Neon HIGH / LOW signs. Eevee.

blender.exe -b --factory-startup --python blender/shot_v06.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import clawd  # noqa: E402
import rules_props as rp  # noqa: E402
import scene_common as sc  # noqa: E402
import streaks as sk  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 150
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24
FONT = str(sc.ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
BLUE = (0.10, 0.35, 1.0)

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.012, floor_rough=0.08, tubes=None)
scn.eevee.use_raytracing = False    # screen-space reflections drew the force arrow as a pink slab on the floor
st.neon_tube([(-0.7, 0.8, 0.0), (-0.7, 0.8, 0.45)], st.MAGENTA, 30.0, name="NeonA")
st.neon_tube([(0.45, 0.85, 0.30), (0.95, 0.85, 0.30)], st.CYAN, 30.0, name="NeonB")
st.strip_softbox((-0.15, -0.4, 0.3), size=(0.4, 0.05), energy=7.0, color=(1.0, 0.85, 0.75), target=(0, 0, 0.05),
                 name="Key", visible=False)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- the tube
X0, X1, R, ZC = -0.18, 0.20, 0.032, 0.048
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R, depth=X1 - X0, location=((X0 + X1) / 2, 0, ZC),
                                    rotation=(0, math.pi / 2, 0))
tube = bpy.context.active_object
tube.name = "Tube"
sol = tube.modifiers.new("s", "SOLIDIFY")
sol.thickness = 0.0025
bpy.ops.object.shade_smooth()
m, nt, out = sc.new_material("TubeGlass")
m.surface_render_method = "BLENDED"
g = nt.nodes.new("ShaderNodeBsdfPrincipled")
g.inputs["Base Color"].default_value = (0.8, 0.9, 1.0, 1)
g.inputs["Roughness"].default_value = 0.03
g.inputs["Thin Film Thickness"].default_value = 450.0
g.inputs["Thin Film IOR"].default_value = 1.4
lw = nt.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.2
mx = nt.nodes.new("ShaderNodeMath")
mx.operation = "MULTIPLY_ADD"
mx.inputs[1].default_value = 0.45
mx.inputs[2].default_value = 0.015
mx.use_clamp = True
nt.links.new(lw.outputs["Fresnel"], mx.inputs[0])
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(mx.outputs[0], mix.inputs["Fac"])
nt.links.new(tr.outputs[0], mix.inputs[1])
nt.links.new(g.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs["Surface"])
tube.data.materials.append(m)
for xs in (X0 + 0.04, X1 - 0.04):                       # little black stands
    bpy.ops.mesh.primitive_cube_add(size=1, location=(xs, 0, (ZC - R) / 2))
    stand = bpy.context.active_object
    stand.scale = (0.012, 0.03, ZC - R)
    stand.data.materials.append(sc.principled("Stand", base=(0.01, 0.01, 0.012), rough=0.2, coat=1.0)[0])

# ---------------------------------------------------------------- plunger (disc + rod + handle) — Clawd pushes it
P0, P1 = -0.165, -0.085                                  # disc x before / after the push
F_PUSH0, F_PUSH1 = 50, 140
plunger = bpy.data.objects.new("Plunger", None)
sc.link(plunger)
blk = sc.principled("PlungerMat", base=(0.012, 0.012, 0.016), rough=0.18, coat=1.0)[0]
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=R * 0.93, depth=0.008, rotation=(0, math.pi / 2, 0))
disc = bpy.context.active_object
disc.data.materials.append(blk)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.004, depth=0.11, location=(-0.055, 0, 0),
                                    rotation=(0, math.pi / 2, 0))
rod = bpy.context.active_object
rod.data.materials.append(blk)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.11, 0, 0))
handle = bpy.context.active_object
handle.scale = (0.008, 0.05, 0.03)
handle.data.materials.append(blk)
for o in (disc, rod, handle):
    o.parent = plunger
st.neon_tube([(-0.108, -0.026, -0.016), (-0.108, -0.026, 0.016)], st.MAGENTA, 12.0, radius=0.0012, light=False,
             name="HandleLine").parent = plunger
for f in range(1, N + 1, 2):
    plunger.location = (P0 + (P1 - P0) * ease((f - F_PUSH0) / (F_PUSH1 - F_PUSH0)), 0, ZC)
    plunger.keyframe_insert("location", frame=f)


def disc_x(f):
    return P0 + (P1 - P0) * ease((f - F_PUSH0) / (F_PUSH1 - F_PUSH0))


# ---------------------------------------------------------------- fluid beads: crowd near the plunger
rng = np.random.default_rng(3)
nb = 1300
s0 = rng.random(nb)
rr = R * 0.85 * np.sqrt(rng.random(nb))
th = rng.random(nb) * 2 * np.pi
jit = rng.standard_normal((N + 2, nb, 3)).cumsum(0) * 0.0007
jit -= jit.mean(0)
heads = np.zeros((N + 1, nb, 3), np.float32)
tails = np.zeros_like(heads)
cols = np.zeros((nb, 3), np.float32)
dens_cols = []
for f in range(N + 1):
    xd = disc_x(f) + 0.006
    k = ease((f - F_PUSH0) / (F_PUSH1 - F_PUSH0))
    expo = 1.0 + 1.3 * k                             # bunching exponent: beads pile up against the disc
    x = xd + (X1 - 0.004 - xd) * s0 ** expo
    pos = np.stack([x, rr * np.cos(th), ZC + rr * np.sin(th)], -1)
    heads[f] = pos + np.clip(jit[f + 1], -0.003, 0.003)
    tails[f] = pos + np.clip(jit[f], -0.003, 0.003)
# colour: by how crowded the bead's neighbourhood is at the end of the push (magenta high -> blue low)
xs_end = heads[-1, :, 0]
u = np.clip((xs_end - P1) / (X1 - P1), 0, 1)
cols = (np.array(st.MAGENTA)[None] * (1 - u[:, None]) ** 1.5 + np.array(BLUE)[None] * (1 - (1 - u[:, None]) ** 1.5))
cols = cols.astype(np.float32)
cam = sc.add_camera(lens=45.0, dof=22.0, clip=(0.01, 50))
beads = sk.Streaks("Beads", heads, tails, sk.streak_material("BeadMat", strength=9.0), width=0.0045, colors=cols,
                   cam=cam)
sk.register()

# ---------------------------------------------------------------- the parcel + its force arrow
par = rp.parcel(0.02, st.CYAN, "Parcel")
par.visible_glossy = False
for f in range(1, N + 1):
    k = ease((f - F_PUSH0 - 10) / (N - F_PUSH0 - 10))
    par.location = (-0.01 + 0.15 * k ** 1.4, 0, ZC)
    par.keyframe_insert("location", frame=f)
arr = rp.arrow("Force", st.MAGENTA, length=0.05, strength=4.0)
arr.visible_glossy = False                    # its floor reflection read as a big pink block
arr.parent = par
arr.location = (0.014, 0, 0)
for f, s in ((1, 0.0), (F_PUSH0 + 4, 0.0), (F_PUSH0 + 30, 1.0), (F_PUSH1, 1.25), (N, 1.25)):
    arr.scale = (s, max(s, 0.001) ** 0.3, max(s, 0.001) ** 0.3)
    arr.keyframe_insert("scale", frame=f)

# ---------------------------------------------------------------- HIGH / LOW neon signs above the tube
hi = st.neon_text(["HIGH"], FONT, 0.016, (-0.11, 0.0, ZC + R + 0.03), st.MAGENTA, strength=30.0, board=False,
                  name="High", light_energy=0.15)
lo = st.neon_text(["LOW"], FONT, 0.016, (0.12, 0.0, ZC + R + 0.03), BLUE, strength=30.0, board=False, name="Low",
                  light_energy=0.15)
st.neon_switch(hi[0], F_PUSH0 + 10)
st.neon_switch(lo[0], F_PUSH0 + 22)

# ---------------------------------------------------------------- Clawd walks in and pushes
U = 0.0042
cl = clawd.Clawd("Clawd", unit=U, location=(-0.42, -0.01, 0), rotation_z=0)
cl.walk(4, 40, (-0.42, -0.01, 0), (-0.29 + 0.0, -0.01, 0))
cl.look(40, 1, 0)
cl.arm(42, "R", 0)
cl.arm(48, "R", 75)
cl.tilt(44, 0)
cl.tilt(54, 11)
cl.walk(F_PUSH0, F_PUSH1, (-0.29, -0.01, 0), (-0.29 + (P1 - P0), -0.01, 0), step=6)
cl.tilt(F_PUSH1 + 6, 0)
cl.arm(F_PUSH1 + 6, "R", 0)
cl.look(F_PUSH1 + 8, 1, 1)
cl.surprise(F_PUSH1 + 20)
cl.say(F_PUSH1 + 20, "whoa!", 30)

tgt = sc.target_empty("T", (-0.06, 0, 0.05))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = par
for f, loc, t in ((1, (-0.12, -0.78, 0.19), (-0.07, 0, 0.045)), (F_PUSH0, (-0.08, -0.74, 0.17), (-0.04, 0, 0.045)),
                  (N, (0.02, -0.66, 0.15), (0.0, 0, 0.045))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V06")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V06_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
