"""Shared Blender helpers (render setup, materials, camera rigs). Import from shot scripts."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"D:\Creative\CFD Intro")


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    return scn


def setup_cycles(scn, samples=128, res=(1920, 1080), denoise=True, adaptive=0.02, bounces=(4, 2, 2)):
    scn.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    scn.cycles.device = "GPU"
    scn.cycles.samples = samples
    scn.cycles.use_adaptive_sampling = adaptive > 0
    if adaptive > 0:
        scn.cycles.adaptive_threshold = adaptive
    scn.cycles.use_denoising = denoise
    try:
        scn.cycles.denoiser = "OPTIX"
    except Exception:
        pass
    scn.cycles.max_bounces = bounces[0]
    scn.cycles.diffuse_bounces = min(bounces[0], 3)
    scn.cycles.glossy_bounces = min(bounces[0], 3)
    scn.cycles.transmission_bounces = bounces[0]
    scn.cycles.volume_bounces = bounces[1]
    scn.cycles.transparent_max_bounces = 8
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_depth = "16"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.use_persistent_data = True
    try:
        scn.view_settings.view_transform = "AgX"
        scn.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scn.view_settings.look = "Medium High Contrast"
        except Exception:
            pass
    return scn


def world_color(scn, color=(0.0, 0.0, 0.0), strength=1.0):
    w = bpy.data.worlds.new("World")
    scn.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg is None:
        bg = w.node_tree.nodes.new("ShaderNodeBackground")
        out = w.node_tree.nodes.get("World Output") or w.node_tree.nodes.new("ShaderNodeOutputWorld")
        w.node_tree.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength
    return w


def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def principled(name, base=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emission=None, emission_strength=0.0, alpha=1.0,
               transmission=0.0, ior=1.45, coat=0.0, spec=0.5):
    m, nt, out = new_material(name)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["IOR"].default_value = ior
    if "Transmission Weight" in p.inputs:
        p.inputs["Transmission Weight"].default_value = transmission
    if "Coat Weight" in p.inputs:
        p.inputs["Coat Weight"].default_value = coat
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = spec
    if emission is not None:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = emission_strength
    p.inputs["Alpha"].default_value = alpha
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m, nt, p


def emission_mat(name, color, strength):
    m, nt, out = new_material(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    return m


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_camera(name="Cam", lens=50.0, sensor=36.0, dof=None, clip=(0.01, 100.0)):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = sensor
    cd.clip_start, cd.clip_end = clip
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    if dof:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = dof
    return cam


def target_empty(name, loc):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def track_to(obj, target_obj):
    c = obj.constraints.new("TRACK_TO")
    c.target = target_obj
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return c


def key_loc(obj, frame, loc, interp="BEZIER"):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def smooth_keys(obj, interp="BEZIER", easing="AUTO"):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    try:
        curves = ad.action.fcurves
    except AttributeError:
        # Blender 5 layered actions
        curves = []
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    curves.extend(cb.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.easing = easing


def add_light(name, ltype, loc, energy, color=(1, 1, 1), size=0.1, target=None, spot_size=None, blend=0.3):
    ld = bpy.data.lights.new(name, ltype)
    ld.energy = energy
    ld.color = color
    if ltype == "AREA":
        ld.size = size
    elif ltype in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    if ltype == "SPOT":
        ld.spot_size = spot_size or math.radians(30)
        ld.spot_blend = blend
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    if target is not None:
        look_at(ob, target)
    return ob


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def render_frames(scn, outdir, first, last, step=1):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for f in range(first, last + 1, step):
        p = outdir / f"{f:04d}.png"
        if p.exists():
            continue
        scn.frame_set(f)
        scn.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        print(f"rendered {p.name}", flush=True)
