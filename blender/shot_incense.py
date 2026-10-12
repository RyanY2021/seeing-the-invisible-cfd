"""S01/S02 (and S15) incense smoke hero shot — photoreal Cycles volume render of the LBM plume.

blender.exe -b --factory-startup --python blender/shot_incense.py -- <mode> <first> <last> [pct] [samples]
  mode: S01 (opening + title, scene frames 1..552), S15 (closing, real look), S15cfd (closing, CFD-coloured twin)
         test  (single-frame look-dev render to cache/lookdev)
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import scene_common as sc  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
PCT = int(A[3]) if len(A) > 3 else 100
SAMPLES = int(A[4]) if len(A) > 4 else 128
VDB_FORCE = int(A[5]) if len(A) > 5 else -1  # test: show this vdb index regardless of frame
DENS = float(A[6]) if len(A) > 6 else 170.0
FALL = float(A[7]) if len(A) > 7 else 1.6
LIGHT = float(A[8]) if len(A) > 8 else 1.35

VDB_DIR = sc.ROOT / "cache" / "incense_vdb"
NVDB = len(list(VDB_DIR.glob("incense_*.vdb")))

scn = sc.reset_scene()
sc.setup_cycles(scn, samples=SAMPLES, bounces=(4, 1, 2), adaptive=0.02)
scn.render.resolution_percentage = PCT
for attr, val in (("volume_step_rate", 1.0), ("volume_preview_step_rate", 1.0), ("volume_max_steps", 2048)):
    if hasattr(scn.cycles, attr):
        setattr(scn.cycles, attr, val)
sc.world_color(scn, (0.0008, 0.0009, 0.0012), 1.0)

# ---------------------------------------------------------------- smoke volume
vol = bpy.data.volumes.new("Smoke")
vol.filepath = str(VDB_DIR / "incense_0000.vdb")
vol.is_sequence = True
vol.frame_duration = 560  # total frames written by sim_incense.py
vol.frame_start = 1
vol.frame_offset = -1  # scene frame 1 -> file 0000
vol.sequence_mode = "CLIP"
smoke = bpy.data.objects.new("Smoke", vol)
sc.link(smoke)
VOX = 0.0005  # metres per fine voxel
smoke.scale = (VOX, VOX, VOX)
smoke.location = (-192 * VOX, -192 * VOX, 0.0)

CFD = MODE == "S15cfd"
m, nt, out = sc.new_material("SmokeMat")
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "density"
attr.attribute_type = "GEOMETRY"
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = DENS if not CFD else DENS * 0.85
# dilution with height: the rising plume entrains air, so visible density falls off ~1/z
geo = nt.nodes.new("ShaderNodeNewGeometry")
sz = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(geo.outputs["Position"], sz.inputs[0])
hz = nt.nodes.new("ShaderNodeMath")
hz.operation = "ADD"
hz.inputs[1].default_value = 0.025
nt.links.new(sz.outputs["Z"], hz.inputs[0])
hd = nt.nodes.new("ShaderNodeMath")
hd.operation = "DIVIDE"
hd.inputs[0].default_value = 0.035
nt.links.new(hz.outputs[0], hd.inputs[1])
hp = nt.nodes.new("ShaderNodeMath")
hp.operation = "POWER"
hp.inputs[1].default_value = FALL
nt.links.new(hd.outputs[0], hp.inputs[0])
hc = nt.nodes.new("ShaderNodeClamp")
hc.inputs["Min"].default_value = 0.05
hc.inputs["Max"].default_value = 1.0
nt.links.new(hp.outputs[0], hc.inputs["Value"])
dz = nt.nodes.new("ShaderNodeMath")
dz.operation = "MULTIPLY"
nt.links.new(attr.outputs["Fac"], dz.inputs[0])
nt.links.new(hc.outputs[0], dz.inputs[1])
nt.links.new(dz.outputs[0], mul.inputs[0])
pv = nt.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Anisotropy"].default_value = 0.55
nt.links.new(mul.outputs[0], pv.inputs["Density"])
if not CFD:
    pv.inputs["Color"].default_value = (0.82, 0.85, 0.9, 1)
else:
    va = nt.nodes.new("ShaderNodeAttribute")
    va.attribute_name = "vorticity"
    va.attribute_type = "GEOMETRY"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.012
    nt.links.new(va.outputs["Fac"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.02, 0.10, 0.55, 1)
    els[1].position, els[1].color = 1.0, (1.0, 0.95, 0.75, 1)
    for pos, col in ((0.25, (0.0, 0.55, 0.95, 1)), (0.5, (0.15, 0.9, 0.6, 1)), (0.75, (1.0, 0.55, 0.08, 1))):
        e = els.new(pos)
        e.color = col
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], pv.inputs["Color"])
    nt.links.new(ramp.outputs["Color"], pv.inputs["Emission Color"])
    em = nt.nodes.new("ShaderNodeMath")
    em.operation = "MULTIPLY"
    em.inputs[1].default_value = 6.0
    nt.links.new(attr.outputs["Fac"], em.inputs[0])
    nt.links.new(em.outputs[0], pv.inputs["Emission Strength"])
nt.links.new(pv.outputs[0], out.inputs["Volume"])
smoke.data.materials.append(m)

# ---------------------------------------------------------------- incense stick
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.00105, depth=0.27, location=(0, 0, 0.0108 - 0.135))
stick = bpy.context.active_object
stick.name = "Stick"
m, nt, out = sc.new_material("StickMat")
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Object"], sep.inputs[0])
noise = nt.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 900.0
noise.inputs["Detail"].default_value = 8.0
nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
p = nt.nodes.new("ShaderNodeBsdfPrincipled")
p.inputs["Roughness"].default_value = 0.85
# z (object space): top at +0.135. ash band at top 6 mm, glowing ember ring just below the ash tip
zr = nt.nodes.new("ShaderNodeMapRange")  # 0 at -0.135 .. 1 at top
zr.inputs["From Min"].default_value = 0.135 - 0.009
zr.inputs["From Max"].default_value = 0.135
nt.links.new(sep.outputs["Z"], zr.inputs["Value"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
els = ramp.color_ramp.elements
els[0].position, els[0].color = 0.0, (0.055, 0.022, 0.012, 1)  # incense paste, dark brown-red
els[1].position, els[1].color = 1.0, (0.32, 0.31, 0.30, 1)  # ash
e = els.new(0.45)
e.color = (0.05, 0.02, 0.01, 1)
e = els.new(0.62)
e.color = (0.25, 0.24, 0.23, 1)
nt.links.new(zr.outputs["Result"], ramp.inputs["Fac"])
mixn = nt.nodes.new("ShaderNodeMix")
mixn.data_type = "RGBA"
mixn.blend_type = "MULTIPLY"
mixn.inputs["Factor"].default_value = 0.35
nt.links.new(ramp.outputs["Color"], mixn.inputs["A"])
nt.links.new(noise.outputs["Color"], mixn.inputs["B"])
nt.links.new(mixn.outputs["Result"], p.inputs["Base Color"])
# ember emission: narrow band at the paste/ash boundary, modulated by noise (flickering via W)
band = nt.nodes.new("ShaderNodeMapRange")
band.interpolation_type = "SMOOTHSTEP"
band.inputs["From Min"].default_value = 0.135 - 0.0075
band.inputs["From Max"].default_value = 0.135 - 0.0035
nt.links.new(sep.outputs["Z"], band.inputs["Value"])
band2 = nt.nodes.new("ShaderNodeMapRange")
band2.interpolation_type = "SMOOTHSTEP"
band2.inputs["From Min"].default_value = 0.135 - 0.0005
band2.inputs["From Max"].default_value = 0.135 - 0.0035
nt.links.new(sep.outputs["Z"], band2.inputs["Value"])
bm = nt.nodes.new("ShaderNodeMath")
bm.operation = "MINIMUM"
nt.links.new(band.outputs["Result"], bm.inputs[0])
nt.links.new(band2.outputs["Result"], bm.inputs[1])
en = nt.nodes.new("ShaderNodeTexNoise")
en.noise_dimensions = "4D"
en.inputs["Scale"].default_value = 1500.0
en.inputs["Detail"].default_value = 4.0
nt.links.new(tc.outputs["Object"], en.inputs["Vector"])
drv = en.inputs["W"].driver_add("default_value")
drv.driver.expression = "frame/30"
em2 = nt.nodes.new("ShaderNodeMath")
em2.operation = "MULTIPLY"
nt.links.new(bm.outputs[0], em2.inputs[0])
nt.links.new(en.outputs["Fac"], em2.inputs[1])
em3 = nt.nodes.new("ShaderNodeMath")
em3.operation = "POWER"
em3.inputs[1].default_value = 1.6
nt.links.new(em2.outputs[0], em3.inputs[0])
em4 = nt.nodes.new("ShaderNodeMath")
em4.operation = "MULTIPLY"
em4.inputs[1].default_value = 45.0
nt.links.new(em3.outputs[0], em4.inputs[0])
bb = nt.nodes.new("ShaderNodeBlackbody")
bb.inputs["Temperature"].default_value = 1350.0
nt.links.new(bb.outputs[0], p.inputs["Emission Color"])
nt.links.new(em4.outputs[0], p.inputs["Emission Strength"])
nt.links.new(p.outputs[0], out.inputs["Surface"])
stick.data.materials.append(m)
bpy.ops.object.shade_smooth()

# ember light
sc.add_light("Ember", "POINT", (0, 0, 0.0072), 0.05, color=(1.0, 0.42, 0.12), size=0.0012)

# ---------------------------------------------------------------- lights (backlit smoke photography)
sc.add_light("RimL", "SPOT", (-0.42, 0.55, 0.42), 34.0 * LIGHT, color=(0.92, 0.95, 1.0), size=0.05, target=(0, 0, 0.22),
             spot_size=math.radians(42), blend=0.6)
sc.add_light("RimR", "SPOT", (0.45, 0.50, 0.18), 14.0 * LIGHT, color=(1.0, 0.88, 0.74), size=0.05, target=(0, 0, 0.12),
             spot_size=math.radians(40), blend=0.6)
sc.add_light("Top", "SPOT", (0.05, 0.25, 0.95), 12.0 * LIGHT, color=(0.85, 0.9, 1.0), size=0.08, target=(0, 0, 0.35),
             spot_size=math.radians(40), blend=0.7)
sc.add_light("Fill", "AREA", (-0.25, -0.6, 0.15), 0.25, color=(0.6, 0.7, 1.0), size=0.3, target=(0, 0, 0.12))

# background: faint warm bokeh far behind (a dim room)
bk = sc.emission_mat("Bokeh", (1.0, 0.62, 0.32), 0.24)
bk2 = sc.emission_mat("Bokeh2", (0.55, 0.65, 1.0), 0.12)
for i, (x, y, z, r, mat) in enumerate([(-0.62, 3.2, 0.10, 0.05, bk), (0.78, 3.8, 0.32, 0.06, bk), (-0.85, 4.4, 0.55, 0.06, bk2),
                                       (0.70, 4.6, -0.12, 0.05, bk), (-0.55, 5.0, 0.85, 0.07, bk), (0.95, 5.2, 0.75, 0.06, bk2)]):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, z), segments=16, ring_count=8)
    o = bpy.context.active_object
    o.data.materials.append(mat)

# ---------------------------------------------------------------- camera
cam = sc.add_camera(lens=85.0, dof=2.8, clip=(0.02, 50))
tgt = sc.target_empty("CamTarget", (0, 0, 0.07))
sc.track_to(cam, tgt)
cam.data.dof.focus_object = tgt


def cam_key(f, dist, tz, tx=0.0, cx=0.0, cz_off=-0.01):
    tgt.location = (tx, 0.0, tz)
    tgt.keyframe_insert("location", frame=f)
    cam.location = (cx, -dist, tz + cz_off)
    cam.keyframe_insert("location", frame=f)


if MODE in ("S01", "test"):
    cam_key(1, 0.40, 0.046, cx=-0.008, cz_off=-0.006)
    cam_key(120, 0.42, 0.062, cx=-0.003, cz_off=-0.006)
    cam_key(336, 0.56, 0.135, cx=0.008, cz_off=-0.008)
    cam_key(552, 0.72, 0.200, cx=0.016, cz_off=-0.010)
    scn.frame_start, scn.frame_end = 1, 552
else:  # S15: wide, calm, whole plume
    cam_key(1, 0.80, 0.175, cx=-0.02)
    cam_key(260, 0.86, 0.19, cx=0.02)
    scn.frame_start, scn.frame_end = 1, 260
for o in (cam, tgt):
    sc.smooth_keys(o)

if MODE == "test":
    out = sc.ROOT / "cache" / "lookdev"
    out.mkdir(parents=True, exist_ok=True)
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 2 or 1)):
        if VDB_FORCE >= 0:
            vol.frame_start = f
            vol.frame_duration = 1
            vol.frame_offset = VDB_FORCE - 1
        scn.frame_set(f)
        print("vdb file:", vol.grids.frame_filepath if hasattr(vol.grids, "frame_filepath") else "?", flush=True)
        scn.render.filepath = str(out / f"incense_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "incense.blend"))
else:
    shot = {"S01": "S01", "S15": "S15", "S15cfd": "S15cfd"}[MODE]
    if MODE.startswith("S15"):
        # closing uses the later, fully developed part of the simulation
        vol.frame_offset = 299
    sc.render_frames(scn, sc.ROOT / "renders" / shot, FIRST, LAST)
