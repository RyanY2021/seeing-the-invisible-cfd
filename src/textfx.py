"""Typography helpers: render tracked text with PIL into float RGBA layers."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import FONT_CAPTION, FONT_CAPTION_IT, FONT_LABEL, FONT_TITLE


@lru_cache(maxsize=64)
def font(path, size):
    return ImageFont.truetype(str(path), size)


def text_layer(text, size, path=FONT_CAPTION, tracking=0.0, color=(1, 1, 1), ss=2):
    """Return float32 RGBA image (h, w, 4) tightly fitting `text`. tracking in em units."""
    f = font(str(path), size * ss)
    # measure per char for tracking
    widths = [f.getlength(ch) for ch in text]
    track = tracking * size * ss
    total = sum(widths) + track * max(len(text) - 1, 0)
    asc, desc = f.getmetrics()
    w = int(total + 4 * ss)
    h = int(asc + desc + 4 * ss)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    x = 2 * ss
    if tracking == 0:
        d.text((x, 2 * ss), text, font=f, fill=255)
    else:
        for ch, cw in zip(text, widths):
            d.text((x, 2 * ss), ch, font=f, fill=255)
            x += cw + track
    img = img.resize((max(1, w // ss), max(1, h // ss)), Image.LANCZOS)
    a = np.asarray(img, np.float32) / 255.0
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = color
    rgba[..., 3] = a
    return rgba


def paste(dst, layer, x, y, opacity=1.0, anchor="lt"):
    """Alpha-composite float RGBA `layer` onto float RGB `dst` (in place). anchor: l/c/r + t/m/b."""
    h, w = layer.shape[:2]
    if anchor[0] == "c":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    x, y = int(round(x)), int(round(y))
    H, W = dst.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return dst
    sub = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4] * opacity
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a
    return dst


__all__ = ["text_layer", "paste", "FONT_CAPTION", "FONT_CAPTION_IT", "FONT_LABEL", "FONT_TITLE"]
