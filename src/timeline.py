"""Edit decision list, shared by the compositor and the music (72 BPM, 4/4 -> 1 bar = 3.333 s).

Each entry: shot id, edit start/end (seconds), source frame dir, source frame for edit-start, transition-in.
"""
BPM = 72.0
BAR = 4 * 60.0 / BPM  # 3.3333 s


def b(n):
    return n * BAR


# (id, start, end, render_dir, src_frame_at_start, src_fps_scale, transition_in_seconds, caption_key)
SHOTS = [
    ("S01", b(0), b(6), "S01", 1, 1.0, 0.0),          # incense + title (Blender frames are 1-based)
    ("S03", b(6), b(13), "S03", 12, 1.0, 1.2),        # equations (frame 12 == shot-local t=0)
    ("S04", b(13), b(17), "S04", 1, 1.0, 0.8),        # mesh
    ("S05", b(17), b(20), "S05", 1, 1.0, 0.6),        # cell
    ("S06", b(20), b(24), "S06", 60, 1.0, 0.8),       # vortex street (from rest)
    ("S07", b(24), b(26), "S07", 20, 1.0, 0.5),       # resolution
    ("S08", b(26), b(30), "S08", 10, 1.0, 0.8),       # Kelvin-Helmholtz clouds
    ("S09", b(30), b(32), "S09", 0, 1.0, 0.6),        # RANS / LES / DNS
    ("S10", b(32), b(34), "S10", 6, 1.0, 0.5),        # wing
    ("S11", b(34), b(36), "S11", 1, 1.0, 0.4),        # car
    ("S12", b(36), b(38), "S12", 1, 1.0, 0.4),        # offshore
    ("S13", b(38), b(40), "S13", 1, 1.0, 0.4),        # weather
    ("S14", b(40), b(42), "S14", 1, 1.0, 0.4),        # blood
    ("S15", b(42), b(46.2), "S15", 1, 1.0, 1.0),      # close + end title
]
END = b(46.2) + 1.0  # short black tail

# on-screen captions (edit time in, out, text, style)
CAPTIONS = [
    (2.0, 5.6, "A ribbon of smoke.", "cap"),
    (6.2, 9.4, "Smooth at first…", "cap"),
    (9.8, 13.0, "…then, suddenly, chaos.", "cap"),
    (b(13) + 0.6, b(13) + 4.6, "So we let a computer solve them — piece by piece.", "cap"),
    (b(13) + 5.2, b(17) - 0.4, "①  Divide space into millions of tiny cells.", "step"),
    (b(17) + 0.4, b(20) - 0.3, "②  In every cell, keep the balance.", "step"),
    (b(20) + 0.4, b(22) + 1.0, "③  Step forward in time — thousands of times.", "step"),
    (b(22) + 1.6, b(24) - 0.3, "From simple local rules, the whole flow emerges.", "cap"),
    (b(24) + 0.3, b(26) - 0.3, "Finer cells reveal more — at a higher cost.", "cap"),
    (b(26) + 0.6, b(28) - 0.2, "The hardest part: turbulence.", "cap"),
    (b(28) + 0.3, b(30) - 0.3, "Swirls within swirls — from kilometres down to millimetres.", "cap"),
    (b(30) + 0.3, b(32) - 0.3, "Too many to compute them all — so the smallest are modelled.", "cap"),
    (b(32) + 0.6, b(34) - 0.3, "Wings that lift us", "app"),
    (b(34) + 0.5, b(36) - 0.3, "Cars that slip through the air", "app"),
    (b(36) + 0.5, b(38) - 0.3, "Turbines standing in the sea", "app"),
    (b(38) + 0.5, b(40) - 0.3, "Tomorrow’s weather", "app"),
    (b(40) + 0.5, b(42) - 0.3, "The blood in our veins", "app"),
]
TITLE = (b(4) + 0.2, b(6) - 0.3)        # main title over the smoke
END_TITLE = (b(44) + 0.3, b(46.2) - 0.2)
