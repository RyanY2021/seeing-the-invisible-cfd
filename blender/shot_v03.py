"""V03 — title: the camera pulls back from Clawd; behind the drifting smoke a neon sign SEEING THE INVISIBLE
buzzes on letter by letter (on the beat); Clawd turns to look, then waves at us.

blender.exe -b --factory-startup --python blender/shot_v03.py -- <test|render> <first> <last> [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import set_incense as si  # noqa: E402
import studio as st  # noqa: E402
import v02_path as vp  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 120
LAST = int(A[2]) if len(A) > 2 else FIRST
SAMPLES = int(A[3]) if len(A) > 3 else 64
N = 4 * 48 + 24

scn = sc.reset_scene()
scn.frame_start, scn.frame_end = 1, N
S = si.build(scn, frame_offset=339, samples=SAMPLES)     # the original plume, later part (after V01's files)

FONT = str(sc.ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
letters = st.neon_text(["SEEING THE", "INVISIBLE"], FONT, 0.032, (0.0, 0.16, 0.175), st.MAGENTA, strength=55.0,
                       name="Title")
# words buzz on on the beat: SEEING (beat 1), THE (beat 2), INVISIBLE stutters on beat 3 and catches on beat 4
st.neon_switch(letters[0], 4, flicker=((0, 1.0), (1, 0.0), (2, 0.8), (4, 0.2), (5, 1.0)))
st.neon_switch(letters[1], 16, flicker=((0, 1.0), (1, 0.0), (2, 0.8), (4, 0.2), (5, 1.0)))
st.neon_switch(letters[2], 28, flicker=((0, 0.7), (2, 0.0), (5, 0.5), (7, 0.0), (10, 1.0), (11, 0.3), (12, 1.0)))

cl = clawd.Clawd("Clawd", unit=vp.UNIT, location=(vp.XL, vp.Y, vp.BLOCK_TOP), rotation_z=math.radians(28))
cl.look(1, 1, 1)
cl.blink(14)
cl.look(30, 0, 1)
cl.turn(34, math.radians(28))
cl.turn(52, math.radians(160))          # turns round to face the sign as it lights up
cl.breathe(60, 140, 24, 0.03)
cl.turn(140, math.radians(160))
cl.turn(156, math.radians(-8))          # ... and back to us
cl.look(156, 0, 0)
cl.surprise(160)
cl.wave(166, 204, "L", period=8)
cl.say(168, "hi!", 30)

cam, tgt, key = si.camera(lens=40.0, dof=8.0)
key(1, (-0.03, -0.40, -0.015), (-0.04, 0.0, 0.01))
key(70, (-0.02, -0.62, 0.01), (-0.015, 0.1, 0.07))
key(N, (-0.01, -0.70, 0.02), (-0.01, 0.12, 0.085))
for o in (cam, tgt):
    sc.smooth_keys(o)
cam.data.dof.focus_object = None
cam.data.dof.focus_distance = 0.72

si.render(scn, MODE, "V03", FIRST, LAST, clawd_obj=cl, n=N)
if MODE == "test":
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "v03.blend"))
