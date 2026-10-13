"""The v2 incense set (V01 look, all neon on): table, tubes, rim lights, acrylic block stacks, stick + smoke.
Used by V02 / V03 / V25 / V26 (V01 builds the same set itself, with the switch-on animation)."""
import math

import bpy

import props
import scene_common as sc
import studio as st
import v02_path as vp

TABLE = vp.TABLE


import os
HAZE = float(os.environ.get("V2_HAZE", "0.0"))      # real haze volume is 4x slower; src/grade.py fakes it
STEP = float(os.environ.get("V2_VSTEP", "1.0"))


def build(scn, smoke_dir=None, prefix="incense", frame_offset=-1, n_files=560, haze=None, stacks=True,
          dens=150.0, samples=64, key_left=False):
    haze = HAZE if haze is None else haze
    st.setup_render(scn, "cycles", samples)
    scn.cycles.volume_step_rate = STEP
    scn.cycles.volume_max_steps = 1024
    st.neon_studio(scn, haze=haze, z0=TABLE, tubes=None, lights=False, floor_rough=0.15)
    tubes = dict(
        mag=st.neon_tube([(-0.30, 0.55, TABLE), (-0.30, 0.55, 0.26)], st.MAGENTA, 34.0, name="NeonMag"),
        cya=st.neon_tube([(0.06, 0.62, 0.17), (0.40, 0.62, 0.17)], st.CYAN, 30.0, name="NeonCyan"),
        vio=st.neon_tube([(-0.18, 0.75, TABLE + 0.035), (0.30, 0.75, TABLE + 0.035)], st.VIOLET, 22.0,
                         name="NeonVio"))
    lights = dict(
        rim_m=sc.add_light("RimMag", "SPOT", (-0.42, 0.42, 0.10), 45.0, color=st.MAGENTA, size=0.04,
                           target=(0, 0, 0.09), spot_size=math.radians(40), blend=0.6),
        rim_c=sc.add_light("RimCyan", "SPOT", (0.44, 0.40, 0.16), 40.0, color=st.CYAN, size=0.04,
                           target=(0, 0, 0.12), spot_size=math.radians(40), blend=0.6),
        top=sc.add_light("Top", "SPOT", (0.04, 0.22, 0.75), 5.0, color=(0.9, 0.85, 1.0), size=0.06,
                         target=(0, 0, 0.2), spot_size=math.radians(35), blend=0.7),
        key=st.strip_softbox((0.18, -0.10, 0.12), size=(0.35, 0.04), energy=1.2, color=(1.0, 0.80, 0.70),
                             target=(0.06, 0, TABLE + 0.02), name="ClawdKey", visible=False))
    if key_left:      # Clawd on the left tower (V03, V25, V26) is outside the right-hand key strip
        kl = sc.add_light("ClawdKeyL", "AREA", (vp.XL - 0.10, -0.16, vp.BLOCK_TOP + 0.09), 2.2, color=(1.0, 0.82, 0.72),
                          size=0.12, target=(vp.XL, vp.Y, vp.BLOCK_TOP + 0.025))
        kl.data.specular_factor = 0.15
        lights["key_l"] = kl
    if stacks:
        for side, x, col in (("R", vp.XR, st.CYAN), ("L", vp.XL, st.MAGENTA)):
            props.block_stack(x, TABLE, n=vp.N_BLOCKS, h=vp.BLOCK_H, edge_color=col, name=f"Stack{side}")
    props.incense_stick(base_z=TABLE)
    smoke, vol, mat = props.incense_smoke(dens=dens, fall=1.5, color=(0.9, 0.9, 0.95), anisotropy=0.6,
                                          frame_offset=frame_offset, n_files=n_files)
    if smoke_dir is not None:
        vol.filepath = str(smoke_dir / f"{prefix}_0000.vdb")
    return dict(tubes=tubes, lights=lights, smoke=smoke, vol=vol, mat=mat)


def camera(lens=50.0, dof=5.6, focus=None):
    cam = sc.add_camera(lens=lens, dof=dof, clip=(0.02, 30))
    tgt = sc.target_empty("CamTarget", (0, 0, 0))
    sc.track_to(cam, tgt)
    if focus is not None:
        cam.data.dof.focus_object = focus
    else:
        cam.data.dof.focus_object = tgt

    def key(f, loc, t):
        cam.location = loc
        cam.keyframe_insert("location", frame=f)
        tgt.location = t
        tgt.keyframe_insert("location", frame=f)

    return cam, tgt, key


def render(scn, mode, shot, first, last, test_step=None, clawd_obj=None, n=None):
    out = sc.ROOT / ("cache/lookdev_v2" if mode == "test" else f"renders/{shot}")
    out.mkdir(parents=True, exist_ok=True)
    if mode != "test" and clawd_obj is not None:
        clawd_obj.export_track(scn, out / "clawd_track.json", 1, n or last)
    step = test_step or (max(1, (last - first) // 3) if mode == "test" else 1)
    for f in range(first, last + 1, step):
        p = out / (f"{shot}_{f:04d}.exr" if mode == "test" else f"{f:04d}.exr")
        if p.exists() and mode != "test":
            continue
        scn.frame_set(f)
        scn.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
