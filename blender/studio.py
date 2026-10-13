"""v2 shared look: render setup (scene-linear EXR out, graded later in src/grade.py) and the neon studio set.

Neon studio = black lacquer floor, glowing glass tubes (each backed by a real area light so it lights the
scene in Eevee too), coloured rim spots, a long overhead strip softbox for 'car-ad' highlights, and haze.
Scale: metres; the tabletop set is ~0.5 m across (Clawd ~7 cm wide at unit 0.004).
"""
import math

import bpy
from mathutils import Vector

import scene_common as sc

# neon palette (linear RGB)
MAGENTA = (1.0, 0.09, 0.62)
CYAN = (0.05, 0.78, 1.0)
VIOLET = (0.38, 0.12, 1.0)
PEACH = (1.0, 0.42, 0.18)
LIME = (0.55, 1.0, 0.06)
WHITE = (1.0, 0.97, 0.94)


def _set(obj, **kw):
    for k, v in kw.items():
        if hasattr(obj, k):
            try:
                setattr(obj, k, v)
            except Exception as e:  # noqa: BLE001
                print("studio: cannot set", k, e)


def setup_render(scn, engine="eevee", samples=64, res=(1920, 1080), exr=True):
    if engine == "cycles":
        sc.setup_cycles(scn, samples=samples, res=res, bounces=(6, 2, 2), adaptive=0.015)
    else:
        scn.render.engine = "BLENDER_EEVEE"
        e = scn.eevee
        _set(e, taa_render_samples=samples, use_raytracing=True, ray_tracing_method="SCREEN", use_shadows=True,
             shadow_ray_count=2, shadow_step_count=8, use_volumetric_shadows=True, volumetric_tile_size="4",
             volumetric_samples=96, volumetric_shadow_samples=24, use_fast_gi=True, fast_gi_method="GLOBAL_ILLUMINATION",
             volumetric_light_clamp=0.0, clamp_surface_indirect=10.0)
        ro = e.ray_tracing_options
        _set(ro, resolution_scale="1", use_denoise=True, screen_trace_quality=0.6, trace_max_roughness=0.6)
        scn.render.resolution_x, scn.render.resolution_y = res
        scn.render.resolution_percentage = 100
        scn.render.fps = 24
    scn.render.use_persistent_data = True
    scn.render.film_transparent = False
    if exr:
        s = scn.render.image_settings
        s.file_format = "OPEN_EXR"
        s.color_depth = "16"
        s.exr_codec = "DWAA"
        s.color_mode = "RGB"
    scn.view_settings.view_transform = "Standard"     # EXR is scene-linear anyway; grading happens in src/grade.py
    scn.view_settings.look = "None"
    return scn


def lacquer_floor(size=6.0, z=0.0, rough=0.09, name="Floor"):
    """black lacquer with a faint roughness breakup so reflections are not CG-perfect"""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    fl = bpy.context.active_object
    fl.name = name
    m, nt, out = sc.new_material("Lacquer")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.004, 0.004, 0.006, 1)
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.015
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 18.0
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough * 0.5
    mr.inputs["To Max"].default_value = rough * 1.6
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], p.inputs["Roughness"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    fl.data.materials.append(m)
    return fl


TUBE_LIGHTS = {}


def neon_tube(points, color, strength=25.0, radius=0.003, light=True, light_energy=None, name="Neon"):
    """a glowing glass tube along a polyline (world coords), plus thin area lights along each segment"""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, q in zip(sp.points, points):
        p.co = (*q, 1)
    ob = bpy.data.objects.new(name, cu)
    sc.link(ob)
    m = sc.emission_mat(f"{name}Mat", color, strength)
    ob.data.materials.append(m)
    ob.visible_shadow = False
    TUBE_LIGHTS[name] = []
    if light:
        for i in range(len(points) - 1):
            a, b = Vector(points[i]), Vector(points[i + 1])
            ld = bpy.data.lights.new(f"{name}L{i}", "AREA")
            ld.shape = "RECTANGLE"
            ld.size = (b - a).length
            ld.size_y = radius * 4
            ld.color = color
            ld.energy = light_energy if light_energy is not None else 40.0 * (b - a).length
            lo = bpy.data.objects.new(f"{name}L{i}", ld)
            lo.location = (a + b) / 2
            d = (b - a).normalized()
            # area light emits along its local -Z; orient X along the tube, face the scene centre
            to_c = (Vector((0, 0, lo.location.z * 0.5)) - lo.location)
            z = -(to_c - to_c.project(d)).normalized()
            if z.length < 1e-6:
                z = Vector((0, 1, 0))
            y = z.cross(d)
            from mathutils import Matrix
            lo.matrix_world = Matrix((d, y, z)).transposed().to_4x4()
            lo.location = (a + b) / 2
            _set(ld, use_soft_falloff=True)
            lo.visible_camera = False
            sc.link(lo)
            TUBE_LIGHTS[name].append(lo)
    return ob


FLICKER = ((0, 1.0), (2, 0.0), (3, 0.6), (5, 0.0), (9, 1.0), (11, 0.35), (12, 1.0))


def _key_value(sock_or_data, attr, frame, value):
    setattr(sock_or_data, attr, value)
    sock_or_data.keyframe_insert(attr, frame=frame)


def neon_switch(tube, f_on, flicker=FLICKER, f_off=None, extra_lights=()):
    """neon sign behaviour: dark until f_on, a few stuttering flashes, then steady (optionally off again at f_off).
    Keys the tube emission, its area lights and any extra lights (e.g. rim spots that 'belong' to the tube)."""
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
    em = tube.data.materials[0].node_tree.nodes["Emission"].inputs["Strength"]
    s_on = em.default_value
    items = [(em, "default_value", s_on)]
    for lo in TUBE_LIGHTS.get(tube.name, []) + list(extra_lights):
        items.append((lo.data, "energy", lo.data.energy))
    for target, attr, full in items:
        _key_value(target, attr, 1, 0.0)
        _key_value(target, attr, f_on - 1, 0.0)
        for df, k in flicker:
            _key_value(target, attr, f_on + df, full * k)
        if f_off is not None:
            _key_value(target, attr, f_off, full * 0.4)
            _key_value(target, attr, f_off + 2, full)
            _key_value(target, attr, f_off + 4, 0.0)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"


def add_haze(density=0.6, size=4.0, center=(0, 0, 0.5), anisotropy=0.35, color=(0.9, 0.92, 1.0), name="Haze"):
    """a big box of thin participating medium (density per metre)"""
    bpy.ops.mesh.primitive_cube_add(size=size, location=center)
    hz = bpy.context.active_object
    hz.name = name
    m, nt, out = sc.new_material(f"{name}Mat")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Density"].default_value = density
    pv.inputs["Anisotropy"].default_value = anisotropy
    pv.inputs["Color"].default_value = (*color, 1)
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    hz.data.materials.append(m)
    hz.visible_shadow = False
    return hz


def strip_softbox(loc, size=(0.9, 0.06), energy=60.0, color=WHITE, target=(0, 0, 0), name="Strip", visible=True):
    lt = sc.add_light(name, "AREA", loc, energy, color=color, target=target)
    lt.data.shape = "RECTANGLE"
    lt.data.size, lt.data.size_y = size
    _set(lt.data, spread=math.radians(60))
    lt.visible_camera = visible
    lt.visible_glossy = True
    return lt


def neon_studio(scn, haze_density=0.9, floor=True, tubes="default", world=(0.002, 0.0015, 0.004), haze=None, z0=0.0,
                lights=True, floor_rough=0.09):
    """the default tabletop neon studio around the origin (Clawd scale); z0 = table height"""
    if haze is not None:
        haze_density = haze
    sc.world_color(scn, world, 1.0)
    if floor:
        lacquer_floor(z=z0, rough=floor_rough)

    def P(x, y, z):
        return (x, y, z + z0)
    if tubes == "default":
        # magenta 'L' far back-left, cyan bar back-right, a violet low bar behind
        neon_tube([P(-0.36, 0.42, 0.0), P(-0.36, 0.42, 0.34), P(-0.16, 0.42, 0.34)], MAGENTA, 30.0, name="NeonMag")
        neon_tube([P(0.12, 0.48, 0.22), P(0.42, 0.48, 0.22)], CYAN, 30.0, name="NeonCyan")
        neon_tube([P(-0.10, 0.62, 0.05), P(0.22, 0.62, 0.05)], VIOLET, 22.0, name="NeonVio")
    if lights:
        # rim spots (coloured), a soft overhead strip for the long glossy highlight, faint warm front fill
        sc.add_light("RimMag", "SPOT", P(-0.45, 0.35, 0.22), 9.0, color=MAGENTA, size=0.03, target=P(0, 0, 0.02),
                     spot_size=math.radians(45), blend=0.7)
        sc.add_light("RimCyan", "SPOT", P(0.45, 0.35, 0.20), 9.0, color=CYAN, size=0.03, target=P(0, 0, 0.02),
                     spot_size=math.radians(45), blend=0.7)
        strip_softbox(P(0.0, 0.05, 0.55), size=(0.8, 0.05), energy=14.0, target=P(0, 0.05, 0), name="TopStrip",
                      visible=False)
        sc.add_light("Fill", "AREA", P(0.1, -0.6, 0.25), 0.6, color=(1.0, 0.75, 0.6), size=0.4, target=P(0, 0, 0.03))
    if haze_density > 0:
        add_haze(haze_density, size=2.5, center=P(0, 0.3, 0.6))


def neon_text(lines, font_path, height, location, color, strength=40.0, tube=None, line_gap=1.25, board=True,
              name="Sign", light_energy=0.6, per_word=True):
    """a neon sign: every word is a glass tube tracing the font outline (separate objects, so they can flicker
    on one by one), on an optional black acrylic backing board. height = cap height in metres.
    Returns a list of word objects (reading order)."""
    import sys
    venv = str(sc.ROOT / ".venv" / "Lib" / "site-packages")
    if venv not in sys.path:
        sys.path.append(venv)          # PIL from the project venv (same Python 3.13 as Blender)
    from PIL import ImageFont
    pf = ImageFont.truetype(font_path, 1000)
    font = bpy.data.fonts.load(font_path, check_existing=True)
    tube = tube or height * 0.035
    letters = []
    em = height / 0.70                                 # Blender body size: cap height ~ 0.70 em
    widths = [pf.getlength(t) / 1000.0 * em for t in lines]
    x0c, y0, z0 = location
    for li, text in enumerate(lines):
        z = z0 - li * height * line_gap * 1.25
        x_line = x0c - widths[li] / 2
        start = 0
        for word in (text.split(" ") if per_word else [text]):
            i0 = text.index(word, start)
            start = i0 + len(word)
            x = x_line + pf.getlength(text[:i0]) / 1000.0 * em
            adv = pf.getlength(word) / 1000.0 * em
            cu = bpy.data.curves.new(f"{name}_{li}_{len(letters)}", "FONT")
            cu.body = word
            cu.font = font
            cu.size = em
            cu.fill_mode = "NONE"
            cu.bevel_depth = tube
            cu.bevel_resolution = 3
            cu.resolution_u = 6
            ob = bpy.data.objects.new(cu.name, cu)
            ob.location = (x, y0, z)
            ob.rotation_euler = (math.pi / 2, 0, 0)
            sc.link(ob)
            ob.data.materials.append(sc.emission_mat(f"{cu.name}Mat", color, strength))
            ob.visible_shadow = False
            letters.append(ob)
            TUBE_LIGHTS[ob.name] = []
            for k in range(max(1, len(word) // 2)):     # a few lights along each word so it lights the smoke
                ld = bpy.data.lights.new(f"{cu.name}L{k}", "POINT")
                ld.energy = light_energy * 2
                ld.color = color
                ld.shadow_soft_size = height * 0.4
                lo = bpy.data.objects.new(f"{cu.name}L{k}", ld)
                lo.location = (x + adv * (k + 0.5) / max(1, len(word) // 2), y0 - height * 0.3, z + height * 0.35)
                lo.visible_camera = False
                lo.visible_glossy = False
                ld.specular_factor = 0.0
                sc.link(lo)
                TUBE_LIGHTS[ob.name].append(lo)
    if board:
        total_h = height * line_gap * 1.25 * (len(lines) - 1) + height
        bw = max(widths) + height * 1.2
        bh = total_h + height * 1.0
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x0c, y0 + height * 0.25, z0 + height / 2 - total_h / 2 +
                                                          height * 0.05))
        bd = bpy.context.active_object
        bd.name = f"{name}Board"
        bd.scale = (bw, height * 0.12, bh)
        m, nt, out = sc.new_material(f"{name}BoardMat")
        p = nt.nodes.new("ShaderNodeBsdfPrincipled")
        p.inputs["Base Color"].default_value = (0.006, 0.005, 0.01, 1)
        p.inputs["Roughness"].default_value = 0.2
        p.inputs["Coat Weight"].default_value = 1.0
        p.inputs["Coat Roughness"].default_value = 0.02
        nt.links.new(p.outputs[0], out.inputs["Surface"])
        bd.data.materials.append(m)
    return letters
