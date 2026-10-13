"""V14 — STEP 2, balance the books: one hero cell in a lattice of faint cells; flow streaks pass through it, its
left face pulses cyan for every bit that comes IN and its right face magenta for every bit that goes OUT; Clawd
sits on top keeping score. Then "each cell only talks to its neighbours": a light ripple runs from the hero
cell outward, neighbour by neighbour, as the camera pulls back. Eevee.

blender.exe -b --factory-startup --python blender/shot_v14.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import cellworld as cw  # noqa: E402
import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import streaks as sk  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 120
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 6 * 48 + 24
C = 1.2                                          # cell size (m)
RIPPLE = 212                                     # bar 64.4
HERO = np.array([0.0, 0.0, 2.5 * C])

scn = sc.reset_scene()
st.setup_render(scn, "eevee", SAMPLES)
scn.frame_start, scn.frame_end = 1, N
cw.build_world(scn, sun=(-120, 260, 25), sun_r=40, sky_strength=0.35, grid_strength=3.0)
sc.add_light("RimMag", "AREA", (-6, 5, 5), 2500.0, color=st.MAGENTA, size=3.0, target=(0, 0, 1.5))
rc = sc.add_light("RimCyan", "AREA", (7, -3, 4), 2500.0, color=st.CYAN, size=3.0, target=(0, 0, 1.5))
rc.visible_glossy = False
sc.add_light("ClawdKey", "AREA", (-2.5, -5.0, 5.0), 300.0, color=(1.0, 0.8, 0.7), size=2.0, target=(0, 0, 2.6))

# ---------------------------------------------------------------- lattice of cells, grouped in shells of equal
# neighbour-distance from the hero cell (so the ripple can travel outward shell by shell)
shells = {}
for i in range(-4, 5):                          # a wall of cells facing the camera, hero = top centre
    for k in range(0, 3):
        dd = abs(i) + abs(k - 2)
        shells.setdefault(dd, []).append((i * C - C / 2, -C / 2, k * C, C, 0 if dd else 5))
mats = {}
for dd, cl_ in shells.items():
    ob = cw.cells_mesh(np.array(cl_, np.float32), name=f"Shell{dd}", shrink=0.015)
    m = cw.acrylic_cell_material(f"ShellMat{dd}", edge_w=0.02, edge_strength=2.4 if dd == 0 else 1.0,
                                 face_alpha=0.05 if dd == 0 else 0.012,
                                 coarse=st.CYAN if dd == 0 else st.VIOLET, fine=st.CYAN)
    ob.data.materials.append(m)
    mats[dd] = m
    base = 1.0 if dd == 0 else 0.55
    cw.key_vis(m, 1, base)
    t0 = RIPPLE + 6 * dd                          # the ripple: each shell flashes after the one inside it
    cw.key_vis(m, t0 - 1, base)
    cw.key_vis(m, t0 + 2, 3.5)
    cw.key_vis(m, t0 + 12, base)

# ---------------------------------------------------------------- flow through the lattice
U = 0.9


def vel(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return np.stack([U * (1 + 0.15 * np.sin(z * 1.3 + 0.5)), 0.02 * U * np.sin(x * 0.9 + z), 0.12 * U * np.cos(x * 0.7 + y)], -1)


def seed(k, rng):
    return np.stack([rng.uniform(-6.5, -5.5, k), rng.uniform(-0.45, 0.45, k), rng.uniform(0.1, 3.5, k)], -1)


seed.outside = lambda p: p[:, 0] > 5.8
rng = np.random.default_rng(4)
npart = 420
heads, tails = sk.trace(vel, lambda k, r: seed(k, r) + np.stack([r.uniform(0, 10, k), np.zeros(k), np.zeros(k)], -1)
                        if k == npart else seed(k, r), npart, N + 2, tail_frames=10, rng=rng)
cols = np.array([st.CYAN, (0.8, 0.9, 1.0), st.VIOLET], np.float32)[rng.integers(0, 3, npart)]
cam = sc.add_camera(lens=35.0, dof=None, clip=(0.05, 2000))
S = sk.Streaks("Flow", heads, tails, sk.streak_material(strength=6.0), width=0.03, colors=cols, cam=cam)
sk.register()

# ---------------------------------------------------------------- IN / OUT faces of the hero cell pulse per crossing
def face(name, x, color):
    bpy.ops.mesh.primitive_plane_add(size=C * 0.97, location=(x, 0, HERO[2]), rotation=(0, math.pi / 2, 0))
    ob = bpy.context.active_object
    ob.name = name
    m = sc.emission_mat(f"{name}Mat", color, 0.0)
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    em = nt.nodes["Emission"]
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    out = nt.nodes["Material Output"]
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    return em.inputs["Strength"]


fin = face("FaceIn", -C / 2, st.CYAN)
fout = face("FaceOut", C / 2, st.MAGENTA)
inside = lambda p: (np.abs(p[:, 1]) < C / 2) & (np.abs(p[:, 2] - HERO[2]) < C / 2)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
glow_in = glow_out = 0.0
for f in range(1, N + 1):
    a, b = heads[f - 1], heads[f]
    n_in = int((inside(b) & (a[:, 0] < -C / 2) & (b[:, 0] >= -C / 2)).sum())
    n_out = int((inside(b) & (a[:, 0] < C / 2) & (b[:, 0] >= C / 2)).sum())
    glow_in = glow_in * 0.6 + 0.9 * n_in
    glow_out = glow_out * 0.6 + 0.9 * n_out
    fin.default_value = min(glow_in, 3.0) * 0.5
    fin.keyframe_insert("default_value", frame=f)
    fout.default_value = min(glow_out, 3.0) * 0.5
    fout.keyframe_insert("default_value", frame=f)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"

# ---------------------------------------------------------------- Clawd on top of the hero cell
Uc = 0.06
top = HERO[2] + C / 2
cl = clawd.Clawd("Clawd", unit=Uc, location=(0.0, 0.05, top), rotation_z=math.radians(-12))
for k, f in enumerate(range(10, RIPPLE, 22)):    # looks left (in) and right (out), keeping score
    cl.look(f, -1 if k % 2 == 0 else 1, -1)
    cl.squash_to(f, 0.94)
    cl.squash_to(f + 5, 1.0)
cl.look(RIPPLE - 4, 0, 0)
cl.surprise(RIPPLE + 2)
cl.cues.append((RIPPLE, "ripple"))
cl.look(RIPPLE + 20, 1, 1)
cl.breathe(RIPPLE + 20, N, 24, 0.03)

tgt = sc.target_empty("T", tuple(HERO))
sc.track_to(cam, tgt)
for f, loc, t in ((1, (-1.6, -5.0, 3.6), (0, 0, HERO[2] + 0.3)), (RIPPLE - 10, (-0.8, -5.4, 3.4), (0, 0, HERO[2] + 0.3)),
                  (N, (-1.2, -11.0, 3.2), (0, 0, 1.6))):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

out = sc.ROOT / ("cache/lookdev_v2" if MODE == "test" else "renders/V14")
out.mkdir(parents=True, exist_ok=True)
if MODE != "test":
    cl.export_track(scn, out / "clawd_track.json", 1, N)
for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3) if MODE == "test" else 1):
    pth = out / (f"V14_{f:04d}.exr" if MODE == "test" else f"{f:04d}.exr")
    if pth.exists() and MODE != "test":
        continue
    scn.frame_set(f)
    scn.render.filepath = str(pth)
    bpy.ops.render.render(write_still=True)
