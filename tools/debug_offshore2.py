import bpy, openvdb
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\Creative\CFD Intro\blender\offshore.blend")
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type in ("MESH",):
        oe = o.evaluated_get(dg)
        bb = [oe.matrix_world @ Vector(c) for c in oe.bound_box]
        zmax = max(v.z for v in bb); zmin = min(v.z for v in bb)
        if zmin > 120:
            print("HIGH", o.name, "parent", o.parent.name if o.parent else None, "zmin", round(zmin,1), "loc", tuple(round(c,1) for c in o.matrix_world.translation))
g = openvdb.read(r"D:\Creative\CFD Intro\cache\wake_vdb\wake_0060.vdb", "density")
print("wake minmax", g.evalMinMax(), "active", g.activeVoxelCount(), "bbox", g.evalActiveVoxelBoundingBox())
w = bpy.data.objects["Wake"]
print("wake matrix", [tuple(round(c,2) for c in r) for r in w.matrix_world])
