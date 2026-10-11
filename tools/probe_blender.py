import bpy, sys
print("PY", sys.version)
print("Fluid modifier:", hasattr(bpy.types, "FluidModifier"))
try:
    import openvdb; print("openvdb module OK", openvdb.__file__)
except Exception as e:
    try:
        import pyopenvdb; print("pyopenvdb OK")
    except Exception as e2: print("no openvdb", e, e2)
import numpy; print("numpy", numpy.__version__)
prefs = bpy.context.preferences.addons['cycles'].preferences
for t in ('OPTIX','CUDA'):
    try:
        prefs.compute_device_type = t
        prefs.refresh_devices()
        print(t, [ (d.name, d.type) for d in prefs.devices])
    except Exception as e: print(t, "err", e)
print("engines:", [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
