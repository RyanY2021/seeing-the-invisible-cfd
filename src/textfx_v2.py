"""v2 on-screen type: bouncy word-by-word captions on frosted-acrylic pills with a soft neon glow,
neon labels, formulas, credits, and Clawd's pixel speech bubbles. All compositing in display space [0,1]."""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
NUNITO = str(ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
PIXEL = str(ROOT / "assets" / "fonts" / "silkscreen" / "Silkscreen-Regular.ttf")
PIXEL_B = str(ROOT / "assets" / "fonts" / "silkscreen" / "Silkscreen-Bold.ttf")
W, H = 1920, 1080


@lru_cache(maxsize=64)
def nunito(size, weight=600):
    f = ImageFont.truetype(NUNITO, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:  # noqa: BLE001
        pass
    return f


@lru_cache(maxsize=16)
def pixfont(size, bold=False):
    return ImageFont.truetype(PIXEL_B if bold else PIXEL, size)


def _rgba(text, font, color=(255, 255, 255), tracking=0.0, pad=4):
    """render text (with letter spacing in em) -> float32 RGBA (premultiplied) array"""
    asc, desc = font.getmetrics()
    if tracking == 0:
        w = int(font.getlength(text)) + 2 * pad
    else:
        w = int(sum(font.getlength(ch) + tracking * font.size for ch in text)) + 2 * pad
    h = asc + desc + 2 * pad
    im = Image.new("L", (max(w, 1), h), 0)
    d = ImageDraw.Draw(im)
    if tracking == 0:
        d.text((pad, pad), text, font=font, fill=255)
    else:
        x = pad
        for ch in text:
            d.text((x, pad), ch, font=font, fill=255)
            x += font.getlength(ch) + tracking * font.size
    a = np.asarray(im, np.float32) / 255.0
    rgb = np.array(color, np.float32) / 255.0
    return np.dstack([a[..., None] * rgb, a])


def over(dst, layer, x, y, opacity=1.0):
    """composite premultiplied RGBA layer onto dst (H,W,3) with top-left at (x,y)"""
    h, w = layer.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0 or opacity <= 0:
        return
    L = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4] * opacity
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + L[..., :3] * opacity


def add(dst, layer, x, y, opacity=1.0):
    """additive (glow)"""
    h, w = layer.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0 or opacity <= 0:
        return
    dst[y0:y1, x0:x1] += layer[y0 - y:y1 - y, x0 - x:x1 - x, :3] * opacity


def glow_of(layer, color, sigma=10, gain=1.0, pad=40):
    a = np.pad(layer[..., 3], pad)
    g = cv2.GaussianBlur(a, (0, 0), sigma) * gain
    rgb = np.array(color, np.float32) / 255.0
    return np.dstack([g[..., None] * rgb, g]), pad


def scaled(layer, s):
    if abs(s - 1) < 1e-3:
        return layer
    h, w = layer.shape[:2]
    return cv2.resize(layer, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_LINEAR)


def rounded_mask(w, h, r):
    m = np.zeros((h, w), np.float32)
    cv2.rectangle(m, (r, 0), (w - r - 1, h - 1), 1.0, -1)
    cv2.rectangle(m, (0, r), (w - 1, h - r - 1), 1.0, -1)
    for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
        cv2.circle(m, (cx, cy), r, 1.0, -1, lineType=cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), 0.8)


def acrylic_pill(frame, x, y, w, h, amount=1.0, tint=(0.10, 0.05, 0.18), border=(1.0, 0.9, 1.0)):
    """frosted acrylic panel: blur + darken what is behind it, faint tint, a thin bright top edge"""
    if amount <= 0:
        return
    x, y, w, h = int(x), int(y), int(w), int(h)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    m = rounded_mask(w, h, min(h // 2, 40))[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * amount
    reg = frame[y0:y1, x0:x1]
    pad = 30
    big = frame[max(y0 - pad, 0):min(y1 + pad, H), max(x0 - pad, 0):min(x1 + pad, W)]
    bl = cv2.GaussianBlur(big, (0, 0), 16)
    bl = bl[y0 - max(y0 - pad, 0):y0 - max(y0 - pad, 0) + (y1 - y0), x0 - max(x0 - pad, 0):x0 - max(x0 - pad, 0) + (x1 - x0)]
    acr = bl * 0.42 + np.array(tint, np.float32) * 0.55
    # top highlight + subtle vertical sheen
    hh = y1 - y0
    sheen = np.linspace(0.06, 0.0, hh, dtype=np.float32)[:, None, None]
    acr = acr + sheen
    frame[y0:y1, x0:x1] = reg * (1 - m) + acr * m
    edge = np.zeros((h, w), np.float32)
    r = min(h // 2, 40)
    cv2.rectangle(edge, (0, 0), (w - 1, h - 1), 0, -1)
    mm = rounded_mask(w, h, r)
    er = cv2.erode((mm > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    ring = np.clip(mm - er, 0, 1)
    top = np.linspace(1.0, 0.15, h, dtype=np.float32)[:, None]
    ring = (ring * top)[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    frame[y0:y1, x0:x1] += ring * 0.22 * amount * np.array(border, np.float32)


# ------------------------------------------------------------------ animation curves
def pop_curve(tau):
    """spring pop-in for a word (tau = frames since it appeared): (scale, dy, alpha)"""
    if tau < 0:
        return 0.0, 0.0, 0.0
    e = np.exp(-tau / 3.5)
    c = np.cos(0.65 * tau)
    return 1 - 0.4 * e * c, 16 * e * c, min(1.0, tau / 3.0)


def exit_curve(t_left, n=8):
    if t_left >= n:
        return 1.0, 0.0
    x = max(t_left, 0) / n
    return x * x * (3 - 2 * x), -8 * (1 - x)


# ------------------------------------------------------------------ caption objects
class Caption:
    """one timed line (or two) of bouncy words"""

    def __init__(self, text, size=46, weight=640, color=(255, 250, 245), glow=(255, 79, 216), y=905, maxw=1480,
                 pill=True, stagger=2.0, tracking=0.0, lines_gap=1.18, x_center=W / 2, align="center"):
        self.size, self.y, self.pill, self.stagger = size, y, pill, stagger
        self.x_center, self.align = x_center, align
        font = nunito(size, weight)
        words = text.split(" ")
        space = font.getlength(" ") + tracking * size
        # wrap
        lines, cur, cw = [], [], 0.0
        for wd in words:
            wl = font.getlength(wd) + tracking * size * len(wd)
            if cur and cw + space + wl > maxw:
                lines.append(cur)
                cur, cw = [], 0.0
            cur.append((wd, wl))
            cw += (space if len(cur) > 1 else 0) + wl
        lines.append(cur)
        self.words = []          # (layer, glow layer, glow pad, x, y)
        lh = size * lines_gap
        total_h = lh * len(lines)
        y0 = y - total_h / 2
        self.box = None
        for li, ln in enumerate(lines):
            lw = sum(wl for _, wl in ln) + space * (len(ln) - 1)
            x = x_center - lw / 2 if align == "center" else x_center
            for wd, wl in ln:
                lay = _rgba(wd, font, color, tracking)
                gl, gp = glow_of(lay, glow, sigma=size * 0.28, gain=0.55)
                self.words.append((lay, gl, gp, x, y0 + li * lh))
                x += wl + space
            bx0 = (x_center - lw / 2) if align == "center" else x_center
            box = (bx0, y0 + li * lh, bx0 + lw, y0 + li * lh + lh)
            self.box = box if self.box is None else (min(self.box[0], box[0]), self.box[1], max(self.box[2], box[2]),
                                                     box[3])

    def draw(self, frame, t, dur):
        """t: frames since caption start, dur: caption length in frames"""
        a_exit, dy_exit = exit_curve(dur - t)
        if self.pill and self.box is not None:
            x0, y0, x1, y1 = self.box
            padx, pady = self.size * 0.75, self.size * 0.22
            pa = min(1.0, max(t, 0) / 5.0) * a_exit
            grow = 0.94 + 0.06 * min(1.0, max(t, 0) / 6.0)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            w = (x1 - x0 + 2 * padx) * grow
            h = (y1 - y0 + 2 * pady) * grow
            acrylic_pill(frame, cx - w / 2, cy - h / 2 + dy_exit, w, h, pa)
        for i, (lay, gl, gp, x, y) in enumerate(self.words):
            s, dy, a = pop_curve(t - i * self.stagger)
            if a <= 0:
                continue
            a *= a_exit
            L = scaled(lay, s)
            G = scaled(gl, s)
            cx = x + lay.shape[1] / 2
            cy = y + lay.shape[0] / 2 + dy + dy_exit
            add(frame, G, cx - G.shape[1] / 2, cy - G.shape[0] / 2, 0.55 * a)
            over(frame, L, cx - L.shape[1] / 2, cy - L.shape[0] / 2, a)


class Label:
    """tracked caps in a neon outline pill (e.g. '① PRESSURE', 'STEP 1')"""

    def __init__(self, text, color=(59, 232, 255), y=830, size=26, x_center=W / 2):
        font = nunito(size, 850)
        self.lay = _rgba(text, font, color, tracking=0.22)
        self.gl, self.gp = glow_of(self.lay, color, sigma=8, gain=0.9)
        self.color = np.array(color, np.float32) / 255
        self.x, self.y = x_center - self.lay.shape[1] / 2, y - self.lay.shape[0] / 2

    def draw(self, frame, t, dur):
        s, dy, a = pop_curve(t)
        a_exit, dy_exit = exit_curve(dur - t)
        a *= a_exit
        if a <= 0:
            return
        h, w = self.lay.shape[:2]
        pw, ph = int(w + 36), int(h + 10)
        px, py = int(self.x + w / 2 - pw / 2), int(self.y + h / 2 - ph / 2 + dy + dy_exit)
        acrylic_pill(frame, px, py, pw, ph, a * 0.9, border=self.color * 1.5)
        L = scaled(self.lay, s)
        G = scaled(self.gl, s)
        cx, cy = self.x + w / 2, self.y + h / 2 + dy + dy_exit
        add(frame, G, cx - G.shape[1] / 2, cy - G.shape[0] / 2, 0.8 * a)
        over(frame, L, cx - L.shape[1] / 2, cy - L.shape[0] / 2, a)


class Plain:
    """static-ish text (notes, credits, subtitles): soft fade + rise"""

    def __init__(self, text, size=30, weight=500, color=(225, 215, 240), y=975, x=None, tracking=0.0, glow=None,
                 align="center", pill=False):
        self.pill = pill
        font = nunito(size, weight)
        self.lay = _rgba(text, font, color, tracking)
        self.gl = None
        if glow is not None:
            self.gl, self.gp = glow_of(self.lay, glow, sigma=size * 0.35, gain=0.7)
        w = self.lay.shape[1]
        if x is None:
            x = W / 2 - w / 2
        elif align == "right":
            x = x - w
        self.x, self.y = x, y - self.lay.shape[0] / 2

    def draw(self, frame, t, dur):
        a = min(1.0, max(t, 0) / 10.0)
        a_exit, dy_exit = exit_curve(dur - t, 10)
        a *= a_exit
        if a <= 0:
            return
        dy = 10 * (1 - min(1.0, max(t, 0) / 10.0)) ** 2 + dy_exit
        if self.pill:
            h, w = self.lay.shape[:2]
            acrylic_pill(frame, self.x - 22, self.y + dy - 2, w + 44, h + 4, a * 0.95)
        if self.gl is not None:
            add(frame, self.gl, self.x - self.gp, self.y - self.gp + dy, 0.6 * a)
        over(frame, self.lay, self.x, self.y + dy, a)


class Formula:
    """'what flows in − what flows out = what changes' with coloured terms"""

    def __init__(self, text, y=905, size=50):
        parts = [p.strip() for p in text.replace("=", "|=|").replace("−", "|−|").split("|")]
        cols = [(59, 232, 255), (255, 250, 245), (255, 79, 216), (255, 250, 245), (255, 158, 107)]
        font = nunito(size, 760)
        self.items = []
        x = 0.0
        gap = size * 0.45
        for i, p in enumerate(parts):
            col = cols[i % len(cols)]
            lay = _rgba(p, font, col)
            gl, gp = glow_of(lay, col, sigma=size * 0.3, gain=0.6)
            self.items.append([lay, gl, gp, x])
            x += lay.shape[1] + gap
        tw = x - gap
        for it in self.items:
            it[3] += W / 2 - tw / 2
        self.y = y
        self.box = (W / 2 - tw / 2, y - size * 0.6, W / 2 + tw / 2, y + size * 0.6)
        self.size = size

    def draw(self, frame, t, dur):
        a_exit, dy_exit = exit_curve(dur - t)
        x0, y0, x1, y1 = self.box
        acrylic_pill(frame, x0 - 40, y0 - 14 + dy_exit, x1 - x0 + 80, y1 - y0 + 28, min(1, max(t, 0) / 5) * a_exit)
        for i, (lay, gl, gp, x) in enumerate(self.items):
            s, dy, a = pop_curve(t - 4 * i)
            a *= a_exit
            if a <= 0:
                continue
            L, G = scaled(lay, s), scaled(gl, s)
            cx, cy = x + lay.shape[1] / 2, self.y + dy + dy_exit
            add(frame, G, cx - G.shape[1] / 2, cy - G.shape[0] / 2, 0.6 * a)
            over(frame, L, cx - L.shape[1] / 2, cy - L.shape[0] / 2, a)


class AppTitle:
    """application montage: neon tracked label + caption, lower left"""

    def __init__(self, label, text, x=110, y=930, color=(59, 232, 255)):
        self.lab = Label(label, color=color, y=y - 62, size=24, x_center=0)
        self.lab.x = x
        self.cap = Caption(text, size=50, weight=700, y=y, x_center=x, align="left", glow=color, pill=True)

    def draw(self, frame, t, dur):
        self.lab.draw(frame, t, dur)
        self.cap.draw(frame, t - 4, dur - 4)


# ------------------------------------------------------------------ Clawd's pixel speech bubble
class Bubble:
    SCALE = 3

    def __init__(self, text):
        k = self.SCALE
        font = pixfont(10 * 1, bold=True)
        tw = int(font.getlength(text))
        asc, desc = font.getmetrics()
        th = asc + desc
        pw, ph = tw + 10, th + 6
        tail = 5
        im = Image.new("RGBA", (pw + 2, ph + tail + 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ink = (26, 14, 34, 255)
        paper = (255, 248, 240, 255)
        # pixel rounded rect: 1px border, corners cut
        d.rectangle((1, 0, pw, ph), fill=ink)
        d.rectangle((0, 1, pw + 1, ph - 1), fill=ink)
        d.rectangle((2, 1, pw - 1, ph - 1), fill=paper)
        d.rectangle((1, 2, pw, ph - 2), fill=paper)
        # tail (staircase) pointing down, slightly left of centre
        cx = pw // 2 - 2
        for i in range(tail):
            d.line((cx - (tail - i) + 1, ph + i - 1, cx + 1, ph + i - 1), fill=paper)
            d.point((cx - (tail - i), ph + i - 1), fill=ink)
            d.point((cx + 2, ph + i - 1), fill=ink)
        d.point((cx + 1, ph + tail - 1), fill=ink)
        d.text((6, 3 - 1), text, font=font, fill=ink)
        a = np.asarray(im, np.float32) / 255.0
        a = cv2.resize(a, (a.shape[1] * k, a.shape[0] * k), interpolation=cv2.INTER_NEAREST)
        self.lay = np.dstack([a[..., :3] * a[..., 3:4], a[..., 3]])
        self.tail_x = (cx + 1) * k

    def draw(self, frame, t, dur, head_xy, clawd_px=None):
        steps = [0.0, 0.45, 0.8, 1.12, 1.0]
        if t < 0 or t >= dur:
            return
        s = steps[min(int(t // 3), 4)]
        tl = dur - t
        if tl < 9:
            s = [0.0, 0.5, 0.85][min(int(tl // 3), 2)]
        if s <= 0:
            return
        L = cv2.resize(self.lay, (max(1, int(self.lay.shape[1] * s)), max(1, int(self.lay.shape[0] * s))),
                       interpolation=cv2.INTER_NEAREST)
        hx, hy = head_xy
        gap = 18 if clawd_px is None else max(10, 0.6 * clawd_px)
        x = hx - self.tail_x * s
        y = hy - gap - L.shape[0]
        x = min(max(x, 30), W - 30 - L.shape[1])
        y = min(max(y, 30), H - 30 - L.shape[0])
        # drop shadow (pixel offset) for a sticker feel
        sh = L.copy()
        sh[..., :3] = 0
        over(frame, sh, x + 6, y + 6, 0.35)
        over(frame, L, x, y, 1.0)


class PixelHUD:
    """pixel-font counter for the cell world (e.g. TIME STEP 12,345)"""

    def __init__(self, label, color=(59, 232, 255)):
        self.label = label
        self.color = color
        self.font = pixfont(28, bold=True)

    def draw(self, frame, value, x=W - 80, y=70, a=1.0):
        lab = _rgba(self.label, pixfont(16), (200, 190, 230))
        num = _rgba(value, self.font, self.color)
        gl, gp = glow_of(num, self.color, sigma=6, gain=0.8)
        wbox = max(lab.shape[1], num.shape[1]) + 36
        acrylic_pill(frame, x - wbox + 14, y - 34, wbox + 4, num.shape[0] + 44, a, tint=(0.03, 0.02, 0.06))
        over(frame, lab, x - lab.shape[1], y - 26, a)
        add(frame, gl, x - num.shape[1] - gp, y - gp, 0.7 * a)
        over(frame, num, x - num.shape[1], y, a)


SPRITE = ["   ############   ",
          "   ##.######.##   ",
          " ################ ",
          "   ############   ",
          "    # #    # #    "]


class PixelClawd:
    """2D Clawd sprite (banner pixels, 1:2) for the flat shots"""

    def __init__(self, px=10):
        h, w = len(SPRITE) * 2 * px, len(SPRITE[0]) * px
        lay = np.zeros((h, w, 4), np.float32)
        orange = np.array([217, 119, 87], np.float32) / 255
        dark = np.array([0.03, 0.02, 0.04], np.float32)
        for r, row in enumerate(SPRITE):
            for c, ch in enumerate(row):
                if ch == " ":
                    continue
                col = dark if ch == "." else orange
                y0, x0 = r * 2 * px, c * px
                lay[y0:y0 + 2 * px, x0:x0 + px, :3] = col
                lay[y0:y0 + 2 * px, x0:x0 + px, 3] = 1.0
                if ch == "#":   # bevel highlight on each pixel
                    lay[y0:y0 + 2, x0:x0 + px, :3] = np.minimum(col * 1.35, 1)
        self.lay = lay
        self.w, self.h = w, h

    def draw(self, frame, x, y, a=1.0, squash=1.0):
        L = self.lay
        if abs(squash - 1) > 1e-3:
            L = cv2.resize(L, (int(self.w / squash ** 0.5), int(self.h * squash)), interpolation=cv2.INTER_NEAREST)
        sh = L.copy()
        sh[..., :3] = 0
        over(frame, sh, x + 6, y + 6 + (self.h - L.shape[0]), 0.35 * a)
        over(frame, L, x, y + (self.h - L.shape[0]), a)


class CreditBlock:
    """end credits: a few centred lines on one frosted-acrylic panel"""

    def __init__(self, lines, cx=1450, cy=560, sizes=(36, 26, 30), weights=(650, 450, 640),
                 colors=((255, 250, 245), (215, 205, 235), (255, 175, 140)), glows=((255, 79, 216), None, (217, 119, 87)),
                 gap=1.55):
        self.items = []
        y = 0.0
        for ln, s, w, c, g in zip(lines, sizes, weights, colors, glows):
            lay = _rgba(ln, nunito(s, w), c)
            gl = glow_of(lay, g, sigma=s * 0.35, gain=0.6) if g else None
            self.items.append((lay, gl, y))
            y += s * gap
        self.h = y
        self.w = max(l.shape[1] for l, _, _ in self.items)
        self.cx, self.cy = cx, cy

    def draw(self, frame, t, dur):
        a = min(1.0, max(t, 0) / 12.0)
        a_exit, dy_exit = exit_curve(dur - t, 12)
        a *= a_exit
        if a <= 0:
            return
        dy = 12 * (1 - min(1.0, max(t, 0) / 12.0)) ** 2 + dy_exit
        x0 = self.cx - self.w / 2 - 50
        y0 = self.cy - self.h / 2 - 34 + dy
        acrylic_pill(frame, x0, y0, self.w + 100, self.h + 52, a, tint=(0.05, 0.03, 0.09))
        for lay, gl, yy in self.items:
            x = self.cx - lay.shape[1] / 2
            y = self.cy - self.h / 2 + yy + dy
            if gl is not None:
                g, gp = gl
                add(frame, g, x - gp, y - gp, 0.6 * a)
            over(frame, lay, x, y, a)
