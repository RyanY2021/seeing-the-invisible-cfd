"""S03 — the Navier-Stokes equations, term by term, for a general audience.

python shot_s03_equations.py bg      -> cache/s03_bg/####.npy  (faint drifting-fluid background, 2D LBM)
python shot_s03_equations.py render  -> renders/S03/####.png
"""
from __future__ import annotations

import sys

import numpy as np

from common import FPS, H, W, cache_dir, save_png16, shot_dir, smoothstep

DUR = 22.0
NFRAMES = int(DUR * FPS) + 24  # + handles
BGW, BGH = 960, 540

# (key, latex, label shown when highlighted)
TERMS = [
    ("dudt", r"$\dfrac{\partial \mathbf{u}}{\partial t}$", "how the velocity changes"),
    ("plus1", r"$+$", None),
    ("adv", r"$(\mathbf{u}\cdot\nabla)\,\mathbf{u}$", "the flow carries itself along"),
    ("eq", r"$=$", None),
    ("press", r"$-\,\dfrac{1}{\rho}\,\nabla p$", "pressure pushes"),
    ("plus2", r"$+$", None),
    ("visc", r"$\nu\,\nabla^{2}\mathbf{u}$", "viscosity smooths it out"),
    ("plus3", r"$+$", None),
    ("force", r"$\mathbf{f}$", "outside forces, like gravity"),
]
MASS = r"$\nabla\cdot\mathbf{u}\;=\;0$"

# timeline (seconds, shot-local)
T_INTRO = (0.3, 3.2)
T_EQ_IN = 3.0
T_NEWTON = (5.2, 8.2)
BEATS = [("dudt", 8.2), ("adv", 9.6), ("press", 11.0), ("visc", 12.4), ("force", 13.8), ("mass", 15.2)]
BEAT_LEN = 1.4
T_HARD = (16.8, 19.4)
T_PRIZE = (19.4, 22.6)


def bg():
    from lbm2d import LBM2D, Scalar

    out = cache_dir("s03_bg")
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:BGH, 0:BGW].astype(np.float32)
    # smooth random vortices
    ux = np.zeros_like(xx)
    uy = np.zeros_like(xx)
    for _ in range(40):
        cx, cy = rng.uniform(0, BGW), rng.uniform(0, BGH)
        r = rng.uniform(25, 70)
        g = rng.choice([-1, 1]) * rng.uniform(0.6, 1.0) * 0.035
        dx = (xx - cx + BGW / 2) % BGW - BGW / 2
        dy = (yy - cy + BGH / 2) % BGH - BGH / 2
        e = np.exp(-(dx * dx + dy * dy) / (2 * r * r))
        ux += -g * dy / r * e
        uy += g * dx / r * e
    s = LBM2D(BGW, BGH, 0.002, u_init=(ux, uy), periodic_x=True, periodic_y=True, inlet=False, csmag=0.1,
              sponge_frac=0)
    c0 = 0.5 + 0.5 * np.sin(xx / 37.0 + 2 * np.sin(yy / 53.0)) * np.cos(yy / 41.0)
    C = Scalar(s, c0.astype(np.float32))
    for f in range(NFRAMES):
        for k in range(10):
            s.step()
            if k % 2:
                C.advect(2.0)
        np.save(out / f"{f:04d}.npy", C.numpy().astype(np.float16))
    print("bg done")


def math_layer(tex, size_px, color=(1, 1, 1)):
    """Render mathtext to a float RGBA array tightly cropped."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams["mathtext.fontset"] = "cm"
    dpi = 200
    fig = plt.figure(figsize=(12, 3), dpi=dpi)
    fig.patch.set_alpha(0)
    t = fig.text(0.5, 0.5, tex, fontsize=size_px * 72 / dpi * 2, ha="center", va="center", color="white")
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba()).astype(np.float32) / 255.0
    plt.close(fig)
    a = buf[..., 3]
    ys, xs = np.nonzero(a > 0.01)
    pad = 6
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, a.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, a.shape[1])
    a = a[y0:y1, x0:x1]
    import cv2

    a = cv2.resize(a, (max(1, (x1 - x0) // 2), max(1, (y1 - y0) // 2)), interpolation=cv2.INTER_AREA)
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = color
    rgba[..., 3] = a
    return rgba


def ramp(t, a, b, fade=0.45):
    """1 inside [a,b] with soft fades."""
    return float(smoothstep(a, a + fade, t) * (1 - smoothstep(b - fade, b, t)))


def render(first=0, last=NFRAMES):
    import cv2

    from look import filmic, gblur, vignette
    from textfx import FONT_CAPTION, FONT_CAPTION_IT, FONT_LABEL, paste, text_layer

    dst = shot_dir("S03")
    bgsrc = cache_dir("s03_bg")
    SIZE = 84
    layers = {k: (math_layer(tex, SIZE), lab) for k, tex, lab in TERMS}
    mass = math_layer(MASS, SIZE)
    gapx = 26
    widths = [layers[k][0].shape[1] for k, _, _ in TERMS]
    total = sum(widths) + gapx * (len(TERMS) - 1)
    x = (W - total) / 2
    eq_y = H * 0.42
    pos = {}
    for (k, _, _), w in zip(TERMS, widths):
        pos[k] = x + w / 2
        x += w + gapx
    mass_y = eq_y + 175
    # pre-rendered captions
    cap = lambda s, size=40, it=False, col=(0.93, 0.93, 0.95): text_layer(s, size, FONT_CAPTION_IT if it else FONT_CAPTION,
                                                                         color=col)
    intro = cap("Air, water, blood — every fluid obeys the same rules.", 44)
    title = text_layer("THE NAVIER–STOKES EQUATIONS", 26, FONT_LABEL, tracking=0.35, color=(0.80, 0.82, 0.86))
    years = text_layer("1822 – 1845", 22, FONT_LABEL, tracking=0.3, color=(0.55, 0.58, 0.63))
    newton = cap("Newton’s  F = ma,  for every drop of fluid", 38, it=True)
    lab_acc = text_layer("ACCELERATION", 22, FONT_LABEL, tracking=0.3, color=(1.0, 0.82, 0.55))
    lab_frc = text_layer("FORCES", 22, FONT_LABEL, tracking=0.3, color=(0.62, 0.82, 1.0))
    beat_caps = {k: cap(lab, 38, it=True, col=(1.0, 0.88, 0.70)) for k, _, lab in TERMS if lab}
    beat_caps["mass"] = cap("and nothing is ever created or lost", 38, it=True, col=(1.0, 0.88, 0.70))
    hard = cap("Beautiful — but almost impossible to solve by hand.", 44)
    prize1 = cap("Even proving that smooth solutions always exist", 32, col=(0.75, 0.77, 0.82))
    prize2 = cap("is an open $1,000,000 Millennium Prize problem.", 32, col=(0.75, 0.77, 0.82))
    vig = vignette(H, W, 0.5)
    left_keys = ("dudt", "plus1", "adv")
    right_keys = ("press", "plus2", "visc", "plus3", "force")
    for f in range(first, last):
        t = f / FPS - 0.5  # 12-frame head handle
        # ---- background: dim drifting fluid
        c = np.load(bgsrc / f"{min(f, NFRAMES - 1):04d}.npy").astype(np.float32)
        c = cv2.resize(c, (W, H), interpolation=cv2.INTER_CUBIC)
        c = gblur(c, 3)
        gx = cv2.Sobel(c, cv2.CV_32F, 1, 0, ksize=3)
        shade = np.clip(0.5 + 0.9 * gx, 0, 1)
        base = np.array([0.010, 0.013, 0.020], np.float32)
        tint = np.array([0.030, 0.045, 0.070], np.float32)
        canvas = base + (c * 0.6 + shade * 0.4)[..., None] * tint
        # ---- equation
        eq_on = smoothstep(T_EQ_IN, T_EQ_IN + 1.6, t) * (1 - smoothstep(22.0, 22.8, t))
        # which term is highlighted
        hl = None
        for k, t0 in BEATS:
            if t0 <= t < t0 + BEAT_LEN:
                hl = k
        newton_on = ramp(t, *T_NEWTON)
        dim_amt = 0.0
        if hl is not None:
            dim_amt = 0.68
        zoom = 1.0 + 0.04 * smoothstep(0, DUR, t)
        for k, _, _ in TERMS:
            lay = layers[k][0]
            o = eq_on
            col_mul = np.array([1, 1, 1], np.float32)
            if hl is not None:
                beat_t0 = dict(BEATS)[hl]
                fade = smoothstep(beat_t0, beat_t0 + 0.25, t) * (1 - smoothstep(beat_t0 + BEAT_LEN - 0.25, beat_t0 + BEAT_LEN, t))
                if k == hl:
                    col_mul = np.array([1.0, 0.86, 0.62]) * fade + (1 - fade) * col_mul
                else:
                    o *= 1 - dim_amt * fade
            if newton_on > 0:
                if k in left_keys:
                    col_mul = col_mul * (1 - newton_on) + np.array([1.0, 0.86, 0.62]) * newton_on
                elif k in right_keys:
                    col_mul = col_mul * (1 - newton_on) + np.array([0.70, 0.86, 1.0]) * newton_on
            L = lay.copy()
            L[..., :3] *= col_mul
            # soft blur-in while appearing
            if eq_on < 0.999:
                L[..., 3] = gblur(L[..., 3], 6 * (1 - eq_on))
            cx = W / 2 + (pos[k] - W / 2) * zoom
            paste(canvas, L, cx, eq_y, opacity=o, anchor="cm")
        # mass equation
        mo = smoothstep(T_EQ_IN + 0.8, T_EQ_IN + 2.4, t) * (1 - smoothstep(22.0, 22.8, t))
        M = mass.copy()
        if hl is not None:
            beat_t0 = dict(BEATS)[hl]
            fade = smoothstep(beat_t0, beat_t0 + 0.25, t) * (1 - smoothstep(beat_t0 + BEAT_LEN - 0.25, beat_t0 + BEAT_LEN, t))
            if hl == "mass":
                M[..., :3] *= np.array([1.0, 0.86, 0.62]) * fade + (1 - fade)
            else:
                mo *= 1 - dim_amt * fade
        paste(canvas, M, W / 2, mass_y, opacity=mo, anchor="cm")
        # glow under the equation
        # ---- labels
        to = ramp(t, T_EQ_IN + 0.6, 16.6, 0.8)
        paste(canvas, title, W / 2, eq_y - 165, opacity=to, anchor="cm")
        paste(canvas, years, W / 2, eq_y - 127, opacity=to * 0.9, anchor="cm")
        if newton_on > 0:
            lx = (pos["dudt"] + pos["adv"]) / 2
            rx = (pos["press"] + pos["force"]) / 2
            paste(canvas, lab_acc, lx, eq_y + 84, opacity=newton_on, anchor="ct")
            paste(canvas, lab_frc, rx, eq_y + 84, opacity=newton_on, anchor="ct")
            paste(canvas, newton, W / 2, H * 0.82, opacity=newton_on, anchor="cm")
        if hl is not None:
            beat_t0 = dict(BEATS)[hl]
            fade = smoothstep(beat_t0, beat_t0 + 0.3, t) * (1 - smoothstep(beat_t0 + BEAT_LEN - 0.3, beat_t0 + BEAT_LEN, t))
            capl = beat_caps[hl]
            paste(canvas, capl, W / 2, H * 0.82, opacity=fade, anchor="cm")
            # underline bar under highlighted term
            if hl != "mass":
                lw = layers[hl][0].shape[1]
                xx0 = int(W / 2 + (pos[hl] - W / 2) * zoom - lw / 2)
                ybar = int(eq_y + 76)
                prog = smoothstep(beat_t0, beat_t0 + 0.5, t)
                canvas[ybar:ybar + 2, xx0:xx0 + int(lw * prog)] += 0.55 * fade * np.array([1.0, 0.8, 0.5])
            else:
                lw = mass.shape[1]
                xx0 = int(W / 2 - lw / 2)
                ybar = int(mass_y + 36)
                prog = smoothstep(beat_t0, beat_t0 + 0.5, t)
                canvas[ybar:ybar + 2, xx0:xx0 + int(lw * prog)] += 0.55 * fade * np.array([1.0, 0.8, 0.5])
        paste(canvas, intro, W / 2, H * 0.5, opacity=ramp(t, *T_INTRO, 0.6), anchor="cm")
        paste(canvas, hard, W / 2, H * 0.82, opacity=ramp(t, *T_HARD, 0.5), anchor="cm")
        po = ramp(t, *T_PRIZE, 0.6)
        paste(canvas, prize1, W / 2, H * 0.84, opacity=po, anchor="cm")
        paste(canvas, prize2, W / 2, H * 0.84 + 44, opacity=po, anchor="cm")
        rgb = filmic(canvas * vig, exposure=1.0) if False else np.clip(canvas * vig, 0, 1)
        save_png16(dst / f"{f:04d}.png", rgb)
        if f % 96 == 0:
            print("render", f, flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("bg", "all"):
        bg()
    if mode in ("render", "all"):
        a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
        render(a, b)
