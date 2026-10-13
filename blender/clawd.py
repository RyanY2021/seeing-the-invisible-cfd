"""Clawd — the orange pixel critter of the Claude Code welcome banner — as a glossy voxel figure,
plus pixel-art acting helpers (hop, walk, look, blink, wave, ...). Import from shot scripts:

    import clawd
    c = clawd.Clawd(unit=0.004, location=(0, 0, 0))
    c.hop(10, 22, (0, 0, 0), (0.05, 0, 0))
    c.look(30, +1); c.blink(40); c.wave(50, 74, side="R")

The banner (block characters, each = 2x2 'pixels' of aspect 1:2):
     ▐▛███▜▌
    ▝▜█████▛▘
      ▘▘ ▝▝
decodes to an 18 x 5 sprite. One sprite pixel = a 1 (wide) x 2 (tall) voxel column; depth is built from 1x1 cubes.
Units: x right, z up, Clawd faces -y (towards a camera on the -y side). 1 unit = `unit` metres.
"""
import math

import bmesh
import bpy
from mathutils import Vector

ORANGE = (0.693, 0.184, 0.095)       # #D97757 (Claude orange) in linear RGB
ORANGE_DEEP = (0.72, 0.15, 0.055)    # rendered base: a touch deeper so it survives coloured light + tone mapping

# sprite rows top -> bottom, columns 0..17
BODY = [(r, c) for r in range(4) for c in range(3, 15)]
EYES = [(1, 5), (1, 12)]
ARM_L = [(2, 1), (2, 2)]
ARM_R = [(2, 15), (2, 16)]
LEGS = [(4, 4), (4, 6), (4, 11), (4, 13)]
BODY_DEPTH = 6
ARM_DEPTH = 4
LEG_DEPTH = 2


def _xz(r, c):
    """lower-left corner (x, z) of sprite pixel (row r, col c); sprite centred on x = 0, feet at z = 0."""
    return c - 9.0, (4 - r) * 2.0


def _bevel_box(bm, x0, y0, z0, sx, sy, sz, bevel):
    """add an axis-aligned box with chamfered edges to bmesh bm"""
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res["verts"]
    for v in verts:
        v.co = Vector((x0 + (v.co.x + 0.5) * sx, y0 + (v.co.y + 0.5) * sy, z0 + (v.co.z + 0.5) * sz))
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=2, profile=0.6, affect="EDGES")


def _part_mesh(name, pixels, depth, origin, bevel, eye=False):
    bm = bmesh.new()
    for (r, c) in pixels:
        x, z = _xz(r, c)
        if eye:
            # a flush black pixel, a hair proud of the face so it reads from every angle
            _bevel_box(bm, x + 0.04, -BODY_DEPTH / 2 - 0.06, z + 0.06, 0.92, 0.5, 1.88, bevel * 0.6)
            continue
        for k in range(depth):
            _bevel_box(bm, x, -depth / 2 + k, z, 1.0, 1.0, 2.0, bevel)
    ox, oy, oz = origin
    for v in bm.verts:
        v.co -= Vector((ox, oy, oz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


def materials(style="glossy"):
    """body + eye materials. style: glossy (lacquered toy plastic) | acrylic (candy-like, light passes through)"""
    def mat(name):
        m = bpy.data.materials.get(name)
        if m:
            return m, None
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        return m, m.node_tree.nodes["Principled BSDF"]

    body, p = mat(f"ClawdBody_{style}")
    if p is not None:
        p.inputs["Base Color"].default_value = (*ORANGE_DEEP, 1)
        p.inputs["Roughness"].default_value = 0.32
        p.inputs["Coat Weight"].default_value = 0.7
        p.inputs["Coat Roughness"].default_value = 0.06
        p.inputs["Subsurface Weight"].default_value = 0.08
        p.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.15)
        p.inputs["Subsurface Scale"].default_value = 0.0015
        if style == "acrylic":
            p.inputs["Transmission Weight"].default_value = 0.55
            p.inputs["Roughness"].default_value = 0.12
            p.inputs["IOR"].default_value = 1.49
            p.inputs["Thin Film Thickness"].default_value = 380.0
            p.inputs["Thin Film IOR"].default_value = 1.4
    eye, p = mat("ClawdEye")
    if p is not None:
        p.inputs["Base Color"].default_value = (0.004, 0.003, 0.006, 1)
        p.inputs["Roughness"].default_value = 0.45          # stays black even when it faces a bright sky
        p.inputs["Specular IOR Level"].default_value = 0.25
        p.inputs["Coat Weight"].default_value = 0.25
        p.inputs["Coat Roughness"].default_value = 0.2
    return body, eye


class Clawd:
    def __init__(self, name="Clawd", unit=0.004, location=(0, 0, 0), rotation_z=0.0, style="glossy", bevel=0.09,
                 collection=None):
        self.name = name
        self.unit = unit
        col = collection or bpy.context.scene.collection
        body_m, eye_m = materials(style)

        def obj(n, data=None, parent=None, loc=(0, 0, 0)):
            o = bpy.data.objects.new(f"{name}_{n}", data)
            col.objects.link(o)
            if parent is not None:
                o.parent = parent
            o.location = loc
            return o

        # root: placement (metres), uniform unit scale. squash: squash & stretch pivot at the feet.
        self.root = obj("root")
        self.root.empty_display_size = 0.02
        self.root.location = location
        self.root.rotation_euler = (0, 0, rotation_z)
        self.root.scale = (unit, unit, unit)
        self.squash = obj("squash", parent=self.root)
        # body: origin at its bottom centre (z = 2 units above the feet)
        me = _part_mesh(f"{name}_body", BODY, BODY_DEPTH, (0, 0, 2.0), bevel)
        me.materials.append(body_m)
        self.body = obj("body", me, self.squash, (0, 0, 2.0))
        # eyes (children of the body)
        self.eyes = []
        for i, px in enumerate(EYES):
            x, z = _xz(*px)
            me = _part_mesh(f"{name}_eye{i}", [px], 1, (x + 0.5, 0, z + 1.0), bevel, eye=True)
            me.materials.append(eye_m)
            self.eyes.append(obj(f"eye{i}", me, self.body, (x + 0.5, 0, z + 1.0 - 2.0)))
        self.eye_home = [e.location.copy() for e in self.eyes]
        # arms: pivot at the shoulder (inner edge of the arm, middle of the row)
        self.arms = {}
        for side, px, sx in (("L", ARM_L, -6.0), ("R", ARM_R, 6.0)):
            me = _part_mesh(f"{name}_arm{side}", px, ARM_DEPTH, (sx, 0, 5.0), bevel)
            me.materials.append(body_m)
            self.arms[side] = obj(f"arm{side}", me, self.body, (sx, 0, 5.0 - 2.0))
        # legs: pivot at the hip (top of the leg), children of the squash pivot (they stay planted when the body bobs)
        self.legs = []
        for i, px in enumerate(LEGS):
            x, z = _xz(*px)
            me = _part_mesh(f"{name}_leg{i}", [px], LEG_DEPTH, (x + 0.5, 0, 2.0), bevel)
            me.materials.append(body_m)
            self.legs.append(obj(f"leg{i}", me, self.squash, (x + 0.5, 0, 2.0)))
        self.leg_home = [l.location.copy() for l in self.legs]
        self.parts = [self.root, self.squash, self.body, *self.eyes, *self.arms.values(), *self.legs]
        self.cues = []                     # (frame, kind) -> sound / bubble cues for the compositor
        self._key_all(1)

    # ------------------------------------------------------------------ keyframing primitives
    @staticmethod
    def _interp(kind):
        bpy.context.preferences.edit.keyframe_new_interpolation_type = kind

    def _k(self, ob, path, frame, value=None, interp="BEZIER"):
        self._interp(interp)
        if value is not None:
            setattr(ob, path, value)
        ob.keyframe_insert(path, frame=frame)
        self._interp("BEZIER")

    def _key_all(self, frame):
        for o in self.parts:
            for path in ("location", "rotation_euler", "scale"):
                o.keyframe_insert(path, frame=frame)

    def place(self, frame, loc, rot_z=None, interp="BEZIER"):
        self._k(self.root, "location", frame, Vector(loc), interp)
        if rot_z is not None:
            self._k(self.root, "rotation_euler", frame, (0, 0, rot_z), interp)

    def squash_to(self, frame, sz, interp="BEZIER"):
        """volume-preserving squash (sz < 1) / stretch (sz > 1)"""
        sxy = 1.0 / math.sqrt(sz)
        self._k(self.squash, "scale", frame, (sxy, sxy, sz), interp)

    # ------------------------------------------------------------------ acting
    def hop(self, f0, f1, start, end, height=None, squash=0.72, stretch=1.18, anticip=4, settle=6, cue=True):
        """jump from start to end (metres, world), taking off at f0 and landing at f1."""
        start, end = Vector(start), Vector(end)
        h = height if height is not None else 6.0 * self.unit
        mid = (f0 + f1) / 2
        self.place(f0 - anticip, start)
        self.squash_to(f0 - anticip, 1.0)
        self.squash_to(f0, squash)                          # crouch
        self.place(f0, start)
        self.squash_to(f0 + 2, stretch)                     # launch
        self.place(mid, (start + end) / 2 + Vector((0, 0, h)))
        self.squash_to(mid, 1.0)
        self.squash_to(f1 - 1, stretch * 0.95)
        self.place(f1, end)
        self.squash_to(f1, squash)                          # land
        self.squash_to(f1 + settle // 2, 1.06)
        self.squash_to(f1 + settle, 1.0)
        for side, a in (("L", 1), ("R", -1)):               # arms fly up in the air
            arm = self.arms[side]
            self._k(arm, "rotation_euler", f0, (0, 0, 0))
            self._k(arm, "rotation_euler", mid, (0, a * math.radians(35), 0))
            self._k(arm, "rotation_euler", f1 + settle, (0, 0, 0))
        if cue:
            self.cues.append((f0, "hop"))
            self.cues.append((f1, "land"))

    def walk(self, f0, f1, start, end, step=3):
        """patter from start to end: legs alternate on a 1/16-note grid (3 frames at 120 BPM), body bobs."""
        start, end = Vector(start), Vector(end)
        self.place(f0, start, interp="LINEAR")
        self.place(f1, end, interp="LINEAR")
        lift = 0.6
        for i, leg in enumerate(self.legs):
            home = self.leg_home[i]
            for j, f in enumerate(range(f0, f1 + 1, step)):
                up = (j + i) % 2 == 0 and f < f1
                self._k(leg, "location", f, home + Vector((0, 0, lift if up else 0.0)), "CONSTANT")
        for j, f in enumerate(range(f0, f1 + 1, step)):
            self._k(self.body, "location", f, Vector((0, 0, 2.0 + (0.25 if j % 2 else 0.0))), "CONSTANT")
        self._k(self.body, "location", f1 + step, Vector((0, 0, 2.0)), "CONSTANT")
        self.cues.append((f0, "walk"))

    def look(self, frame, dx=0, dz=0):
        """eyes slide by whole pixels (dx in sprite pixels, dz in half-rows)"""
        for e, home in zip(self.eyes, self.eye_home):
            self._k(e, "location", frame, home + Vector((dx, 0, dz)), "CONSTANT")

    def blink(self, frame, dur=3):
        for e in self.eyes:
            self._k(e, "scale", frame - 1, (1, 1, 1), "CONSTANT")
            self._k(e, "scale", frame, (1, 1, 0.12), "CONSTANT")
            self._k(e, "scale", frame + dur, (1, 1, 1), "CONSTANT")

    def eyes_scale(self, frame, s=(1, 1, 1), interp="CONSTANT"):
        for e in self.eyes:
            self._k(e, "scale", frame, s, interp)

    def surprise(self, frame, hold=18):
        self.eyes_scale(frame - 1, (1, 1, 1))
        self.eyes_scale(frame, (1.0, 1, 1.45))
        self.eyes_scale(frame + hold, (1, 1, 1))
        self.squash_to(frame - 1, 1.0)
        self.squash_to(frame + 2, 1.12)
        self.squash_to(frame + 6, 1.0)
        self.cues.append((frame, "surprise"))

    def wave(self, f0, f1, side="R", period=8, amp=55.0):
        arm = self.arms[side]
        a = 1 if side == "L" else -1
        self._k(arm, "rotation_euler", f0, (0, 0, 0))
        f = f0 + period // 2
        up = True
        while f < f1:
            self._k(arm, "rotation_euler", f, (0, a * math.radians(amp if up else amp * 0.45), 0))
            f += period // 2
            up = not up
        self._k(arm, "rotation_euler", f1, (0, 0, 0))
        self.cues.append((f0, "wave"))

    def arm(self, frame, side, deg, interp="BEZIER"):
        a = 1 if side == "L" else -1
        self._k(self.arms[side], "rotation_euler", frame, (0, a * math.radians(deg), 0), interp)

    def tilt(self, frame, deg, interp="BEZIER"):
        """lean sideways (rotation about the viewing axis), pivot at the feet"""
        self._k(self.squash, "rotation_euler", frame, (0, math.radians(deg), 0), interp)

    def turn(self, frame, rot_z, interp="BEZIER"):
        self._k(self.root, "rotation_euler", frame, (0, 0, rot_z), interp)

    def breathe(self, f0, f1, period=24, amt=0.03):
        """idle: a gentle beat-synced bob of the body"""
        for j, f in enumerate(range(f0, f1 + 1, period // 2)):
            self._k(self.body, "scale", f, (1, 1, 1 + (amt if j % 2 else 0.0)))

    def say(self, frame, text, dur=36):
        """speech bubble cue for the compositor (drawn in 2D, anchored above Clawd's head)"""
        self.cues.append((frame, f"say:{dur}:{text}"))

    # ------------------------------------------------------------------ export for the compositor
    def head_world(self):
        return self.body.matrix_world @ Vector((0, 0, 9.0))

    def export_track(self, scn, path, first, last):
        """per-frame screen position (pixels) of the head top + apparent size, and the action cues -> json"""
        import json
        from bpy_extras.object_utils import world_to_camera_view
        cam = scn.camera
        rx = scn.render.resolution_x
        ry = scn.render.resolution_y
        frames = {}
        for f in range(first, last + 1):
            scn.frame_set(f)
            p = world_to_camera_view(scn, cam, self.head_world())
            p2 = world_to_camera_view(scn, cam, self.body.matrix_world @ Vector((6.0, 0, 9.0)))
            frames[f] = [p.x * rx, (1 - p.y) * ry, p.z, abs(p2.x - p.x) * rx / 6.0]
        with open(path, "w") as fh:
            json.dump({"frames": frames, "cues": sorted(self.cues, key=lambda c: c[0])}, fh)


def _voxel_vert_count(bevel):
    """vertices per bevelled voxel box (all boxes in a part mesh are built identically)"""
    bm = bmesh.new()
    _bevel_box(bm, 0, 0, 0, 1, 1, 2, bevel)
    n = len(bm.verts)
    bm.free()
    return n


def add_explode(c, amount=0.6, bevel=0.09):
    """shape key 'explode' on Clawd's body: every voxel flies outward from the body centre (pixel burst).
    Arms and legs get location offsets keyed by explode_key(). Returns the body shape key."""
    me = c.body.data
    nv = _voxel_vert_count(bevel)
    if not me.shape_keys:
        c.body.shape_key_add(name="Basis", from_mix=False)
    sk = c.body.shape_key_add(name="explode", from_mix=False)
    import numpy as np
    co = np.array([v.co[:] for v in me.vertices])
    centre = np.array([0.0, 0.0, 4.0])                       # body-local centre (body origin at its bottom)
    rng = np.random.default_rng(1)
    for i in range(0, len(co), nv):
        vc = co[i:i + nv].mean(0)
        off = (vc - centre) * amount + rng.normal(0, 0.35, 3)
        for k in range(i, min(i + nv, len(co))):
            sk.data[k].co = Vector(co[k] + off)
    return sk


def explode_key(c, sk, frame, value, interp="BEZIER"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    sk.value = value
    sk.keyframe_insert("value", frame=frame)
    for side, s in (("L", -1), ("R", 1)):
        arm = c.arms[side]
        base = Vector((s * 6.0, 0, 3.0))
        arm.location = base + Vector((s * 3.0 * value, 0, 1.0 * value))
        arm.keyframe_insert("location", frame=frame)
    for i, leg in enumerate(c.legs):
        leg.location = c.leg_home[i] + Vector((c.leg_home[i].x * 0.25 * value, 0, -1.5 * value))
        leg.keyframe_insert("location", frame=frame)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
