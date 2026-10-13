"""Act II props (Eevee-friendly): the fluid parcel (edge-lit acrylic cube), pillars, arrows."""
import math

import bpy
from mathutils import Vector

import scene_common as sc
import studio as st


def _edge_factor(nt, half, width):
    """smooth 0..1 factor near the cube edges (object space), 'half' = half size"""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ds = []
    for comp in ("X", "Y", "Z"):
        a = nt.nodes.new("ShaderNodeMath")
        a.operation = "ABSOLUTE"
        nt.links.new(sep.outputs[comp], a.inputs[0])
        d = nt.nodes.new("ShaderNodeMath")
        d.operation = "SUBTRACT"
        d.inputs[0].default_value = half
        nt.links.new(a.outputs[0], d.inputs[1])
        ds.append(d.outputs[0])

    def m(op, x, y):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        nt.links.new(x, n.inputs[0])
        nt.links.new(y, n.inputs[1])
        return n.outputs[0]
    second = m("MAXIMUM", m("MINIMUM", ds[0], ds[1]), m("MINIMUM", m("MAXIMUM", ds[0], ds[1]), ds[2]))
    e = nt.nodes.new("ShaderNodeMapRange")
    e.interpolation_type = "SMOOTHSTEP"
    e.inputs["From Min"].default_value = width
    e.inputs["From Max"].default_value = 0.0
    nt.links.new(second, e.inputs["Value"])
    return e.outputs["Result"]


def parcel(size=0.022, color=st.CYAN, name="Parcel", glow=5.0, inner=0.6):
    """a parcel of fluid: clear acrylic cube with glowing edges and a soft inner glow"""
    bpy.ops.mesh.primitive_cube_add(size=size)
    ob = bpy.context.active_object
    ob.name = name
    bv = ob.modifiers.new("b", "BEVEL")
    bv.width = size * 0.06
    bv.segments = 3
    m, nt, out = sc.new_material(f"{name}Mat")
    m.surface_render_method = "BLENDED"
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = 0.05
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Thin Film Thickness"].default_value = 400.0
    p.inputs["Thin Film IOR"].default_value = 1.4
    ef = _edge_factor(nt, size / 2, size * 0.07)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    sm = nt.nodes.new("ShaderNodeMath")
    sm.operation = "MULTIPLY_ADD"
    sm.inputs[1].default_value = glow
    sm.inputs[2].default_value = inner
    nt.links.new(ef, sm.inputs[0])
    nt.links.new(sm.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(p.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.3
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(lw.outputs["Fresnel"], mx.inputs[0])
    nt.links.new(ef, mx.inputs[1])
    mx2 = nt.nodes.new("ShaderNodeMath")
    mx2.operation = "MULTIPLY_ADD"
    mx2.inputs[1].default_value = 0.8
    mx2.inputs[2].default_value = 0.25
    mx2.use_clamp = True
    nt.links.new(mx.outputs[0], mx2.inputs[0])
    nt.links.new(mx2.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(add.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    lt = bpy.data.lights.new(f"{name}Glow", "POINT")
    lt.energy = 0.25
    lt.color = color
    lt.shadow_soft_size = size
    lt.specular_factor = 0.0          # light the surroundings, but no mirror-highlight blob on glossy floors
    lo = bpy.data.objects.new(f"{name}Glow", lt)
    lo.parent = ob
    sc.link(lo)
    return ob


def pillar(radius=0.035, height=0.07, loc=(0, 0, 0), ring=st.MAGENTA, name="Pillar"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=height,
                                        location=(loc[0], loc[1], loc[2] + height / 2))
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.shade_smooth()
    m, nt, p = sc.principled(f"{name}Mat", base=(0.006, 0.006, 0.01), rough=0.15, coat=1.0)
    ob.data.materials.append(m)
    st.neon_tube([(loc[0] + radius * 1.02 * math.cos(t), loc[1] + radius * 1.02 * math.sin(t), loc[2] + height - 0.004)
                  for t in [2 * math.pi * k / 48 for k in range(49)]], ring, 18.0, radius=0.0012, light=False,
                 name=f"{name}Ring")
    return ob


def arrow(name, color, length=0.05, radius=0.0025, strength=8.0):
    """neon arrow along +X from the origin (scale X to change length)"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=length * 0.75,
                                        location=(length * 0.375, 0, 0), rotation=(0, math.pi / 2, 0))
    shaft = bpy.context.active_object
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=radius * 2.6, depth=length * 0.25,
                                    location=(length * 0.875, 0, 0), rotation=(0, math.pi / 2, 0))
    head = bpy.context.active_object
    shaft.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = shaft
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    ob.data.materials.append(sc.emission_mat(f"{name}Mat", color, strength))
    return ob


def smooth_path_keys(ob, positions, frames, interp="LINEAR"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    for f, p in zip(frames, positions):
        ob.location = Vector(p)
        ob.keyframe_insert("location", frame=f)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
