"""S12 — offshore wind turbine on a monopile at sunset, with its helical tip-vortex wake made visible.

blender.exe -b --factory-startup --python blender/shot_offshore.py -- <mode> <first> <last> [pct] [samples] [wake_dens]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

import scene_common as sc  # noqa: E402

A = sc.args()
MODE = A[0] if A else "test"
FIRST = int(A[1]) if len(A) > 1 else 1
LAST = int(A[2]) if len(A) > 2 else FIRST
PCT = int(A[3]) if len(A) > 3 else 100
SAMPLES = int(A[4]) if len(A) > 4 else 48
WAKE_D = float(A[5]) if len(A) > 5 else 0.0  # 0 = no visible wake (looked unconvincing)
NFR = 190
R = 80.0
HUB_Z = 112.0
OMEGA = 2 * math.pi * 10 / 60
YAW = math.radians(30.0)  # downstream wind direction (from +X towards +Y)
SUN_AZ, SUN_EL = 52.0, 8.0
HDRI_SUN_AZ = -38.4

scn = sc.reset_scene()
sc.setup_cycles(scn, samples=SAMPLES, bounces=(6, 1, 2), adaptive=0.02)
scn.render.resolution_percentage = PCT
if hasattr(scn.cycles, "volume_step_rate"):
    scn.cycles.volume_step_rate = 2.0
scn.frame_start, scn.frame_end = 1, NFR
try:
    scn.view_settings.look = "AgX - High Contrast"
    scn.view_settings.exposure = -0.45
except Exception:
    pass

# ---------------------------------------------------------------- sky
w = bpy.data.worlds.new("World")
scn.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes.get("Background")
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(str(sc.ROOT / "assets" / "hdri" / "kloppenheim_06_puresky.hdr"))
tc = nt.nodes.new("ShaderNodeTexCoord")
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Rotation"].default_value = (0, 0, math.radians(HDRI_SUN_AZ - SUN_AZ))
nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0
sun_d = bpy.data.lights.new("Sun", "SUN")
sun_d.energy = 2.5
sun_d.angle = math.radians(0.8)
sun_d.color = (1.0, 0.72, 0.45)
sun = bpy.data.objects.new("Sun", sun_d)
sc.link(sun)
az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
sdir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
sun.rotation_euler = (-sdir).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- sea
def water_material(with_foam=True):
    m, nt, out = sc.new_material("Water" + ("Foam" if with_foam else ""))
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.004, 0.022, 0.030, 1)
    p.inputs["Roughness"].default_value = 0.05
    p.inputs["IOR"].default_value = 1.333
    if with_foam:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "foam"
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.25
        mr.inputs["From Max"].default_value = 0.9
        nt.links.new(at.outputs["Fac"], mr.inputs["Value"])
        foam = nt.nodes.new("ShaderNodeBsdfPrincipled")
        foam.inputs["Base Color"].default_value = (0.75, 0.78, 0.8, 1)
        foam.inputs["Roughness"].default_value = 0.8
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mr.outputs["Result"], mix.inputs["Fac"])
        nt.links.new(p.outputs[0], mix.inputs[1])
        nt.links.new(foam.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


# the ocean modifier generates [origin - size/2, origin - size/2 + size*repeat]: cover x -1000..1000, y -550..1450
bpy.ops.mesh.primitive_plane_add(size=2, location=(-875, -425, 0))
ocean = bpy.context.active_object
ocean.name = "Ocean"
om = ocean.modifiers.new("Ocean", "OCEAN")
om.geometry_mode = "GENERATE"
om.spatial_size = 250
om.resolution = 12
om.viewport_resolution = 6
om.repeat_x = 8
om.repeat_y = 8
om.wave_scale = 1.6
om.choppiness = 1.15
om.wind_velocity = 12.0
om.wave_alignment = 0.55
om.wave_direction = YAW
om.use_normals = True
om.use_foam = True
om.foam_coverage = 0.35
om.foam_layer_name = "foam"
om.random_seed = 7
om.time = 0.0
om.keyframe_insert("time", frame=1)
om.time = (NFR - 1) / 24.0
om.keyframe_insert("time", frame=NFR)
sc.smooth_keys(ocean, interp="LINEAR")
ocean.data.materials.append(water_material(True))
bpy.ops.object.shade_smooth()
# flat water out to the horizon around the ocean tile (4 quads with a hole)
half = 1000.0
cx, cy = 0.0, 450.0
far = 25000.0
bm = bmesh.new()
for (x0, x1, y0, y1) in ((-far, far, cy + half, far), (-far, far, -far, cy - half),
                         (-far, cx - half, cy - half, cy + half), (cx + half, far, cy - half, cy + half)):
    vs = [bm.verts.new((x0, y0, -0.2)), bm.verts.new((x1, y0, -0.2)), bm.verts.new((x1, y1, -0.2)),
          bm.verts.new((x0, y1, -0.2))]
    bm.faces.new(vs)
me = bpy.data.meshes.new("FarSea")
bm.to_mesh(me)
farsea = bpy.data.objects.new("FarSea", me)
sc.link(farsea)
farsea.data.materials.append(water_material(False))

# ---------------------------------------------------------------- turbine
paint, _, _ = sc.principled("TurbineWhite", base=(0.78, 0.79, 0.80), rough=0.38)
yellow, _, _ = sc.principled("TPYellow", base=(0.85, 0.55, 0.02), rough=0.45)
steel, _, _ = sc.principled("PileSteel", base=(0.10, 0.11, 0.10), rough=0.6)
grey, _, _ = sc.principled("Platform", base=(0.35, 0.36, 0.37), rough=0.6)


def cyl(r1, r2, z0, z1, mat, loc=(0, 0), verts=64):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=z1 - z0,
                                    location=(loc[0], loc[1], 0.5 * (z0 + z1)))
    o = bpy.context.active_object
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def blade_mesh():
    """Tapered, twisted blade along +Z (root at z=2.5, tip at z=R)."""
    bm = bmesh.new()
    nsec, npts = 28, 24
    rings = []
    for i in range(nsec):
        u = i / (nsec - 1)
        rr = 2.5 + (R - 2.5) * u
        chord = 2.6 + 2.6 * math.exp(-((u - 0.18) / 0.16) ** 2) - 1.9 * u if u > 0.05 else 2.8
        chord = max(chord, 0.7)
        thick = 0.42 if u < 0.06 else max(0.12, 0.38 - 0.3 * u)
        twist = math.radians(14.0 * (1 - u) ** 1.5)
        ring = []
        for j in range(npts):
            a = 2 * math.pi * j / npts
            # airfoil-ish: rounded leading edge (+x), sharper trailing edge (-x)
            xx = 0.5 * chord * math.cos(a)
            xx = xx if xx > 0 else xx * 1.2
            yy = 0.5 * chord * thick * math.sin(a) * (1 - 0.25 * math.cos(a))
            xr = xx * math.cos(twist) - yy * math.sin(twist)
            yr = xx * math.sin(twist) + yy * math.cos(twist)
            if u < 0.06:  # circular root
                xr, yr = 1.2 * math.cos(a), 1.2 * math.sin(a)
            ring.append(bm.verts.new((yr, xr, rr)))  # chord along Y (rotor plane), thickness along X
        rings.append(ring)
    for i in range(nsec - 1):
        for j in range(npts):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % npts], rings[i + 1][(j + 1) % npts], rings[i + 1][j]))
    bm.faces.new(rings[-1][::-1])
    me = bpy.data.meshes.new("Blade")
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    return me


BLADE = blade_mesh()


def make_turbine(name, x, y, phase=0.0, detailed=True):
    root = bpy.data.objects.new(name, None)
    sc.link(root)
    root.location = (x, y, 0)
    parts = [cyl(3.5, 3.5, -25, 16, steel, verts=64 if detailed else 24),
             cyl(3.65, 3.65, 16, 26, yellow, verts=64 if detailed else 24),
             cyl(5.8, 5.8, 26, 26.6, grey, verts=48 if detailed else 16),
             cyl(3.3, 2.25, 26.6, HUB_Z - 3.5, paint, verts=64 if detailed else 24)]
    for o in parts:
        o.parent = root  # local coords: (0, 0, z) relative to the turbine root
    # nacelle frame: local +X = downstream (wind) direction
    nac = bpy.data.objects.new(name + "_nacelle", None)
    sc.link(nac)
    nac.location = (x, y, HUB_Z)
    nac.rotation_euler = (0, 0, YAW)
    bpy.ops.mesh.primitive_cube_add(size=1)
    box = bpy.context.active_object
    box.scale = (17, 5.6, 6.0)
    box.location = (x, y, HUB_Z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = box.modifiers.new("bev", "BEVEL")
    bev.width = 1.2
    bev.segments = 4
    box.data.materials.append(paint)
    box.parent = nac
    box.location = (4.5, 0, 0.6)
    # rotor (upwind side, local -X)
    rotor = bpy.data.objects.new(name + "_rotor", None)
    sc.link(rotor)
    rotor.parent = nac
    rotor.location = (-5.5, 0, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=2.6, segments=32, ring_count=16)
    hub = bpy.context.active_object
    hub.scale = (1.5, 1, 1)
    hub.data.materials.append(paint)
    bpy.ops.object.shade_smooth()
    hub.parent = rotor
    hub.location = (-1.5, 0, 0)
    for k in range(3):
        b = bpy.data.objects.new(f"{name}_blade{k}", BLADE)
        sc.link(b)
        b.data.materials.append(paint) if not b.data.materials else None
        b.parent = rotor
        b.rotation_euler = (2 * math.pi * k / 3, 0, 0)
        b.location = (-1.0, 0, 0)
    for f in (1, NFR):
        rotor.rotation_euler = (phase + OMEGA * (f - 1) / 24.0, 0, 0)
        rotor.keyframe_insert("rotation_euler", frame=f)
    sc.smooth_keys(rotor, interp="LINEAR")
    return root, nac, rotor


hero = make_turbine("T0", 0.0, 0.0)
for i, (x, y, ph) in enumerate([(520, 620, 1.1), (-420, 820, 2.3), (980, 1150, 0.4), (-980, 1400, 1.7),
                                (240, 1650, 2.9), (1500, 1900, 0.9)]):
    make_turbine(f"T{i + 1}", x, y, ph, detailed=False)

# foam ring where waves hit the monopile
bpy.ops.mesh.primitive_circle_add(vertices=64, radius=6.5, fill_type="NGON", location=(0, 0, 0.35))
ring = bpy.context.active_object
m, ntr, out = sc.new_material("PileFoam")
tcr = ntr.nodes.new("ShaderNodeTexCoord")
dist = ntr.nodes.new("ShaderNodeVectorMath")
dist.operation = "LENGTH"
ntr.links.new(tcr.outputs["Object"], dist.inputs[0])
fr = ntr.nodes.new("ShaderNodeMapRange")
fr.inputs["From Min"].default_value = 6.5
fr.inputs["From Max"].default_value = 3.6
ntr.links.new(dist.outputs["Value"], fr.inputs["Value"])
nz = ntr.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 1.2
nz.inputs["Detail"].default_value = 8
ntr.links.new(tcr.outputs["Object"], nz.inputs["Vector"])
mm = ntr.nodes.new("ShaderNodeMath")
mm.operation = "MULTIPLY"
ntr.links.new(fr.outputs["Result"], mm.inputs[0])
ntr.links.new(nz.outputs["Fac"], mm.inputs[1])
pw = ntr.nodes.new("ShaderNodeMath")
pw.operation = "POWER"
pw.inputs[1].default_value = 2.0
ntr.links.new(mm.outputs[0], pw.inputs[0])
wf = ntr.nodes.new("ShaderNodeBsdfPrincipled")
wf.inputs["Base Color"].default_value = (0.8, 0.82, 0.84, 1)
wf.inputs["Roughness"].default_value = 0.8
tr = ntr.nodes.new("ShaderNodeBsdfTransparent")
mx = ntr.nodes.new("ShaderNodeMixShader")
ntr.links.new(pw.outputs[0], mx.inputs["Fac"])
ntr.links.new(tr.outputs[0], mx.inputs[1])
ntr.links.new(wf.outputs[0], mx.inputs[2])
ntr.links.new(mx.outputs[0], out.inputs["Surface"])
ring.data.materials.append(m)

# ---------------------------------------------------------------- wake (helical tip vortices)
vol = bpy.data.volumes.new("Wake")
vol.filepath = str(sc.ROOT / "cache" / "wake_vdb" / "wake_0000.vdb")
vol.is_sequence = True
vol.frame_duration = NFR
vol.frame_start = 1
vol.frame_offset = -1
vol.sequence_mode = "CLIP"
wake = bpy.data.objects.new("Wake", vol)
if WAKE_D > 0:
    sc.link(wake)
VOX = 1.2
# VDB index (s, y, z) * VOX + (0, -125, -125) in rotor frame; rotor plane sits 5.5 m upwind of the tower axis
rot = Matrix.Rotation(YAW, 4, "Z")
hub_world = Vector((0, 0, HUB_Z)) + Matrix.Rotation(YAW, 3, "Z") @ Vector((-6.5, 0, 0))
wake.matrix_world = Matrix.Translation(hub_world) @ rot @ Matrix.Translation((0, -125, -125)) @ Matrix.Scale(VOX, 4)
m, ntw, out = sc.new_material("WakeFog")
at = ntw.nodes.new("ShaderNodeAttribute")
at.attribute_name = "density"
at.attribute_type = "GEOMETRY"
mu = ntw.nodes.new("ShaderNodeMath")
mu.operation = "MULTIPLY"
mu.inputs[1].default_value = WAKE_D
ntw.links.new(at.outputs["Fac"], mu.inputs[0])
pv = ntw.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Color"].default_value = (0.95, 0.95, 0.97, 1)
pv.inputs["Anisotropy"].default_value = 0.75
ntw.links.new(mu.outputs[0], pv.inputs["Density"])
ntw.links.new(pv.outputs[0], out.inputs["Volume"])
wake.data.materials.append(m)

# ---------------------------------------------------------------- camera
cam = sc.add_camera(lens=35.0, dof=None, clip=(0.5, 30000))
tgt = sc.target_empty("CamTarget", (10, 0, 88))
sc.track_to(cam, tgt)
for f, cl, tl in ((1, (-95.0, -440.0, 12.0), (8, 0, 90)), (NFR, (-58.0, -430.0, 13.0), (14, 0, 88))):
    cam.location = cl
    cam.keyframe_insert("location", frame=f)
    tgt.location = tl
    tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    sc.smooth_keys(o)

if MODE == "test":
    outd = sc.ROOT / "cache" / "lookdev"
    for f in range(FIRST, LAST + 1, max(1, (LAST - FIRST) // 2 or 1)):
        scn.frame_set(f)
        scn.render.filepath = str(outd / f"offshore_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sc.ROOT / "blender" / "offshore.blend"))
else:
    sc.render_frames(scn, sc.ROOT / "renders" / "S12", FIRST, LAST)
