import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bpy
import scene_common as sc
import car_common as cc
scn = sc.reset_scene()
sc.setup_cycles(scn, samples=32, res=(960, 540))
sc.world_color(scn, (0.05, 0.05, 0.055), 1.0)
cc.build_car()
bpy.ops.mesh.primitive_plane_add(size=40)
fl = bpy.context.active_object
m, nt, p = sc.principled("Floor", base=(0.08, 0.08, 0.085), rough=0.35)
fl.data.materials.append(m)
sc.add_light("Key", "AREA", (2.2, -3, 5), 350, size=4, target=(2.2, 0, 0.5))
sc.add_light("Rim", "AREA", (6, 4, 3), 250, size=3, target=(2.2, 0, 0.5))
cam = sc.add_camera(lens=50)
out = sc.ROOT / "cache" / "lookdev"
for i, (loc, tgt) in enumerate([((-2.8, -5.2, 1.6), (2.0, 0, 0.6)), ((2.25, -8.5, 0.7), (2.25, 0, 0.65)), ((7.0, 3.8, 2.2), (2.3, 0, 0.6))]):
    cam.location = loc
    sc.look_at(cam, tgt)
    scn.render.filepath = str(out / f"car_{i}.png")
    bpy.ops.render.render(write_still=True)
