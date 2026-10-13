"""v2 'cell world' (inside the computer): synthwave grid floor, sunset sky with a striped sun, and
edge-lit acrylic cells. Metres; the set is car scale (~10 m)."""
import math

import bmesh
import bpy
import numpy as np

import scene_common as sc
import studio as st


def _n(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def _m(nt, op, a=None, b=None, v0=None, v1=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    if a is not None:
        nt.links.new(a, n.inputs[0])
    elif v0 is not None:
        n.inputs[0].default_value = v0
    if b is not None:
        nt.links.new(b, n.inputs[1])
    elif v1 is not None:
        n.inputs[1].default_value = v1
    return n


def synth_sky(scn, top=(0.012, 0.004, 0.035), mid=(0.20, 0.02, 0.22), horizon=(1.0, 0.25, 0.30), strength=1.0):
    """world: gradient on the view direction's elevation (violet zenith -> magenta -> hot peach horizon)"""
    w = bpy.data.worlds.new("SynthSky")
    scn.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.0, (*horizon, 1)
    el[1].position, el[1].color = 0.45, (*top, 1)
    e = el.new(0.10)
    e.color = (*mid, 1)
    ramp.color_ramp.interpolation = "EASE"
    zc = _m(nt, "MAXIMUM", sep.outputs["Z"], v1=0.0)
    nt.links.new(zc.outputs[0], ramp.inputs["Fac"])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def synth_sun(loc=(0, 220, 30), radius=55.0, stripes=7):
    """the striped synthwave sun: a far disk, yellow-to-magenta, sliced by widening horizontal gaps"""
    bpy.ops.mesh.primitive_circle_add(vertices=128, radius=radius, fill_type="NGON", location=loc,
                                      rotation=(math.pi / 2, 0, 0))
    sun = bpy.context.active_object
    sun.name = "SynthSun"
    m, nt, out = sc.new_material("SunMat")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # object Y is world up for the rotated circle; normalise to v in [-1, 1]
    v = _m(nt, "DIVIDE", sep.outputs["Y"], v1=radius)
    vr = _n(nt, "ShaderNodeMapRange")
    vr.inputs["From Min"].default_value = -1.0
    vr.inputs["From Max"].default_value = 1.0
    nt.links.new(v.outputs[0], vr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.0, (1.0, 0.03, 0.45, 1)
    el[1].position, el[1].color = 1.0, (1.0, 0.85, 0.12, 1)
    e = el.new(0.5)
    e.color = (1.0, 0.32, 0.12, 1)
    nt.links.new(vr.outputs["Result"], ramp.inputs["Fac"])
    # stripes in the lower half: gap where frac(v * stripes) < width(v)
    s = _m(nt, "MULTIPLY", v.outputs[0], v1=stripes)
    fr = _m(nt, "FRACT", s.outputs[0])
    wdt = _m(nt, "MULTIPLY", v.outputs[0], v1=-0.55)       # wider gaps further down
    gap = _m(nt, "LESS_THAN", fr.outputs[0], wdt.outputs[0])
    lower = _m(nt, "LESS_THAN", v.outputs[0], v1=0.1)
    cut = _m(nt, "MULTIPLY", gap.outputs[0], lower.outputs[0])
    vis = _m(nt, "SUBTRACT", v0=1.0, b=cut.outputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 6.0
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(vis.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    sun.data.materials.append(m)
    sun.visible_shadow = False
    return sun


def synth_floor(size=600.0, z=0.0, spacing=1.0, line=(1.0, 0.1, 0.75), strength=3.0, width=0.025, fade=60.0):
    """dark glossy floor with glowing grid lines that fade into the distance"""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    fl = bpy.context.active_object
    fl.name = "GridFloor"
    m, nt, out = sc.new_material("GridFloorMat")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def line_mask(coord):
        a = _m(nt, "DIVIDE", coord, v1=spacing)
        f = _m(nt, "FRACT", _m(nt, "ADD", a.outputs[0], v1=0.5).outputs[0])
        d = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", f.outputs[0], v1=0.5).outputs[0])   # 0 on the line
        r = _n(nt, "ShaderNodeMapRange")
        r.interpolation_type = "SMOOTHSTEP"
        r.inputs["From Min"].default_value = width / spacing
        r.inputs["From Max"].default_value = 0.0
        nt.links.new(d.outputs[0], r.inputs["Value"])
        return r.outputs["Result"]

    lx = line_mask(sep.outputs["X"])
    ly = line_mask(sep.outputs["Y"])
    lm = _m(nt, "MAXIMUM", lx, ly)
    # distance fade from the scene centre (keeps the horizon clean and moire-free)
    vl = nt.nodes.new("ShaderNodeVectorMath")
    vl.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], vl.inputs[0])
    fd = _m(nt, "DIVIDE", vl.outputs["Value"], v1=-fade)
    ex = _m(nt, "EXPONENT", fd.outputs[0])
    lm2 = _m(nt, "MULTIPLY", lm.outputs[0], ex.outputs[0])
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.004, 0.002, 0.008, 1)
    p.inputs["Roughness"].default_value = 0.18
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Coat Roughness"].default_value = 0.05
    p.inputs["Emission Color"].default_value = (*line, 1)
    sm = _m(nt, "MULTIPLY", lm2.outputs[0], v1=strength)
    nt.links.new(sm.outputs[0], p.inputs["Emission Strength"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    fl.data.materials.append(m)
    return fl


def cells_mesh(cells, name="Cells", shrink=0.0):
    """one mesh with a cube per cell (x0, y0, z0, h, level); every face gets the full 0..1 UV square and
    a per-face 'csize' attribute (cell size, metres) + 'clevel', so the shader can draw constant-width edges"""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for (x0, y0, z0, h, L) in cells:
        s = shrink * h
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co.x = x0 + s + (v.co.x + 0.5) * (h - 2 * s)
            v.co.y = y0 + s + (v.co.y + 0.5) * (h - 2 * s)
            v.co.z = z0 + s + (v.co.z + 0.5) * (h - 2 * s)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        for lp, (a, b) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[uv].uv = (a, b)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    hs = np.repeat(np.asarray(cells)[:, 3], 6).astype(np.float32)
    lv = np.repeat(np.asarray(cells)[:, 4], 6).astype(np.float32)
    a = me.attributes.new("csize", "FLOAT", "FACE")
    a.data.foreach_set("value", hs)
    a2 = me.attributes.new("clevel", "FLOAT", "FACE")
    a2.data.foreach_set("value", lv)
    ob = bpy.data.objects.new(name, me)
    sc.link(ob)
    return ob


def acrylic_cell_material(name="AcrylicCell", edge_w=0.012, edge_strength=6.0, face_alpha=0.07,
                          coarse=st.MAGENTA, fine=st.CYAN, lmax=5.0):
    """edge-lit acrylic: nearly clear glossy faces + glowing edges (colour by refinement level)"""
    m, nt, out = sc.new_material(name)
    m.surface_render_method = "BLENDED"
    vis = nt.nodes.new("ShaderNodeValue")
    vis.name = "Vis"
    vis.outputs[0].default_value = 1.0
    uvn = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uvn.outputs["UV"], sep.inputs[0])
    cs = nt.nodes.new("ShaderNodeAttribute")
    cs.attribute_name = "csize"
    cs.attribute_type = "GEOMETRY"
    cl = nt.nodes.new("ShaderNodeAttribute")
    cl.attribute_name = "clevel"
    cl.attribute_type = "GEOMETRY"
    # distance to the nearest face edge, in metres
    u, v = sep.outputs["X"], sep.outputs["Y"]
    du = _m(nt, "MINIMUM", u, _m(nt, "SUBTRACT", v0=1.0, b=u).outputs[0])
    dv = _m(nt, "MINIMUM", v, _m(nt, "SUBTRACT", v0=1.0, b=v).outputs[0])
    d = _m(nt, "MINIMUM", du.outputs[0], dv.outputs[0])
    dm = _m(nt, "MULTIPLY", d.outputs[0], cs.outputs["Fac"])
    # finer cells get thinner lines (but never vanish)
    wl = _m(nt, "MULTIPLY", cs.outputs["Fac"], v1=edge_w / 0.4)
    w = _m(nt, "MINIMUM", wl.outputs[0], v1=edge_w)
    w2 = _m(nt, "MAXIMUM", w.outputs[0], v1=edge_w * 0.22)
    em = _n(nt, "ShaderNodeMapRange")
    em.interpolation_type = "SMOOTHSTEP"
    em.inputs["From Min"].default_value = 0.0
    nt.links.new(dm.outputs[0], em.inputs["Value"])
    nt.links.new(w2.outputs[0], em.inputs["From Max"])
    em.inputs["To Min"].default_value = 1.0
    em.inputs["To Max"].default_value = 0.0
    lvl = _m(nt, "DIVIDE", cl.outputs["Fac"], v1=lmax)
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (*coarse, 1)
    col.inputs["B"].default_value = (*fine, 1)
    nt.links.new(lvl.outputs[0], col.inputs["Factor"])
    e = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(col.outputs["Result"], e.inputs["Color"])
    es = _m(nt, "MULTIPLY", em.outputs["Result"], v1=edge_strength)
    es.name = "EdgeGain"
    es2 = _m(nt, "MULTIPLY", es.outputs[0], vis.outputs[0])
    nt.links.new(es2.outputs[0], e.inputs["Strength"])
    # faces: glossy acrylic sheen, mostly transparent
    g = nt.nodes.new("ShaderNodeBsdfPrincipled")
    g.inputs["Base Color"].default_value = (0.6, 0.75, 1.0, 1)
    g.inputs["Roughness"].default_value = 0.08
    g.inputs["Thin Film Thickness"].default_value = 450.0
    g.inputs["Thin Film IOR"].default_value = 1.45
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.25
    fa = _m(nt, "MULTIPLY", lw.outputs["Fresnel"], v1=face_alpha * 4)
    fa2 = _m(nt, "ADD", fa.outputs[0], v1=face_alpha * 0.4, clamp=True)
    fa3 = _m(nt, "MULTIPLY", fa2.outputs[0], vis.outputs[0])
    fmix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fa3.outputs[0], fmix.inputs["Fac"])
    nt.links.new(tr.outputs[0], fmix.inputs[1])
    nt.links.new(g.outputs[0], fmix.inputs[2])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(fmix.outputs[0], add.inputs[0])
    nt.links.new(e.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def build_world(scn, sun=(150, 200, 30), sun_r=48, sky_strength=0.6, grid_spacing=0.8, grid_strength=4.0, fade=45.0):
    """the standard cell-world environment"""
    synth_sky(scn, strength=sky_strength)
    synth_sun(loc=sun, radius=sun_r)
    synth_floor(spacing=grid_spacing, strength=grid_strength, fade=fade)


def key_vis(mat, frame, value, interp="BEZIER"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    v = mat.node_tree.nodes["Vis"].outputs[0]
    v.default_value = value
    v.keyframe_insert("default_value", frame=frame)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
