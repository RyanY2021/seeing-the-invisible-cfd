"""Look-dev: the cell world — black car wrapped in a half octree of acrylic cells, synthwave grid + sun, Clawd.
blender.exe -b --factory-startup --python blender/lookdev_cellworld.py -- [engine] [samples]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import car_common as cc  # noqa: E402
import cellworld as cw  # noqa: E402
import clawd  # noqa: E402
import scene_common as sc  # noqa: E402
import studio as st  # noqa: E402

A = sc.args()
ENGINE = A[0] if A else "eevee"
SAMPLES = int(A[1]) if len(A) > 1 else 64

scn = sc.reset_scene()
st.setup_render(scn, ENGINE, SAMPLES)
cw.synth_sky(scn, strength=0.6)
cw.synth_sun(loc=(150, 200, 30), radius=48)
cw.synth_floor(spacing=0.8, strength=4.0, fade=45.0)

d = np.load(sc.ROOT / "cache" / "v2" / "octree_car.npz")
cells = d["cells"]
ob = cw.cells_mesh(cells)
ob.data.materials.append(cw.acrylic_cell_material(edge_strength=2.6, face_alpha=0.018))

body = cc.body_material(color=(0.008, 0.008, 0.01), rough=0.18, coat=1.0)
car, _, _ = cc.build_car(body_mat=body)

NO_CLAWD = len(A) > 2 and A[2] == "noclawd"
if not NO_CLAWD:
    c = clawd.Clawd("Clawd", unit=0.07, location=(-1.6, -2.2, 0.0), rotation_z=math.radians(-30))
    c.look(10, 1, 1)
    c.arm(10, "R", 50)

st.strip_softbox((2.2, 0.0, 4.5), size=(6.0, 0.25), energy=900.0, target=(2.2, 0, 0), name="TopStrip", visible=False)
sc.add_light("RimMag", "AREA", (-4, 3, 2.5), 1500.0, color=st.MAGENTA, size=2.0, target=(2, 0, 0.6))
rc = sc.add_light("RimCyan", "AREA", (9, -2, 2.0), 1500.0, color=st.CYAN, size=2.0, target=(2, 0, 0.6))
rc.visible_glossy = False
sc.add_light("ClawdKey", "AREA", (-3.5, -5.0, 2.5), 250.0, color=(1.0, 0.8, 0.7), size=1.5, target=(-1.6, -2.2, 0.4))

cam = sc.add_camera(lens=32.0, dof=None, clip=(0.05, 2000))
cam.location = (-5.2, -9.5, 2.3)
tgt = sc.target_empty("T", (2.4, 0.6, 1.0))
sc.track_to(cam, tgt)
import time
out = sc.ROOT / "cache" / "lookdev_v2"
for f in (10, 11):
    t0 = time.time()
    scn.frame_set(f)
    scn.render.filepath = str(out / f"cellworld_{ENGINE}{'_noclawd' if NO_CLAWD else ''}.exr")
    bpy.ops.render.render(write_still=True)
    print(f"RENDER TIME frame {f}: {time.time() - t0:.1f}s", flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "lookdev_cellworld.blend"))
