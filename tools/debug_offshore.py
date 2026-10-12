import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\Creative\CFD Intro\blender\offshore.blend")
dg = bpy.context.evaluated_depsgraph_get()
for name in ("Ocean", "FarSea", "T0_nacelle", "T0_rotor", "Wake", "T1"):
    o = bpy.data.objects.get(name)
    if o is None:
        print(name, "missing"); continue
    oe = o.evaluated_get(dg)
    bb = [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    print(f"{name:12s} loc={tuple(round(c,1) for c in o.matrix_world.translation)} bbox min={tuple(round(c,1) for c in mn)} max={tuple(round(c,1) for c in mx)}")
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent and o.parent.name == "T0_nacelle":
        print("nacelle child", o.name, tuple(round(c,1) for c in o.matrix_world.translation))
