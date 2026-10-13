"""Look-dev: Clawd character sheet in the neon studio.
blender.exe -b --factory-startup --python blender/lookdev_clawd.py -- <engine: eevee|cycles> [style: glossy|acrylic] [samples]
-> cache/lookdev_v2/clawd_<engine>_<style>.png
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio  # noqa: E402

A = sc.args()
ENGINE = A[0] if A else "eevee"
STYLE = A[1] if len(A) > 1 else "glossy"
SAMPLES = int(A[2]) if len(A) > 2 else 128

scn = sc.reset_scene()
studio.setup_render(scn, ENGINE, SAMPLES)
studio.neon_studio(scn, haze=0.06)

U = 0.004
c1 = clawd.Clawd("C1", unit=U, location=(-0.115, 0.02, 0), rotation_z=math.radians(28), style=STYLE)
c2 = clawd.Clawd("C2", unit=U, location=(0.0, -0.01, 0), style=STYLE)
c3 = clawd.Clawd("C3", unit=U, location=(0.115, 0.02, 0.035), rotation_z=math.radians(-25), style=STYLE)
# poses at frame 10: C1 looks right, C2 waves, C3 mid-jump stretched with arms up
c1.look(10, 1)
c2.arm(10, "R", 60)
c2.tilt(10, -6)
c3.squash_to(10, 1.15)
c3.arm(10, "L", 40)
c3.arm(10, "R", 40)
c3.surprise(8)

cam = sc.add_camera(lens=50.0, dof=5.6, clip=(0.01, 50))
tgt = sc.target_empty("T", (0, 0.0, 0.022))
cam.location = (0.0, -0.62, 0.12)
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt
scn.frame_set(10)
out = sc.ROOT / "cache" / "lookdev_v2"
out.mkdir(parents=True, exist_ok=True)
scn.render.filepath = str(out / f"clawd_{ENGINE}_{STYLE}.png")
bpy.ops.render.render(write_still=True)
