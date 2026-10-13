"""Glowing flow streaks for Blender: particles traced through a velocity field (precomputed in numpy), drawn each
frame as camera-facing ribbons from head to tail (a frame_change handler rewrites one mesh), with a per-vertex
colour attribute 'scol' and a 'sfade' attribute (fades the tail).

    S = Streaks("Flow", trace(...), material)      # trace -> heads[f, n, 3], tails[f, n, 3], alive[f, n], col[n, 3]
"""
import bpy
import numpy as np

import scene_common as sc

_REG = []


def trace(vel, seed_fn, n, frames, dt_frame=1 / 24, substeps=4, tail_frames=5, spawn_every=None, life=None, rng=None):
    """vel(p[N,3]) -> v[N,3] (m/s); seed_fn(k, rng) -> positions [k,3] for (re)spawned particles.
    Particles respawn when they leave (seed_fn decides) or after `life` frames.
    Returns heads, tails (frames+1, n, 3) and alive (frames+1, n)."""
    rng = rng or np.random.default_rng(1)
    p = seed_fn(n, rng)
    age = rng.integers(0, life or 10 ** 6, n) if life else np.zeros(n, int)
    hist = np.zeros((frames + 1 + tail_frames, n, 3), np.float32)
    alive = np.ones((frames + 1 + tail_frames, n), bool)
    born = np.zeros(n, int)
    for f in range(frames + 1 + tail_frames):
        hist[f] = p
        h = dt_frame / substeps
        for _ in range(substeps):
            k1 = vel(p)
            k2 = vel(p + 0.5 * h * k1)
            p = p + h * k2
        age += 1
        dead = ~np.isfinite(p).all(1)
        if hasattr(seed_fn, "outside"):
            dead |= seed_fn.outside(p)
        if life:
            dead |= age > life
        if dead.any():
            p[dead] = seed_fn(int(dead.sum()), rng)
            age[dead] = 0
            born[dead] = f + 1
            hist_mask = np.zeros(n, bool)
            hist_mask[dead] = True
        # tails must not jump across a respawn: remember birth frame per particle per frame
        alive[f] = True
        if f == 0:
            births = np.zeros((frames + 1 + tail_frames, n), int)
        births[f] = born
    heads = hist[tail_frames:]
    tails = np.empty_like(heads)
    for f in range(heads.shape[0]):
        ft = f                    # index in hist of the tail
        tails[f] = hist[ft]
        # if the particle was born after the tail time, clamp the tail to its birth position
        b = births[f + tail_frames]
        late = b > ft
        if late.any():
            idx = np.clip(b[late], 0, hist.shape[0] - 1)
            tails[f][late] = hist[idx, np.nonzero(late)[0]]
    return heads, tails


class Streaks:
    def __init__(self, name, heads, tails, material, width=0.0015, colors=None, cam=None, frame0=1, fade=None):
        self.heads, self.tails = heads, tails
        self.n = heads.shape[1]
        self.width = width
        self.cam = cam
        self.frame0 = frame0
        self.colors = colors if colors is not None else np.ones((self.n, 3), np.float32)
        self.fade = fade                                      # optional fn(frame) -> per particle alpha [n]
        me = bpy.data.meshes.new(name)
        n = self.n
        verts = np.zeros((4 * n, 3), np.float32)
        faces = np.arange(4 * n).reshape(n, 4)
        me.from_pydata(verts.tolist(), [], faces.tolist())
        me.attributes.new("scol", "FLOAT_COLOR", "POINT")
        me.attributes.new("sfade", "FLOAT", "POINT")
        self.ob = bpy.data.objects.new(name, me)
        sc.link(self.ob)
        self.ob.data.materials.append(material)
        self.ob.visible_shadow = False
        _REG.append(self)
        self.update(bpy.context.scene.frame_current)

    def update(self, frame):
        f = int(np.clip(frame - self.frame0, 0, self.heads.shape[0] - 1))
        h, t = self.heads[f], self.tails[f]
        d = h - t
        if self.cam is not None:
            view = h - np.array(self.cam.matrix_world.translation)
        else:
            view = np.tile(np.array([0, 1.0, 0]), (self.n, 1))
        side = np.cross(d, view)
        nrm = np.linalg.norm(side, axis=1, keepdims=True)
        side = np.where(nrm > 1e-9, side / np.maximum(nrm, 1e-9), np.array([0, 0, 1.0]))
        w = self.width * 0.5
        v = np.empty((self.n, 4, 3), np.float32)
        v[:, 0] = t - side * w * 0.3
        v[:, 1] = t + side * w * 0.3
        v[:, 2] = h + side * w
        v[:, 3] = h - side * w
        me = self.ob.data
        me.vertices.foreach_set("co", v.reshape(-1))
        col = np.ones((self.n, 4, 4), np.float32)
        col[..., :3] = self.colors[:, None, :]
        me.attributes["scol"].data.foreach_set("color", col.reshape(-1))
        fd = np.empty((self.n, 4), np.float32)
        fd[:, 0:2] = 0.0
        fd[:, 2:4] = 1.0
        if self.fade is not None:
            fd *= self.fade(frame)[:, None]
        me.attributes["sfade"].data.foreach_set("value", fd.reshape(-1))
        me.update()


def _handler(scene, depsgraph=None):
    for s in _REG:
        s.update(scene.frame_current)


def register():
    if _handler not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(_handler)


def streak_material(name="StreakMat", strength=6.0, base=(0.6, 0.9, 1.0)):
    """emission = per-vertex colour x fade (tail -> head), additive-looking (transparent blend)"""
    m, nt, out = sc.new_material(name)
    m.surface_render_method = "BLENDED"
    ac = nt.nodes.new("ShaderNodeAttribute")
    ac.attribute_name = "scol"
    af = nt.nodes.new("ShaderNodeAttribute")
    af.attribute_name = "sfade"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(ac.outputs["Color"], em.inputs["Color"])
    s = nt.nodes.new("ShaderNodeMath")
    s.operation = "MULTIPLY"
    s.inputs[1].default_value = strength
    nt.links.new(af.outputs["Fac"], s.inputs[0])
    nt.links.new(s.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m
