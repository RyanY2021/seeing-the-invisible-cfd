"""V25 — close: back in the neon studio, Clawd on its tower watches the incense; a glowing scan line sweeps across the
plume and the smoke turns into its simulated twin (coloured by vorticity) — Clawd can see the invisible. Holds for
the closing line, then sweeps back to real smoke. Cycles (incense VDB + vorticity grid).

blender.exe -b --factory-startup --python blender/shot_v25.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import props  # noqa: E402
import scene_common as sc  # noqa: E402
import set_incense as si  # noqa: E402
import v02_path as vp  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 200
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 48
N = 6 * 48 + 24
WIPE = [(1, -0.11), (46, -0.11), (166, 0.11), (252, 0.11), (300, -0.11), (N, -0.11)]

scn = sc.reset_scene()
scn.frame_start, scn.frame_end = 1, N
S = si.build(scn, frame_offset=199, samples=SAMPLES, key_left=True)          # files 199.. (developed plume)
props.smoke_twin_wipe(S["mat"], WIPE)

cl = clawd.Clawd("Clawd", unit=vp.UNIT, location=(vp.XL, vp.Y, vp.BLOCK_TOP), rotation_z=math.radians(20))
cl.look(1, 1, 1)
cl.breathe(1, 60, 24, 0.03)
cl.surprise(70)
cl.say(74, "I can see it!", 44)
cl.hop(96, 108, (vp.XL, vp.Y, vp.BLOCK_TOP), (vp.XL, vp.Y, vp.BLOCK_TOP), height=0.02)
cl.look(130, 1, 1)
cl.turn(176, math.radians(20))
cl.turn(188, math.radians(-5))                     # turns to us ...
cl.look(188, 0, 0)
cl.squash_to(196, 1.0)
cl.squash_to(200, 0.88)                            # ... a little nod
cl.squash_to(206, 1.0)
cl.turn(250, math.radians(25))
cl.look(250, 1, 1)
cl.breathe(210, N, 24, 0.03)

cam, tgt, key = si.camera(lens=45.0, dof=8.0, focus=None)
cam.data.dof.focus_distance = 0.6
key(1, (-0.02, -0.62, 0.02), (0.0, 0.0, 0.07))
key(N, (0.02, -0.56, 0.03), (0.005, 0.0, 0.075))
for o in (cam, tgt):
    sc.smooth_keys(o)

si.render(scn, MODE, "V25", FIRST, LAST, clawd_obj=cl, n=N)
