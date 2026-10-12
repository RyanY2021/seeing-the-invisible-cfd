import sys
sys.path.append(r"D:\Creative\CFD Intro\.venv\Lib\site-packages")
sys.path.insert(0, r"D:\Creative\CFD Intro\src")
import numpy as np
print("numpy", np.__version__, np.__file__)
import warp as wp
wp.config.kernel_cache_dir = r"D:\Creative\CFD Intro\cache\warp"
wp.init()
import openvdb as vdb
a = np.zeros((64,64,64), np.float32); a[20:40,20:40,20:40] = 1.0
g = vdb.FloatGrid(); g.copyFromArray(a); g.name = "density"
print("active", g.activeVoxelCount())
try:
    g.saveFloatAsHalf = True; print("half via attr")
except Exception as e: print("no saveFloatAsHalf attr", e)
print([m for m in dir(g) if not m.startswith('_')][:80])
vdb.write(r"D:\Creative\CFD Intro\cache\probe.vdb", grids=[g])
import os; print(os.path.getsize(r"D:\Creative\CFD Intro\cache\probe.vdb"))
