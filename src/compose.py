"""Final edit: assemble shots (src/timeline.py), captions, titles, overlays, grain -> ffmpeg (H.264 + AAC).

python compose.py [--draft] [--start S] [--end S] [--out name.mp4]
  --draft : 960x540 quick preview, missing frames shown as labelled placeholders
"""
from __future__ import annotations

import argparse
import subprocess
import sys

import cv2
import numpy as np

from common import AUDIO, FPS, H, OUTPUT, RENDERS, CACHE, ffmpeg_exe, smoothstep
from look import bloom, gblur
from textfx import FONT_CAPTION, FONT_CAPTION_IT, FONT_LABEL, FONT_TITLE, paste, text_layer
import timeline as TL

W = 1920
BLOOM_SHOTS = {"S04": 0.35, "S05": 0.45, "S13": 0.2, "S14": 0.3}


class FrameSource:
    def __init__(self, shot):
        self.dir = RENDERS / shot
        self.files = sorted(self.dir.glob("*.png")) if self.dir.exists() else []
        self.idx = {int(p.stem): p for p in self.files}
        self.cache = {}

    def get(self, n):
        if not self.idx:
            return None
        if n not in self.idx:
            keys = np.array(sorted(self.idx))
            n = int(keys[np.argmin(np.abs(keys - n))])
        if n in self.cache:
            return self.cache[n]
        a = cv2.imread(str(self.idx[n]), cv2.IMREAD_UNCHANGED)
        scale = 65535.0 if a.dtype == np.uint16 else 255.0
        img = a[..., :3][..., ::-1].astype(np.float32) / scale
        if img.shape[1] != W:
            img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
        self.cache = {n: img}
        return img


def placeholder(name):
    img = np.full((H, W, 3), 0.03, np.float32)
    paste(img, text_layer(f"[{name} rendering…]", 40, FONT_LABEL, tracking=0.2, color=(0.6, 0.6, 0.6)), W / 2, H / 2,
          anchor="cm")
    return img


def ease(x):
    return float(smoothstep(0, 1, x))


# ---------------------------------------------------------------- text assets
_cache = {}


def T(key, *a, **k):
    if key not in _cache:
        _cache[key] = text_layer(*a, **k)
    return _cache[key]


def shadowed(dst, layer, x, y, opacity, anchor="cm", shadow=0.55, blur=6, spread=0):
    """Paste `layer` over a soft dark halo; `spread` (px) fattens thin strokes so text stays legible over bright smoke."""
    if opacity <= 0.003:
        return
    sh = layer.copy()
    sh[..., :3] = 0
    pad = blur * 3 + spread
    big = np.zeros((sh.shape[0] + 2 * pad, sh.shape[1] + 2 * pad, 4), np.float32)
    big[pad:-pad, pad:-pad] = sh
    if spread:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * spread + 1, 2 * spread + 1))
        big[..., 3] = np.clip(gblur(cv2.dilate(big[..., 3], k), blur) * 1.2, 0, 1)
    else:
        big[..., 3] = gblur(big[..., 3], blur) * 1.4
    hh, ww = layer.shape[:2]
    ox = {"c": ww / 2, "l": 0, "r": ww}[anchor[0]]
    oy = {"m": hh / 2, "t": 0, "b": hh}[anchor[1]]
    paste(dst, big, x - ox - pad + 2, y - oy - pad + 3, opacity=opacity * shadow, anchor="lt")
    paste(dst, layer, x, y, opacity=opacity, anchor=anchor)


def caption_alpha(t, t0, t1, fade=0.55):
    return ease((t - t0) / fade) * (1 - ease((t - (t1 - fade)) / fade))


def caption_band(img, t):
    a = 0.0
    for (t0, t1, text, style, label) in TL.CAPTIONS:
        if style in ("cap", "eq") and t0 - 0.6 <= t <= t1 + 0.6:
            a = max(a, caption_alpha(t, t0 - 0.3, t1 + 0.3, 0.6))
    if a > 0:
        g = np.clip((np.arange(H, dtype=np.float32) - H * 0.70) / (H * 0.30), 0, 1) ** 1.4
        img *= (1 - 0.55 * a * g)[:, None, None]


def draw_captions(img, t):
    for (t0, t1, text, style, label) in TL.CAPTIONS:
        if not (t0 - 0.1 <= t <= t1 + 0.1):
            continue
        a = caption_alpha(t, t0, t1)
        rise = (1 - ease((t - t0) / 0.8)) * 10
        if style == "capL":
            lay = T(("capL", text), text, 46, FONT_CAPTION_IT, color=(0.95, 0.95, 0.96))
            shadowed(img, lay, 150, H * 0.56 + rise, a, anchor="lm")
            continue
        if style == "cap":
            lay = T(("cap", text), text, 44, FONT_CAPTION, color=(0.95, 0.95, 0.96))
            y = H - 118 + rise
            shadowed(img, lay, W / 2, y, a)
            if label:
                lab = T(("lab", label), label, 21, FONT_LABEL, tracking=0.42, color=(1.0, 0.80, 0.50))
                shadowed(img, lab, W / 2, y - 50, a)
        elif style == "eq":
            parts = [("what flows ", (0.93, 0.93, 0.95)), ("in", (1.0, 0.66, 0.28)), ("  −  what flows ", (0.93, 0.93, 0.95)),
                     ("out", (0.45, 0.8, 1.0)), ("  =  what changes", (0.93, 0.93, 0.95))]
            lays = [T(("eq", s_, c), s_, 38, FONT_CAPTION_IT, color=c) for s_, c in parts]
            tw = sum(L.shape[1] for L in lays) - 6 * (len(lays) - 1)
            x = W / 2 - tw / 2
            y = H - 62 + rise
            for L in lays:
                shadowed(img, L, x, y, a, anchor="lm")
                x += L.shape[1] - 6
        elif style == "app":
            lay = T(("app", text), text, 54, FONT_CAPTION_IT, color=(0.97, 0.97, 0.98))
            x0, y = 120, H - 132 + rise
            # soft elliptical scrim so light backgrounds (sea, sky) keep the caption legible
            if "_scrim" not in _cache:
                yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                e = ((xx - 420) / 760.0) ** 2 + ((yy - (H - 150)) / 190.0) ** 2
                _cache["_scrim"] = np.clip(1 - e, 0, 1) ** 1.6
            img *= (1 - 0.55 * a * _cache["_scrim"])[..., None]
            shadowed(img, lay, x0, y, a, anchor="lm", shadow=0.6)
            if label:
                lab = T(("lab", label), label, 20, FONT_LABEL, tracking=0.42, color=(1.0, 0.82, 0.55))
                shadowed(img, lab, x0 + 2, y - 52, a, anchor="lm")
                # thin rule
                wl = int(60 * ease((t - t0) / 0.9))
                if wl > 0:
                    yy = int(y - 78)
                    img[yy:yy + 2, x0 + 2:x0 + 2 + wl] = img[yy:yy + 2, x0 + 2:x0 + 2 + wl] * (1 - a) + a * np.array([1.0, 0.82, 0.55])


def draw_title(img, t, t0, t1, main, sub, y=H * 0.47, x=140, size=52, align="l", halo=0):
    if not (t0 <= t <= t1):
        return
    a = caption_alpha(t, t0, t1, 0.9)
    if ("title", main, size) not in _cache:
        ls_ = [text_layer(line, size, FONT_TITLE, tracking=0.26, color=(0.97, 0.97, 0.98)) for line in main.split(chr(10))]
        wmax = max(L.shape[1] for L in ls_)
        lh = int(size * 1.25)
        stack = np.zeros((lh * (len(ls_) - 1) + ls_[-1].shape[0], wmax, 4), np.float32)
        for i, L in enumerate(ls_):
            x_ = 0 if align == "l" else (wmax - L.shape[1]) // 2
            stack[i * lh:i * lh + L.shape[0], x_:x_ + L.shape[1]] = np.maximum(stack[i * lh:i * lh + L.shape[0], x_:x_ + L.shape[1]], L)
        _cache[("title", main, size)] = stack
    big = _cache[("title", main, size)]
    s_ = 1.0 + 0.03 * (1 - ease((t - t0) / 3.0))
    if abs(s_ - 1) > 1e-3:
        big = cv2.resize(big, (int(big.shape[1] * s_), int(big.shape[0] * s_)), interpolation=cv2.INTER_LINEAR)
    blur = 6 * (1 - ease((t - t0) / 1.2))
    if blur > 0.3:
        big = big.copy()
        big[..., 3] = gblur(big[..., 3], blur)
    anc = "lm" if align == "l" else "cm"
    shadowed(img, big, x, y, a, anchor=anc, shadow=0.5 + 0.35 * bool(halo), blur=10, spread=halo)
    nl = main.count(chr(10))
    subl = T(("sub", sub, size), sub, 34 if size >= 56 else 30, FONT_CAPTION_IT, color=(0.86, 0.88, 0.92))
    a2 = caption_alpha(t, t0 + 0.9, t1, 0.9)
    shadowed(img, subl, x + (4 if align == "l" else 0), y + big.shape[0] / 2 + 34, a2, anchor=anc,
             shadow=0.55 + 0.3 * bool(halo), blur=6 + 2 * bool(halo), spread=halo // 2)
    # thin rule under the title
    if align == "l":
        wl = int(220 * ease((t - t0 - 0.5) / 1.2))
        if wl > 0:
            yy = int(y + big.shape[0] / 2 + 6)
            img[yy:yy + 1, x + 4:x + 4 + wl] = img[yy:yy + 1, x + 4:x + 4 + wl] * (1 - a) + a * np.array([0.8, 0.82, 0.86])


def overlays(img, shot, local_t, src_frame):
    if shot == "S06":
        meta = np.load(CACHE / "s06" / "meta.npz")
        steps = meta["steps"]
        n = int(steps[min(max(src_frame, 0), len(steps) - 1)])
        a = caption_alpha(local_t, 0.6, 13.0, 0.6)
        lab = T(("lab", "TIME STEP"), "TIME STEP", 18, FONT_LABEL, tracking=0.4, color=(0.75, 0.78, 0.82))
        num = text_layer(f"{n:,}", 34, FONT_LABEL, tracking=0.08, color=(0.95, 0.95, 0.96))
        paste(img, lab, W - 90, 70, opacity=a, anchor="rm")
        paste(img, num, W - 90, 108, opacity=a, anchor="rm")
    if shot == "S04":
        cells = 11_304_960 * ease((local_t - 1.0) / 7.5) ** 2
        a = caption_alpha(local_t, 1.0, 13.0, 0.6)
        lab = T(("lab", "CELLS"), "CELLS", 18, FONT_LABEL, tracking=0.4, color=(0.70, 0.86, 1.0))
        num = text_layer(f"{int(cells):,}", 34, FONT_LABEL, tracking=0.08, color=(0.95, 0.97, 1.0))
        paste(img, lab, W - 90, 70, opacity=a, anchor="rm")
        paste(img, num, W - 90, 108, opacity=a, anchor="rm")


def shot_frame(sources, entry, t, draft):
    sid, start, end, rdir, src0, _, _ = entry
    local = t - start
    n = src0 + int(round(local * FPS))
    src = sources[rdir]
    img = src.get(n)
    if img is None:
        return placeholder(sid), n
    img = img.copy()
    if sid in BLOOM_SHOTS and not draft:
        img = bloom(img, threshold=0.55, strength=BLOOM_SHOTS[sid], sigmas=(4, 12, 32))
    overlays(img, sid, local, n)
    return img, n


def build_frame(sources, t, draft, grain_rng):
    shots = TL.SHOTS
    cur = None
    for i, e in enumerate(shots):
        if e[1] <= t < e[2]:
            cur = i
    if cur is None:
        return np.zeros((H, W, 3), np.float32)
    e = shots[cur]
    img, _ = shot_frame(sources, e, t, draft)
    # crossfade from the previous shot over the transition length (previous shot continues past its end)
    tr = e[6]
    if cur > 0 and tr > 0 and t < e[1] + tr:
        prev = shots[cur - 1]
        pimg, _ = shot_frame(sources, prev, t, draft)
        a = ease((t - e[1]) / tr)
        img = pimg * (1 - a) + img * a
    # fade from black at the very start, to black at the end
    if t < 1.2:
        img = img * ease(t / 1.2)
    if t > TL.SHOTS[-1][2] - 2.0:
        img = img * (1 - ease((t - (TL.SHOTS[-1][2] - 2.0)) / 2.0))
    caption_band(img, t)
    draw_captions(img, t)
    draw_title(img, t, *TL.TITLE, "SEEING THE" + chr(10) + "INVISIBLE", "an introduction to Computational Fluid Dynamics", y=H * 0.42, x=130, size=60)
    draw_title(img, t, *TL.END_TITLE, "COMPUTATIONAL FLUID DYNAMICS", "seeing the invisible — before it is built", y=H * 0.5, x=W / 2, size=60, align="c", halo=8)
    # end credit (small, under the end title)
    c0, c1 = TL.END_TITLE[0] + 1.6, TL.END_TITLE[1]
    if c0 <= t <= c1:
        ca = caption_alpha(t, c0, c1, 0.8)
        lines = [("THE SMOKE, VORTICES AND CLOUDS IN THIS FILM WERE SIMULATED", 17, FONT_LABEL, 0.32, (0.80, 0.82, 0.86)),
                 ("lattice-Boltzmann and vortex-method solvers written for this film  ·  real NOAA GFS winds of 12 Oct 2026",
                  20, FONT_CAPTION_IT, 0.0, (0.66, 0.68, 0.72)),
                 ("Earth imagery NASA  ·  skies Poly Haven (CC0)  ·  original music generated in code",
                  20, FONT_CAPTION_IT, 0.0, (0.66, 0.68, 0.72))]
        for i, (txt, sz, fnt, trk, col) in enumerate(lines):
            lay = T(("cred", txt), txt, sz, fnt, tracking=trk, color=col)
            shadowed(img, lay, W / 2, H * 0.80 + i * 32, ca, anchor="cm", shadow=0.7, blur=5, spread=3)
    # film grain (luma), stronger in shadows
    if not draft:
        g = grain_rng.standard_normal((H // 2, W // 2)).astype(np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        lum = img.mean(-1, keepdims=True)
        img = img + g[..., None] * 0.010 * (1.2 - lum)
    return np.clip(img, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=TL.END)
    ap.add_argument("--out", default=None)
    ap.add_argument("--still", type=float, default=None, help="write a single PNG at this time")
    args = ap.parse_args()
    sources = {e[3]: FrameSource(e[3]) for e in TL.SHOTS}
    rng = np.random.default_rng(1)
    if args.still is not None:
        img = build_frame(sources, args.still, args.draft, rng)
        cv2.imwrite(str(CACHE / f"still_{args.still:06.2f}.jpg"), (img[..., ::-1] * 255).astype(np.uint8),
                    [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / (args.out or ("draft.mp4" if args.draft else "Seeing_the_Invisible_CFD.mp4"))
    ow, oh = (960, 540) if args.draft else (W, H)
    audio = AUDIO / "score.wav"
    cmd = [ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le" if not args.draft else "rgb24", "-s", f"{ow}x{oh}",
           "-r", str(FPS), "-i", "-"]
    if audio.exists():
        cmd += ["-ss", f"{args.start:.3f}", "-t", f"{args.end - args.start:.3f}", "-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", "slow" if not args.draft else "veryfast", "-crf", "15" if not args.draft else "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if audio.exists():
        cmd += ["-c:a", "aac", "-b:a", "256k", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-shortest"]
    cmd += [str(out)]
    print(" ".join(cmd))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n0, n1 = int(args.start * FPS), int(args.end * FPS)
    for k in range(n0, n1):
        t = k / FPS
        img = build_frame(sources, t, args.draft, rng)
        if args.draft:
            img = cv2.resize(img, (ow, oh), interpolation=cv2.INTER_AREA)
            p.stdin.write((img * 255 + 0.5).astype(np.uint8).tobytes())
        else:
            # ordered dither to 16-bit (keeps gradients smooth through the 8-bit encode)
            p.stdin.write((img * 65535 + 0.5).astype(np.uint16).tobytes())
        if k % 240 == 0:
            print(f"t={t:.1f}s", flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
