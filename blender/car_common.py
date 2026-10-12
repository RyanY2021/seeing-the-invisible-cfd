"""Import the procedural SDF car into Blender with clay / glass / rubber / alloy materials."""
import math

import bpy

import scene_common as sc

CAR_DIR = sc.ROOT / "cache" / "car"
WHEELS_X = (0.92, 3.58)
WHEEL_Z = 0.335
RIM_Y = 0.955


def import_ply(path, name):
    bpy.ops.wm.ply_import(filepath=str(path))
    o = bpy.context.selected_objects[0]
    o.name = name
    bpy.ops.object.shade_smooth()
    return o


def body_material(color=(0.60, 0.585, 0.56), rough=0.40, coat=0.25):
    m, nt, out = sc.new_material("CarBody")
    clay = nt.nodes.new("ShaderNodeBsdfPrincipled")
    clay.inputs["Base Color"].default_value = (*color, 1)
    clay.inputs["Roughness"].default_value = rough
    clay.inputs["Coat Weight"].default_value = coat
    glass = nt.nodes.new("ShaderNodeBsdfPrincipled")
    glass.inputs["Base Color"].default_value = (0.012, 0.014, 0.018, 1)
    glass.inputs["Roughness"].default_value = 0.04
    glass.inputs["Coat Weight"].default_value = 1.0
    glass.inputs["Specular IOR Level"].default_value = 0.8
    vc = nt.nodes.new("ShaderNodeVertexColor")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vc.outputs["Color"], sep.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    edge = nt.nodes.new("ShaderNodeMapRange")
    edge.interpolation_type = "SMOOTHSTEP"
    edge.inputs["From Min"].default_value = 0.42
    edge.inputs["From Max"].default_value = 0.58
    nt.links.new(sep.outputs[0], edge.inputs["Value"])
    nt.links.new(edge.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(clay.outputs[0], mix.inputs[1])
    nt.links.new(glass.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def rim_material():
    m, nt, out = sc.new_material("Rim")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ang = nt.nodes.new("ShaderNodeMath")
    ang.operation = "ARCTAN2"
    nt.links.new(sep.outputs["Y"], ang.inputs[0])
    nt.links.new(sep.outputs["X"], ang.inputs[1])
    m5 = nt.nodes.new("ShaderNodeMath")
    m5.operation = "MULTIPLY"
    m5.inputs[1].default_value = 5.0
    nt.links.new(ang.outputs[0], m5.inputs[0])
    cs = nt.nodes.new("ShaderNodeMath")
    cs.operation = "COSINE"
    nt.links.new(m5.outputs[0], cs.inputs[0])
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = "GREATER_THAN"
    st.inputs[1].default_value = 0.2
    nt.links.new(cs.outputs[0], st.inputs[0])
    # radius: hub (<0.06) and outer lip (>0.19) are always metal
    vl = nt.nodes.new("ShaderNodeVectorMath")
    vl.operation = "LENGTH"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], vl.inputs[0])
    hub = nt.nodes.new("ShaderNodeMath")
    hub.operation = "LESS_THAN"
    hub.inputs[1].default_value = 0.06
    nt.links.new(vl.outputs["Value"], hub.inputs[0])
    lip = nt.nodes.new("ShaderNodeMath")
    lip.operation = "GREATER_THAN"
    lip.inputs[1].default_value = 0.19
    nt.links.new(vl.outputs["Value"], lip.inputs[0])
    mx1 = nt.nodes.new("ShaderNodeMath")
    mx1.operation = "MAXIMUM"
    nt.links.new(st.outputs[0], mx1.inputs[0])
    nt.links.new(hub.outputs[0], mx1.inputs[1])
    mx2 = nt.nodes.new("ShaderNodeMath")
    mx2.operation = "MAXIMUM"
    nt.links.new(mx1.outputs[0], mx2.inputs[0])
    nt.links.new(lip.outputs[0], mx2.inputs[1])
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.inputs["A"].default_value = (0.01, 0.01, 0.012, 1)
    mixc.inputs["B"].default_value = (0.75, 0.76, 0.78, 1)
    nt.links.new(mx2.outputs[0], mixc.inputs["Factor"])
    nt.links.new(mixc.outputs["Result"], p.inputs["Base Color"])
    nt.links.new(mx2.outputs[0], p.inputs["Metallic"])
    p.inputs["Roughness"].default_value = 0.22
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def build_car(location=(0, 0, 0), rot_z=0.0, body_mat=None):
    body = import_ply(CAR_DIR / "car_body.ply", "CarBody")
    wheels = import_ply(CAR_DIR / "car_wheels.ply", "CarWheels")
    body.data.materials.append(body_mat or body_material())
    m, nt, p = sc.principled("Rubber", base=(0.022, 0.022, 0.024), rough=0.7)
    wheels.data.materials.append(m)
    root = bpy.data.objects.new("Car", None)
    sc.link(root)
    rm = rim_material()
    parts = [body, wheels]
    for xw in WHEELS_X:
        for side in (-1, 1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.212, depth=0.014,
                                                location=(xw, side * RIM_Y, WHEEL_Z), rotation=(math.pi / 2, 0, 0))
            r = bpy.context.active_object
            r.data.materials.append(rm)
            bpy.ops.object.shade_smooth()
            parts.append(r)
    for o in parts:
        o.parent = root
    root.location = location
    root.rotation_euler[2] = rot_z
    return root, body, wheels
