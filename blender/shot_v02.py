"""V02 — Clawd leaps across the smoke plume (slow, floaty jump); its body cuts the plume and sheds swirls
(cache/v02_vdb, simulated with Clawd as a moving obstacle: blender/sim_v02.py + v02_path.py).

blender.exe -b --factory-startup --python blender/shot_v02.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import set_incense as si  # noqa: E402
import v02_path as vp  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 78
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24

scn = sc.reset_scene()
scn.frame_start, scn.frame_end = 1, N
S = si.build(scn, smoke_dir=sc.ROOT / "cache" / "v02_vdb", prefix="v02", frame_offset=-1, n_files=216,
             samples=SAMPLES)

cl = clawd.Clawd("Clawd", unit=vp.UNIT, location=vp.feet(1), rotation_z=math.radians(-12))
# before: eyes on the plume, a crouch-wiggle, then the leap (root follows the shared path frame by frame)
cl.look(1, -1, 1)
cl.blink(20)
cl.look(34, -1, 0)
cl.squash_to(40, 1.0)
cl.squash_to(46, 0.9)
cl.squash_to(50, 1.0)
cl.squash_to(54, 0.88)
cl.squash_to(vp.T_OFF - 1, 0.74)                       # crouch
cl.squash_to(vp.T_OFF + 3, 1.16)                       # launch
cl.squash_to(vp.T_OFF + 18, 1.0)
cl.squash_to(vp.T_LAND - 2, 1.1)
cl.squash_to(vp.T_LAND, 0.74)                          # land
cl.squash_to(vp.T_LAND + 4, 1.07)
cl.squash_to(vp.T_LAND + 9, 1.0)
cl.eyes_scale(vp.T_OFF + 2, (1, 1, 1.4))               # wide-eyed in the air
cl.eyes_scale(vp.T_LAND + 2, (1, 1, 1))
for side, a in (("L", 1), ("R", -1)):
    cl.arm(vp.T_OFF, side, 0)
    cl.arm(vp.T_OFF + 8, side, 60)
    cl.arm(vp.T_LAND - 4, side, 40)
    cl.arm(vp.T_LAND + 6, side, 0)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
for f in range(vp.T_OFF - 1, vp.T_LAND + 2):
    cl.root.location = vp.feet(f)
    cl.root.keyframe_insert("location", frame=f)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
cl.cues.append((vp.T_OFF, "hop"))
cl.cues.append((vp.T_LAND, "land"))
# after: turns round to look back at the swirls it made
cl.turn(vp.T_LAND + 6, math.radians(-12))
cl.turn(vp.T_LAND + 16, math.radians(28))
cl.look(vp.T_LAND + 14, 1, 0)
cl.surprise(vp.T_LAND + 16)
cl.say(vp.T_LAND + 16, "!?", 34)
cl.look(150, 1, 1)
cl.tilt(150, 0)
cl.tilt(166, -6)
cl.blink(184)
cl.breathe(120, N, 24, 0.025)

cam, tgt, key = si.camera(lens=50.0, dof=4.5, focus=cl.root)
key(1, (0.045, -0.44, -0.02), (0.035, 0.0, 0.0))
key(vp.T_OFF, (0.03, -0.43, -0.018), (0.02, 0.0, 0.002))
key(vp.T_LAND + 10, (-0.005, -0.42, -0.015), (-0.01, 0.0, 0.01))
key(N, (-0.01, -0.46, -0.005), (-0.005, 0.0, 0.035))
for o in (cam, tgt):
    sc.smooth_keys(o)

si.render(scn, MODE, "V02", FIRST, LAST, clawd_obj=cl, n=N)
if MODE == "test":
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "v02.blend"))
