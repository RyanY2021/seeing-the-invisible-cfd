"""Shared staging for V01's end / V02: two edge-lit acrylic block stacks flank the incense stick; Clawd climbs the
right stack (V01) and leaps across the smoke plume to the left one (V02). The V02 smoke simulation uses the same
path for its moving obstacle, so the swirls match Clawd's body exactly. Metres, Blender world axes."""
TABLE = -0.10
BLOCK_H = 0.0425
N_BLOCKS = 2
BLOCK_TOP = TABLE + N_BLOCKS * BLOCK_H          # -0.015
XR, XL = 0.075, -0.075
Y = -0.004
UNIT = 0.005                                    # Clawd voxel unit (body 6 cm wide, 3 cm deep, 5 cm tall)
T_OFF, T_LAND = 60, 96                          # V02 local frames: take-off, landing (= bar 8 downbeat)
APEX = 0.032
STEPS_PER_FRAME = 64                            # V02 sim time runs 64/24 = 2.7x the V01 plume


def feet(f):
    """Clawd root (feet centre) at V02 frame f (float)"""
    if f <= T_OFF:
        return (XR, Y, BLOCK_TOP)
    if f >= T_LAND:
        return (XL, Y, BLOCK_TOP)
    s = (f - T_OFF) / (T_LAND - T_OFF)
    return (XR + (XL - XR) * s, Y, BLOCK_TOP + 4 * APEX * s * (1 - s))


def body_box(f):
    """centre and half-extents of Clawd's body (legs included, arms ignored)"""
    x, y, z = feet(f)
    return (x, y, z + 0.025), (6 * UNIT, 3 * UNIT, 0.025)
