"""v2 edit: graded EXR shots (timeline_v2) + beat-aligned transitions + bouncy captions + Clawd bubbles + grain
-> ffmpeg (H.264, 16-bit input, AAC 48 kHz).

  python compose_v2.py                    full film  -> output/Seeing_the_Invisible_CFD_v2.mp4
  python compose_v2.py --draft            half-res, fast encode -> output/draft_v2.mp4
  python compose_v2.py --bars 22 50       only a bar range (draft or full)
  python compose_v2.py --still 37.5       one PNG at bar 37.5 -> cache/v2/stills/
Missing shot frames become labelled placeholders, so the edit can be previewed before everything is rendered.
"""
import argparse
import json
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import grade as G  # noqa: E402
import textfx_v2 as TX  # noqa: E402
import timeline_v2 as TL  # noqa: E402
from common import AUDIO, CACHE, OUTPUT, RENDERS, ffmpeg_exe  # noqa: E402

W, H = 1920, 1080
GRADE_DEFAULT = dict(exposure=0.0, bloom_strength=0.08, bloom_threshold=1.0, sat=1.25, contrast=1.0, ca=1.2, vig=0.22)
STARTS = {s[0]: s[1] * TL.BAR for s in TL.SHOTS}
SHOT = {s[0]: s for s in TL.SHOTS}


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ sources
@lru_cache(maxsize=None)
def track(sid):
    p = RENDERS / sid / "clawd_track.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return {int(k): v for k, v in d["frames"].items()}, d["cues"]


def placeholder(sid, k):
    g = np.linspace(0.05, 0.015, H, dtype=np.float32)[:, None, None] * np.array([1.2, 0.5, 1.8], np.float32)
    img = np.ascontiguousarray(np.broadcast_to(g * 255, (H, W, 3)).astype(np.uint8))
    cv2.putText(img, f"{sid}  #{k}", (80, 140), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (150, 100, 200), 3, cv2.LINE_AA)
    cv2.putText(img, "not rendered yet", (80, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 75, 125), 2, cv2.LINE_AA)
    return img.astype(np.float32) / 255.0


def shot_image(sid, k):
    """display-space float image of shot sid, file frame k (1-based)"""
    d = RENDERS / sid
    nfr = TL.shot_frames(sid)
    k = min(max(k, 1), nfr)
    exr = d / f"{k:04d}.exr"
    if exr.exists():
        params = dict(GRADE_DEFAULT)
        params.update(SHOT[sid][4])
        return G.grade(G.read_exr(exr), **params)
    png = d / f"{k:04d}.png"
    if png.exists():
        im = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        scale = 65535.0 if im.dtype == np.uint16 else 255.0
        return im[..., ::-1].astype(np.float32) / scale
    # nearest existing frame (renders in progress) else placeholder
    for dk in range(1, 6):
        for kk in (k - dk, k + dk):
            if (d / f"{kk:04d}.exr").exists():
                return shot_image(sid, kk)
    return placeholder(sid, k)


# ------------------------------------------------------------------ transitions
def pixelate(img, block):
    if block <= 1:
        return img
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(1, w // block), max(1, h // block)), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def prism_flash(img, x):
    """additive prismatic light leak; x = frames after the cut (peaks at 0)"""
    a = np.exp(-max(x, 0) / 3.5) * (1.0 if x >= 0 else np.exp(x / 1.5))
    if a < 0.01:
        return img
    yy, xx = np.mgrid[0:H:8, 0:W:8].astype(np.float32)
    u = (xx / W + 0.6 * yy / H)
    col = np.dstack([0.5 + 0.5 * np.cos(6.28 * (u + 0.0)), 0.5 + 0.5 * np.cos(6.28 * (u + 0.33)),
                     0.5 + 0.5 * np.cos(6.28 * (u + 0.66))]).astype(np.float32)
    col = cv2.resize(col, (W, H), interpolation=cv2.INTER_LINEAR)
    return np.clip(img + a * (0.22 + 0.33 * col), 0, None)


def frame_picture(F):
    """the picture (no type) at edit frame F"""
    idx = None
    for i, s in enumerate(TL.SHOTS):
        if s[1] * TL.BAR <= F < s[2] * TL.BAR:
            idx = i
            break
    if idx is None:   # tail after the last shot: hold the last one
        s = TL.SHOTS[-1]
        return shot_image(s[0], F - s[1] * TL.BAR + 1)
    sid, b0, b1, (kind, n), _ = TL.SHOTS[idx]
    S = b0 * TL.BAR
    cur = shot_image(sid, F - S + 1)
    x = F - S
    if idx == 0 or kind == "cut" or n <= 0 or x >= n + 6:
        if kind == "fade" and idx == 0:
            return cur * smooth(x / max(n, 1))
        return cur
    prev = TL.SHOTS[idx - 1]
    t = x / n
    if kind == "flash":
        if x < n:
            p = shot_image(prev[0], F - prev[1] * TL.BAR + 1)
            w = smooth(t * 2)
            cur = p * (1 - w) + cur * w
        return prism_flash(cur, x)
    if x >= n:
        return cur
    p = shot_image(prev[0], F - prev[1] * TL.BAR + 1)
    if kind == "xfade":
        w = smooth(t)
        return p * (1 - w) + cur * w
    if kind == "pixel":
        block = int(round(1 + 38 * np.sin(np.pi * t)))
        w = 1.0 if t >= 0.5 else 0.0
        w = smooth((t - 0.35) / 0.3)
        return pixelate(p, block) * (1 - w) + pixelate(cur, block) * w
    return cur


# ------------------------------------------------------------------ type
_objs = {}


def caption_obj(i):
    if i in _objs:
        return _objs[i]
    b0, b1, style, text, ex = TL.CAPTIONS[i]
    col = TL.PALETTE.get(ex.get("color", "cyan"), TL.PALETTE["cyan"])
    if style == "cap":
        o = TX.Caption(text, y=ex.get("y", 905), x_center=ex.get("x", W / 2), maxw=ex.get("maxw", 1480))
    elif style == "label":
        o = TX.Label(text, color=col)
    elif style == "note":
        o = TX.Plain(text, size=31, weight=560, y=990, color=(240, 232, 250), pill=True)
    elif style == "sub":
        o = TX.Plain(text, size=40, weight=420, y=ex.get("y", 590), tracking=0.06, color=(240, 235, 255),
                     glow=TL.PALETTE["cyan"], pill=True)
    elif style == "formula":
        o = TX.Formula(text)
    elif style == "credit":
        o = TX.Plain(text, size=22, weight=500, y=1040, x=W - 60, align="right", color=(190, 180, 210))
    elif style == "app":
        lab, txt = text.split("|")
        o = TX.AppTitle(lab, txt, color=col if "color" in ex else TL.PALETTE["cyan"])
    elif style == "credit_block":
        o = TX.CreditBlock(text.split("|"), cx=ex.get("x", 1450), cy=ex.get("y", 560))
    else:
        o = TX.Plain(text)
    _objs[i] = o
    return o


_bubbles = {}


def draw_type(img, F):
    for i, (b0, b1, style, text, ex) in enumerate(TL.CAPTIONS):
        F0, F1 = TL.f(b0), TL.f(b1)
        if F0 <= F < F1 + 1:
            o = caption_obj(i)
            for oo in (o if isinstance(o, list) else [o]):
                oo.draw(img, F - F0, F1 - F0)
    # Clawd speech bubbles (cues exported by the Blender shot scripts)
    for s in TL.SHOTS:
        sid, b0, b1 = s[0], s[1], s[2]
        S = b0 * TL.BAR
        if not (S <= F < b1 * TL.BAR + TL.HANDLE):
            continue
        tr = track(sid)
        if tr is None:
            continue
        frames, cues = tr
        k = F - S + 1
        for cf, kind in cues:
            if not kind.startswith("say:"):
                continue
            _, dur, text = kind.split(":", 2)
            dur = int(dur)
            if cf <= k < cf + dur and k in frames:
                key = text
                if key not in _bubbles:
                    _bubbles[key] = TX.Bubble(text)
                hx, hy, hz, px = frames[k]
                if hz > 0:
                    _bubbles[key].draw(img, k - cf, dur, (hx, hy), px)


_huds = {}
_pix = None
FLAT_CLAWD = {"V18": dict(f0=1, f1=118, x=150, y=780, say=(10, 58, "why is it so hard?"))}


def draw_overlays(img, F):
    """shot-specific overlays: pixel HUD counters (hud.json) and the 2D Clawd on flat shots"""
    global _pix
    for s in TL.SHOTS:
        sid, b0, b1 = s[0], s[1], s[2]
        S = b0 * TL.BAR
        if not (S <= F < b1 * TL.BAR):
            continue
        k = F - S + 1
        hp = RENDERS / sid / "hud.json"
        if hp.exists():
            if sid not in _huds:
                d = json.loads(hp.read_text())
                _huds[sid] = (TX.PixelHUD(d["label"]), {int(a): v for a, v in d["values"].items()})
            hud, vals = _huds[sid]
            if k in vals and vals[k] > 0:
                a = min(1.0, (k - 1) / 8.0) * min(1.0, (b1 * TL.BAR - F) / 8.0)
                hud.draw(img, f"{vals[k]:,}", a=a)
        if sid in FLAT_CLAWD:
            c = FLAT_CLAWD[sid]
            if _pix is None:
                _pix = TX.PixelClawd(10)
            if c["f0"] <= k <= c["f1"]:
                t_in, t_out = k - c["f0"], c["f1"] - k
                hop = max(0.0, 1 - t_in / 10) * 80 + max(0.0, 1 - t_out / 10) * 80
                bob = 4 * np.sin(k * 0.5)
                sq = 1.0 + 0.06 * np.sin(k * 0.5)
                _pix.draw(img, c["x"], c["y"] - hop + bob, a=1.0, squash=sq)
                s0, s1, text = c["say"]
                if s0 <= k < s1:
                    key = "flat:" + text
                    if key not in _bubbles:
                        _bubbles[key] = TX.Bubble(text)
                    _bubbles[key].draw(img, k - s0, s1 - s0, (c["x"] + _pix.w * 0.5, c["y"] - hop), 10)


_grain = None


def finish(img, F):
    global _grain
    if _grain is None:
        r = np.random.default_rng(7)
        _grain = [cv2.GaussianBlur(r.standard_normal((H, W)).astype(np.float32), (0, 0), 0.7) for _ in range(12)]
    g = _grain[F % 12]
    lum = img.mean(axis=2, keepdims=True)
    amp = 0.022 * (0.35 + 0.65 * np.clip(1 - lum, 0, 1))      # more grain in the shadows, like film
    return np.clip(img + g[..., None] * amp, 0, 1)


def render_frame(F):
    img = frame_picture(F)
    img = np.ascontiguousarray(img, dtype=np.float32)
    draw_overlays(img, F)
    draw_type(img, F)
    if F >= TL.N_BARS * TL.BAR:      # fade to black in the tail
        img *= 1 - smooth((F - TL.N_BARS * TL.BAR) / (TL.TAIL_FRAMES - 4))
    return finish(img, F)


def _work(args):
    F, draft = args
    img = render_frame(F)
    if draft:
        img = cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        return (img * 255 + 0.5).astype(np.uint8).tobytes()
    return (img * 65535 + 0.5).astype(np.uint16).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--bars", type=float, nargs=2, default=None)
    ap.add_argument("--still", type=float, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--audio", default=str(AUDIO / "mix_v2.wav"))
    a = ap.parse_args()
    if a.still is not None:
        F = TL.f(a.still)
        img = render_frame(F)
        d = CACHE / "v2" / "stills"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"still_{a.still:06.2f}.jpg"
        cv2.imwrite(str(p), (img[..., ::-1] * 255 + 0.5).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 93])
        print(p)
        return
    F0, F1 = 0, TL.TOTAL
    if a.bars:
        F0, F1 = TL.f(a.bars[0]), min(TL.f(a.bars[1]), TL.TOTAL)
    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / (a.out or ("draft_v2.mp4" if a.draft else "Seeing_the_Invisible_CFD_v2.mp4"))
    ow, oh = (W // 2, H // 2) if a.draft else (W, H)
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24" if a.draft else "rgb48le",
           "-s", f"{ow}x{oh}", "-r", str(TL.FPS), "-i", "-"]
    audio = Path(a.audio)
    if not audio.exists():
        audio = AUDIO / "score_v2.wav"
    if audio.exists():
        cmd += ["-ss", f"{F0 / TL.FPS:.3f}", "-t", f"{(F1 - F0) / TL.FPS:.3f}", "-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast" if a.draft else "slow", "-crf", "22" if a.draft else "15",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if audio.exists():
        cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest"]
    cmd += [str(out)]
    print(" ".join(cmd), flush=True)
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(a.jobs) as pool:
        for i, buf in enumerate(pool.imap(_work, [(F, a.draft) for F in range(F0, F1)], chunksize=2)):
            p.stdin.write(buf)
            if (F0 + i) % 240 == 0:
                print(f"frame {F0 + i} / {F1}  (bar {(F0 + i) / TL.BAR:.1f})", flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
