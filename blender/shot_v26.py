"""V26 — goodbye: the neon title sign glows over the drifting smoke; Clawd waves 'bye!', hops off its tower and
patters out of frame; the sign stutters and switches off; in the dark, Clawd peeks back in (post-credit). Cycles.

blender.exe -b --factory-startup --python blender/shot_v26.py -- <test|render> <first> <last> [samples]
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
N = 6 * 48 + 24
OFF = 250                                  # the sign switches off (bar 141.2)

scn = sc.reset_scene()
scn.frame_start, scn.frame_end = 1, N
S = si.build(scn, frame_offset=120, samples=SAMPLES, key_left=True)

FONT = str(sc.ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
letters = st.neon_text(["SEEING THE", "INVISIBLE"], FONT, 0.032, (0.0, 0.16, 0.175), st.MAGENTA, strength=55.0,
                       name="Title")
# the sign is on from the start and stutters off at OFF; the studio neon goes with it
for i, ob in enumerate(letters):
    st.neon_switch(ob, 1, flicker=((0, 1.0),), f_off=OFF + 3 * i)
for nm in ("mag", "cya", "vio"):
    st.neon_switch(S["tubes"][nm], 1, flicker=((0, 1.0),), f_off=OFF + 8,
                   extra_lights=[S["lights"][k] for k in {"mag": ("rim_m",), "cya": ("rim_c", "top"), "vio": ()}[nm]])

cl = clawd.Clawd("Clawd", unit=vp.UNIT, location=(vp.XL, vp.Y, vp.BLOCK_TOP), rotation_z=math.radians(-8))
cl.look(1, 0, 0)
cl.wave(16, 84, "L", period=8)
cl.say(22, "bye!", 34)
cl.blink(90)
cl.hop(100, 114, (vp.XL, vp.Y, vp.BLOCK_TOP), (vp.XL + 0.06, vp.Y - 0.04, vp.TABLE), height=0.02)
cl.turn(118, math.radians(-8))
cl.turn(124, math.radians(-80))                 # turns to walk off to the right
cl.walk(126, 210, (vp.XL + 0.06, vp.Y - 0.04, vp.TABLE), (0.42, vp.Y - 0.04, vp.TABLE), step=3)
# post-credit: in the dark, it peeks back in from the right edge
cl.place(268, (0.42, vp.Y - 0.04, vp.TABLE))
cl.turn(268, math.radians(80))
cl.walk(270, 284, (0.42, vp.Y - 0.04, vp.TABLE), (0.30, vp.Y - 0.04, vp.TABLE), step=3)
cl.turn(286, math.radians(-10))
cl.look(288, -1, 0)
cl.blink(296)
cl.say(290, "...", 20)
cl.cues.append((288, "blip"))
peek = bpy.data.lights.new("PeekLight", "SPOT")
peek.energy = 0.0
peek.color = (1.0, 0.75, 0.6)
peek.spot_size = math.radians(30)
pk = bpy.data.objects.new("PeekLight", peek)
pk.location = (0.30, -0.35, 0.10)
sc.link(pk)
import scene_common as _sc  # noqa: E402
_sc.look_at(pk, (0.30, vp.Y, vp.TABLE + 0.02))
for f, e in ((1, 0.0), (OFF + 10, 0.0), (OFF + 20, 2.5), (N, 2.5)):
    peek.energy = e
    peek.keyframe_insert("energy", frame=f)

cam, tgt, key = si.camera(lens=40.0, dof=8.0)
key(1, (0.02, -0.74, 0.02), (0.02, 0.1, 0.06))
key(N, (0.04, -0.70, 0.01), (0.04, 0.1, 0.055))
for o in (cam, tgt):
    sc.smooth_keys(o)
cam.data.dof.focus_object = None
cam.data.dof.focus_distance = 0.72

si.render(scn, MODE, "V26", FIRST, LAST, clawd_obj=cl, n=N)
if MODE == "test":
    pass
