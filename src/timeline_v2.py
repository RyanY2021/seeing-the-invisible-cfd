"""v2 edit: shots on the 120 BPM bar grid (1 bar = 48 frames), transitions, per-shot grade, captions, bubbles.

Every shot directory renders/<id>/ holds scene-linear EXR frames ####.exr numbered from 1; the edit frame
bar0*48 shows file `src0` (default 1). Shots render HANDLE extra frames at the end for transitions.
"""
BAR = 48            # frames per bar
FPS = 24
N_BARS = 142
TAIL_FRAMES = 2 * FPS
TOTAL = N_BARS * BAR + TAIL_FRAMES
HANDLE = 24


def f(bar, beat=0.0):
    """edit frame of a bar (+ beats, 4 per bar)"""
    return int(round(bar * BAR + beat * 12))


# id, bar0, bar1, transition-in (kind, frames), grade overrides
SHOTS = [
    ("V01", 0, 6, ("fade", 1), {"haze": 0.15}),
    ("V02", 6, 10, ("cut", 0), {"haze": 0.15}),
    ("V03", 10, 14, ("flash", 8), {"bloom_strength": 0.12, "haze": 0.15}),
    ("V04", 14, 22, ("xfade", 12), {}),
    ("V05", 22, 26, ("flash", 6), {}),
    ("V06", 26, 30, ("cut", 0), {}),
    ("V07", 30, 34, ("cut", 0), {}),
    ("V08", 34, 38, ("cut", 0), {}),
    ("V09", 38, 42, ("cut", 0), {}),
    ("V10", 42, 48, ("xfade", 12), {}),
    ("V11", 48, 50, ("cut", 0), {}),
    ("V12", 50, 54, ("flash", 6), {}),
    ("V13", 54, 60, ("pixel", 18), {}),
    ("V14", 60, 66, ("xfade", 12), {}),
    ("V15", 66, 74, ("pixel", 12), {}),
    ("V16", 74, 80, ("xfade", 24), {"bloom_strength": 0.03, "sat": 1.05, "ca": 0.6}),
    ("V17", 80, 86, ("pixel", 12), {}),
    ("V18", 86, 96, ("flash", 8), {}),
    ("V19", 96, 106, ("xfade", 12), {}),
    ("V20", 106, 112, ("pixel", 18), {}),
    ("V21", 112, 116, ("flash", 6), {}),
    ("V22", 116, 120, ("flash", 6), {}),
    ("V23", 120, 124, ("flash", 6), {}),
    ("V24", 124, 130, ("flash", 6), {}),
    ("V25", 130, 136, ("xfade", 24), {}),
    ("V26", 136, 142, ("cut", 0), {}),
]


def shot_frames(sid):
    for s in SHOTS:
        if s[0] == sid:
            return (s[2] - s[1]) * BAR + HANDLE
    raise KeyError(sid)


# captions: (bar0, bar1, style, text, extra)  style: cap | label | note | title | sub | formula | credit
CAPTIONS = [
    (1.0, 3.2, "cap", "Air is invisible…", {}),
    (3.6, 5.85, "cap", "…but it is never still.", {}),
    (8.25, 9.9, "cap", "Smoke lets us see it move — for a moment.", {}),
    (11.0, 13.4, "sub", "an introduction to Computational Fluid Dynamics", {}),
    (15.0, 17.6, "cap", "Wings, cars, turbines, storms, even our blood —", {}),
    (17.8, 19.4, "cap", "all are shaped by flows we cannot see.", {}),
    (19.6, 21.85, "cap", "To design them, we must see the flow before it is built.", {}),
    (23.0, 24.7, "cap", "It does. Follow one tiny parcel of fluid…", {}),
    (24.8, 25.85, "cap", "…and ask: what pushes it?", {}),
    (26.25, 29.85, "label", "1 · PRESSURE", {"color": "magenta"}),
    (26.5, 29.85, "cap", "Squeezed from high pressure towards low.", {}),
    (30.25, 33.85, "label", "2 · VISCOSITY", {"color": "lime"}),
    (30.5, 32.2, "cap", "Neighbouring layers drag each other along.", {}),
    (32.3, 33.85, "note", "honey: a lot  ·  air: very little", {}),
    (34.25, 37.85, "label", "3 · MOMENTUM", {"color": "cyan"}),
    (34.5, 36.0, "cap", "Once moving, it keeps going —", {}),
    (36.1, 37.85, "cap", "and the flow carries itself along.", {}),
    (38.25, 41.85, "label", "4 · CONSERVATION", {"color": "peach"}),
    (38.5, 40.0, "cap", "Fluid never appears or vanishes:", {}),
    (40.1, 41.85, "cap", "narrow the path, and it speeds up.", {}),
    (42.5, 44.8, "cap", "Together, they are the Navier–Stokes equations.", {}),
    (45.0, 47.85, "cap", "Newton's “force = mass × acceleration” — for every drop of fluid.", {}),
    (48.1, 49.9, "cap", "Easy to write. Almost impossible to solve.", {}),
    (48.6, 49.9, "note", "proving they always behave is a $1,000,000 open problem", {}),
    (51.0, 52.45, "cap", "A computer can't solve it everywhere at once…", {}),
    (52.55, 53.85, "cap", "…so it works piece by piece.", {}),
    (54.25, 59.85, "label", "STEP 1", {"color": "cyan"}),
    (54.5, 57.3, "cap", "Chop space into millions of tiny cells —", {}),
    (57.4, 59.85, "cap", "tiny where the action is, big where nothing happens.", {}),
    (60.25, 65.85, "label", "STEP 2", {"color": "cyan"}),
    (60.5, 62.3, "cap", "In every cell, balance the books:", {}),
    (62.4, 64.3, "formula", "what flows in  −  what flows out  =  what changes", {}),
    (64.4, 65.85, "cap", "Each cell only talks to its neighbours.", {}),
    (66.25, 73.85, "label", "STEP 3", {"color": "cyan"}),
    (66.5, 68.8, "cap", "Take a tiny step forward in time…", {}),
    (69.0, 71.4, "cap", "…then another. Tens of thousands of them.", {}),
    (71.6, 73.85, "cap", "Watch the swirls appear.", {}),
    (74.4, 75.65, "cap", "Nobody told the computer to make swirls —", {}),
    (75.75, 76.9, "cap", "they emerge from the rules.", {}),
    (77.1, 79.85, "cap", "And nature agrees: real clouds behind an island.", {}),
    (77.3, 79.85, "credit", "Clouds behind Alejandro Selkirk Island, Chile · Landsat 7 image: NASA/GSFC", {}),
    (80.5, 82.8, "cap", "More cells, sharper flow…", {"y": 120}),
    (83.0, 85.85, "cap", "…but halve the cell size in 3D, and the work grows 16×.", {"y": 120}),
    (87.0, 89.8, "cap", "The real challenge: turbulence.", {}),
    (90.0, 92.8, "cap", "Big swirls feed smaller swirls — down to fractions of a millimetre.", {}),
    (93.0, 95.85, "cap", "Far too many to compute them all.", {}),
    (96.4, 98.0, "cap", "So the smallest swirls are modelled, not computed —", {}),
    (98.1, 99.3, "cap", "a bit like choosing camera settings:", {}),
    (108.0, 111.85, "app", "AIRCRAFT|the swirl behind every wingtip", {}),
    (112.25, 115.85, "app", "CARS|less drag, less fuel", {}),
    (116.25, 119.85, "app", "OFFSHORE WIND|turbines standing in the waves", {}),
    (120.25, 123.85, "app", "WEATHER|tomorrow's winds, computed today", {}),
    (124.25, 128.5, "app", "MEDICINE|blood flowing through an artery", {}),
    (131.0, 133.4, "cap", "Computational Fluid Dynamics:", {"x": 1480, "y": 600, "maxw": 700}),
    (133.5, 135.85, "cap", "seeing the invisible — before it is built.", {"x": 1480, "y": 600, "maxw": 520}),
    (137.6, 141.6, "credit_block", "Simulations, renders and music: all made in code.|"
     "Lattice-Boltzmann flows on the GPU · Blender · a procedural score|with Clawd, the Claude Code critter", {}),
]

PALETTE = {  # display-space caption accents
    "magenta": (255, 79, 216), "cyan": (59, 232, 255), "violet": (138, 92, 255), "peach": (255, 158, 107),
    "lime": (198, 255, 79), "white": (255, 250, 245), "clawd": (217, 119, 87),
}
