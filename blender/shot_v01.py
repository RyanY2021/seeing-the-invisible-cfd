"""V01 — prologue: dark table, ember glow; neon flickers on; incense smoke rises; Clawd hops in and looks up.

blender.exe -b --factory-startup --python blender/shot_v01.py -- <mode> <first> <last> [samples]
  mode: test  -> cache/lookdev_v2/V01_####.exr (+ graded png by tools)   |  render -> renders/V01/####.exr
Shot frames 1..300 (bars 0-6 = 288 frames + handles). Writes renders/V01/clawd_track.json for the compositor.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import props  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402
import v02_path as vp  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 150
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 96
N = 312               # bars 0-6 (288 frames) + 24 handle
TABLE = -0.10

scn = sc.reset_scene()
st.setup_render(scn, "cycles", SAMPLES)
scn.cycles.volume_step_rate = 1.0
scn.cycles.volume_max_steps = 1024
scn.frame_start, scn.frame_end = 1, N
st.neon_studio(scn, haze=0.0, z0=TABLE, tubes=None, lights=False, floor_rough=0.15)   # haze faked in grade

# ---------------------------------------------------------------- neon tubes (background) — switched on in turn
mag = st.neon_tube([(-0.30, 0.55, TABLE), (-0.30, 0.55, 0.26)], st.MAGENTA, 34.0, name="NeonMag")
cya = st.neon_tube([(0.06, 0.62, 0.17), (0.40, 0.62, 0.17)], st.CYAN, 30.0, name="NeonCyan")
vio = st.neon_tube([(-0.18, 0.75, TABLE + 0.035), (0.30, 0.75, TABLE + 0.035)], st.VIOLET, 22.0, name="NeonVio")

# smoke rim lights belong to the tubes (they switch on with them)
rim_m = sc.add_light("RimMag", "SPOT", (-0.42, 0.42, 0.10), 45.0, color=st.MAGENTA, size=0.04, target=(0, 0, 0.09),
                     spot_size=math.radians(40), blend=0.6)
rim_c = sc.add_light("RimCyan", "SPOT", (0.44, 0.40, 0.16), 40.0, color=st.CYAN, size=0.04, target=(0, 0, 0.12),
                     spot_size=math.radians(40), blend=0.6)
top = sc.add_light("Top", "SPOT", (0.04, 0.22, 0.75), 5.0, color=(0.9, 0.85, 1.0), size=0.06, target=(0, 0, 0.2),
                   spot_size=math.radians(35), blend=0.7)
key = st.strip_softbox((0.18, -0.10, 0.12), size=(0.35, 0.04), energy=1.2, color=(1.0, 0.80, 0.70),
                       target=(0.06, 0, TABLE + 0.02), name="ClawdKey", visible=False)
st.neon_switch(mag, 22, extra_lights=[rim_m])
st.neon_switch(cya, 60, extra_lights=[rim_c, top])
st.neon_switch(vio, 84, extra_lights=[key])

# ---------------------------------------------------------------- incense + smoke
props.incense_stick(base_z=TABLE)
smoke, vol, _ = props.incense_smoke(dens=150.0, fall=1.5, color=(0.9, 0.9, 0.95), anisotropy=0.6, frame_offset=40)

# ---------------------------------------------------------------- acrylic block stacks flanking the incense
for side, x, col in (("R", vp.XR, st.CYAN), ("L", vp.XL, st.MAGENTA)):
    props.block_stack(x, TABLE, n=vp.N_BLOCKS, h=vp.BLOCK_H, edge_color=col, name=f"Stack{side}")
bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
for m in bpy.data.materials:
    if m.name.startswith("Stack") and "EdgeGain" in m.node_tree.nodes:
        g = m.node_tree.nodes["EdgeGain"].inputs[1]
        full = g.default_value
        for fr, k in ((1, 0.0), (83, 0.0), (84, 1.0), (86, 0.2), (88, 1.0)):
            g.default_value = full * k
            g.keyframe_insert("default_value", frame=fr)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"

# ---------------------------------------------------------------- Clawd: hops in, climbs the right stack, eyes the smoke
U = vp.UNIT
Y = vp.Y
cl = clawd.Clawd("Clawd", unit=U, location=(0.27, Y, TABLE), rotation_z=math.radians(-15))
cl.hop(100, 112, (0.27, Y, TABLE), (0.21, Y, TABLE), height=0.024)
cl.hop(118, 130, (0.21, Y, TABLE), (0.15, Y, TABLE), height=0.022)
cl.look(140, -1, 0)                        # looks at the tower ...
cl.look(152, -1, 1)
cl.blink(160)
cl.hop(176, 196, (0.15, Y, TABLE), (vp.XR, Y, vp.BLOCK_TOP), height=0.0625, anticip=6)   # ... and jumps up
cl.turn(196, math.radians(-15))
cl.turn(208, math.radians(-28))
cl.look(206, -1, 1)                        # up at the plume
cl.tilt(206, 0)
cl.tilt(222, 7)
cl.blink(244)
cl.tilt(262, 0)
for k, fr in enumerate((270, 276, 282, 288)):   # little determined wiggle: getting ready to leap
    cl.squash_to(fr, 0.9 if k % 2 == 0 else 1.0)
cl.squash_to(300, 0.86)
cl.breathe(200, 262, 24, 0.025)

# ---------------------------------------------------------------- camera: slow push-in, tilting up with the smoke
cam = sc.add_camera(lens=50.0, dof=5.6, clip=(0.02, 30))
tgt = sc.target_empty("CamTarget", (0.03, 0, -0.02))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = cl.root


def cam_key(f, loc, t):
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    tgt.location = t
    tgt.keyframe_insert("location", frame=f)


# opens low on the ember and Clawd's arrival, then tilts up the plume as the smoke turns to chaos
cam_key(1, (0.04, -0.66, -0.07), (0.05, 0.0, -0.05))
cam_key(170, (0.04, -0.64, -0.068), (0.05, 0.0, -0.04))
cam_key(N, (0.02, -0.68, -0.04), (0.02, 0.0, 0.06))
for o in (cam, tgt):
    sc.smooth_keys(o)

if MODE == "test":
    out = sc.ROOT / "cache" / "lookdev_v2"
    out.mkdir(parents=True, exist_ok=True)
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 3 or 1)):
        scn.frame_set(f)
        scn.render.filepath = str(out / f"V01_{f:04d}.exr")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "v01.blend"))
else:
    outdir = sc.ROOT / "renders" / "V01"
    outdir.mkdir(parents=True, exist_ok=True)
    cl.export_track(scn, outdir / "clawd_track.json", 1, N)
    for f in range(FIRST, LAST + 1):
        p = outdir / f"{f:04d}.exr"
        if p.exists():
            continue
        scn.frame_set(f)
        scn.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
