"""v2 reusable props: incense stick + its simulated smoke (v1 VDBs), holder, table-top."""
import bpy

import scene_common as sc

VDB_DIR = sc.ROOT / "cache" / "incense_vdb"
VOX = 0.0005             # metres per fine smoke voxel (fine grid 384 x 384 x 768, ember at z ~ 0.011 m)


def _math(nt, op, a=None, b=None, v1=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    if a is not None:
        nt.links.new(a, n.inputs[0])
    if b is not None:
        nt.links.new(b, n.inputs[1])
    elif v1 is not None:
        n.inputs[1].default_value = v1
    return n


def incense_smoke(dens=170.0, fall=1.6, color=(0.85, 0.87, 0.92), anisotropy=0.55, frame_offset=-1, n_files=560,
                  emission=0.0, emission_color=(1, 1, 1)):
    """the v1 LBM plume as a VDB sequence; visible density thins ~1/z^fall as the plume entrains air"""
    vol = bpy.data.volumes.new("Smoke")
    vol.filepath = str(VDB_DIR / "incense_0000.vdb")
    vol.is_sequence = True
    vol.frame_duration = n_files
    vol.frame_start = 1
    vol.frame_offset = frame_offset
    vol.sequence_mode = "CLIP"
    smoke = bpy.data.objects.new("Smoke", vol)
    sc.link(smoke)
    smoke.scale = (VOX, VOX, VOX)
    smoke.location = (-192 * VOX, -192 * VOX, 0.0)
    m, nt, out = sc.new_material("SmokeMat")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "density"
    attr.attribute_type = "GEOMETRY"
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sz.inputs[0])
    hz = _math(nt, "ADD", sz.outputs["Z"], v1=0.025)
    hd = nt.nodes.new("ShaderNodeMath")
    hd.operation = "DIVIDE"
    hd.inputs[0].default_value = 0.035
    nt.links.new(hz.outputs[0], hd.inputs[1])
    hp = _math(nt, "POWER", hd.outputs[0], v1=fall)
    hc = nt.nodes.new("ShaderNodeClamp")
    hc.inputs["Min"].default_value = 0.05
    hc.inputs["Max"].default_value = 1.0
    nt.links.new(hp.outputs[0], hc.inputs["Value"])
    dz = _math(nt, "MULTIPLY", attr.outputs["Fac"], hc.outputs[0])
    mul = _math(nt, "MULTIPLY", dz.outputs[0], v1=dens)
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Anisotropy"].default_value = anisotropy
    pv.inputs["Color"].default_value = (*color, 1)
    nt.links.new(mul.outputs[0], pv.inputs["Density"])
    if emission > 0:
        pv.inputs["Emission Color"].default_value = (*emission_color, 1)
        em = _math(nt, "MULTIPLY", dz.outputs[0], v1=emission)
        nt.links.new(em.outputs[0], pv.inputs["Emission Strength"])
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    smoke.data.materials.append(m)
    smoke.visible_shadow = True
    return smoke, vol, (nt, pv, dz)


def incense_stick(base_z=-0.1):
    """burning incense stick, ember tip at z ~ 0.011, standing in a small holder whose top is at base_z"""
    top = 0.0108
    length = top - base_z + 0.01
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.00105, depth=length, location=(0, 0, top - length / 2))
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
    h = length / 2   # object-space z of the tip
    zr = nt.nodes.new("ShaderNodeMapRange")
    zr.inputs["From Min"].default_value = h - 0.009
    zr.inputs["From Max"].default_value = h
    nt.links.new(sep.outputs["Z"], zr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.055, 0.022, 0.012, 1)
    els[1].position, els[1].color = 1.0, (0.32, 0.31, 0.30, 1)
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
    band = nt.nodes.new("ShaderNodeMapRange")
    band.interpolation_type = "SMOOTHSTEP"
    band.inputs["From Min"].default_value = h - 0.0075
    band.inputs["From Max"].default_value = h - 0.0035
    nt.links.new(sep.outputs["Z"], band.inputs["Value"])
    band2 = nt.nodes.new("ShaderNodeMapRange")
    band2.interpolation_type = "SMOOTHSTEP"
    band2.inputs["From Min"].default_value = h - 0.0005
    band2.inputs["From Max"].default_value = h - 0.0035
    nt.links.new(sep.outputs["Z"], band2.inputs["Value"])
    bm = _math(nt, "MINIMUM", band.outputs["Result"], band2.outputs["Result"])
    en = nt.nodes.new("ShaderNodeTexNoise")
    en.noise_dimensions = "4D"
    en.inputs["Scale"].default_value = 1500.0
    en.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], en.inputs["Vector"])
    drv = en.inputs["W"].driver_add("default_value")
    drv.driver.expression = "frame/30"
    em2 = _math(nt, "MULTIPLY", bm.outputs[0], en.outputs["Fac"])
    em3 = _math(nt, "POWER", em2.outputs[0], v1=1.6)
    em4 = _math(nt, "MULTIPLY", em3.outputs[0], v1=45.0)
    bb = nt.nodes.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = 1350.0
    nt.links.new(bb.outputs[0], p.inputs["Emission Color"])
    nt.links.new(em4.outputs[0], p.inputs["Emission Strength"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    stick.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    sc.add_light("Ember", "POINT", (0, 0, 0.0072), 0.05, color=(1.0, 0.42, 0.12), size=0.0012)
    # holder: a small glossy black puck
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.018, depth=0.008, location=(0, 0, base_z + 0.004))
    puck = bpy.context.active_object
    puck.name = "Holder"
    pm, _, pp = sc.principled("HolderMat", base=(0.02, 0.02, 0.025), rough=0.25, coat=1.0)
    puck.data.materials.append(pm)
    bpy.ops.object.shade_smooth()
    return stick, puck


def acrylic_block(center, size, edge_color=(0.05, 0.78, 1.0), edge_strength=12.0, edge_w=0.0012, name="Block",
                  tint=(0.85, 0.9, 1.0)):
    """clear acrylic box whose edges glow (edge-lit acrylic sign look); size = (sx, sy, sz) metres"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width = min(size) * 0.04
    bev.segments = 3
    m, nt, out = sc.new_material(f"{name}Mat")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*tint, 1)
    p.inputs["Roughness"].default_value = 0.03
    p.inputs["IOR"].default_value = 1.49
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Thin Film Thickness"].default_value = 320.0
    p.inputs["Thin Film IOR"].default_value = 1.35
    # edges: distance to the nearest box edge in object space (two smallest face distances)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    half = [s / 2 for s in size]
    ds = []
    for comp, h in zip(("X", "Y", "Z"), half):
        a = _math(nt, "ABSOLUTE", sep.outputs[comp])
        d = nt.nodes.new("ShaderNodeMath")
        d.operation = "SUBTRACT"
        d.inputs[0].default_value = h
        nt.links.new(a.outputs[0], d.inputs[1])
        ds.append(d.outputs[0])
    # second-smallest of three = max(min(a,b), min(max(a,b), c))
    mn_ab = _math(nt, "MINIMUM", ds[0], ds[1])
    mx_ab = _math(nt, "MAXIMUM", ds[0], ds[1])
    mn2 = _math(nt, "MINIMUM", mx_ab.outputs[0], ds[2])
    second = _math(nt, "MAXIMUM", mn_ab.outputs[0], mn2.outputs[0])
    e = nt.nodes.new("ShaderNodeMapRange")
    e.interpolation_type = "SMOOTHSTEP"
    e.inputs["From Min"].default_value = edge_w
    e.inputs["From Max"].default_value = 0.0
    nt.links.new(second.outputs[0], e.inputs["Value"])
    es = _math(nt, "MULTIPLY", e.outputs["Result"], v1=edge_strength)
    es.name = "EdgeGain"
    p.inputs["Emission Color"].default_value = (*edge_color, 1)
    nt.links.new(es.outputs[0], p.inputs["Emission Strength"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


def block_stack(x, table_z, n=2, w=0.05, d=0.04, h=0.0425, edge_color=(0.05, 0.78, 1.0), name="Stack", gap=0.0006,
                edge_strength=2.5):
    """n acrylic blocks stacked on the table at x; returns the top height"""
    z = table_z
    for i in range(n):
        tint = tuple(0.75 + 0.25 * c for c in edge_color)
        acrylic_block((x, 0.0, z + h / 2), (w, d, h - gap), edge_color=edge_color, name=f"{name}{i}",
                      edge_strength=edge_strength, tint=tint)
        z += h
    return z


def smoke_twin_wipe(mat_info, wipe_keys, vort_max=0.007, edge_color=(0.75, 0.95, 1.0), emission=22.0, cell=8.0):
    """turn an incense_smoke() material into a 'CFD x-ray' wipe: left of a moving vertical scan plane the smoke shows
    its simulated twin (coloured by vorticity, neon ramp, glowing); right of it the real smoke; a bright scan edge.
    wipe_keys: [(frame, x_world), ...]"""
    nt, pv, dz = mat_info
    out = nt.nodes["Material Output"]
    dens_link = pv.inputs["Density"].links[0].from_socket
    pc = nt.nodes.new("ShaderNodeVolumePrincipled")
    pc.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(dens_link, pc.inputs["Density"])
    va = nt.nodes.new("ShaderNodeAttribute")
    va.attribute_name = "vorticity"
    va.attribute_type = "GEOMETRY"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = vort_max
    nt.links.new(va.outputs["Fac"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.12, 0.05, 0.9, 1)           # calm: violet
    els[1].position, els[1].color = 1.0, (1.0, 0.55, 0.12, 1)           # strongest swirl: hot orange
    for pos, col in ((0.3, (0.02, 0.7, 1.0, 1)), (0.65, (1.0, 0.08, 0.6, 1))):
        e = els.new(pos)
        e.color = col
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    pc.inputs["Color"].default_value = (0.08, 0.08, 0.1, 1)             # barely scatters: the colour is its own light
    nt.links.new(ramp.outputs["Color"], pc.inputs["Emission Color"])
    # the twin is made of cells: faint lattice lines every `cell` voxels
    tcg = nt.nodes.new("ShaderNodeTexCoord")
    sg = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tcg.outputs["Object"], sg.inputs[0])
    lines = None
    for comp in ("X", "Z"):
        fr_ = _math(nt, "FRACT", _math(nt, "DIVIDE", sg.outputs[comp], v1=cell).outputs[0])
        dd = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", fr_.outputs[0], v1=0.5).outputs[0])
        ln = _math(nt, "GREATER_THAN", dd.outputs[0], v1=0.44)
        lines = ln if lines is None else _math(nt, "MAXIMUM", lines.outputs[0], ln.outputs[0])
    gl = _math(nt, "MULTIPLY_ADD", lines.outputs[0], v1=0.9)
    gl.inputs[2].default_value = 0.75
    em0 = _math(nt, "MULTIPLY", dz.outputs[0], v1=emission)
    em = _math(nt, "MULTIPLY", em0.outputs[0], gl.outputs[0])
    nt.links.new(em.outputs[0], pc.inputs["Emission Strength"])
    # explicit object-space coordinates (voxel units), converted back to metres: robust whatever space
    # 'Geometry > Position' uses for volumes
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sx = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sx.inputs[0])
    xm = _math(nt, "MULTIPLY_ADD", sx.outputs["X"], v1=VOX)
    xm.inputs[2].default_value = -192 * VOX
    xw = nt.nodes.new("ShaderNodeValue")
    for f, v in wipe_keys:
        xw.outputs[0].default_value = v
        xw.outputs[0].keyframe_insert("default_value", frame=f)
    dx = _math(nt, "SUBTRACT", xw.outputs[0], xm.outputs[0])
    fac = nt.nodes.new("ShaderNodeMapRange")
    fac.interpolation_type = "SMOOTHSTEP"
    fac.inputs["From Min"].default_value = 0.0015
    fac.inputs["From Max"].default_value = -0.0015
    nt.links.new(dx.outputs[0], fac.inputs["Value"])
    mixw = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac.outputs["Result"], mixw.inputs["Fac"])
    nt.links.new(pc.outputs[0], mixw.inputs[1])
    nt.links.new(pv.outputs[0], mixw.inputs[2])
    ad = _math(nt, "ABSOLUTE", dx.outputs[0])
    edge = nt.nodes.new("ShaderNodeMapRange")
    edge.inputs["From Min"].default_value = 0.0012
    edge.inputs["From Max"].default_value = 0.0
    nt.links.new(ad.outputs[0], edge.inputs["Value"])
    eg = _math(nt, "MULTIPLY", edge.outputs["Result"], dz.outputs[0])
    eg2 = _math(nt, "MULTIPLY", eg.outputs[0], v1=60.0)
    ev = nt.nodes.new("ShaderNodeEmission")
    ev.inputs["Color"].default_value = (*edge_color, 1)
    nt.links.new(eg2.outputs[0], ev.inputs["Strength"])
    addv = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(mixw.outputs[0], addv.inputs[0])
    nt.links.new(ev.outputs[0], addv.inputs[1])
    nt.links.new(addv.outputs[0], out.inputs["Volume"])
    return xw
