"""V10/V11 equation textures: each Navier-Stokes term rendered separately (matplotlib mathtext, white on
transparent) + its label (Nunito), laid out on a virtual board. Writes cache/v2/eq/<name>.png, layout.json and
board_full.png (all terms coloured, for the shatter shot).

Board units: pixels of a 4000 x 1700 canvas (Blender scales 1 px = 0.5 mm -> 2.0 x 0.85 m... scaled in the shot).
"""
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import ROOT, cache_dir

OUT = cache_dir("v2/eq")
NUNITO = str(ROOT / "assets" / "fonts" / "nunito" / "Nunito[wght].ttf")
BW, BH = 4000, 1700
COLORS = {"momentum": (59, 232, 255), "pressure": (255, 79, 216), "viscosity": (198, 255, 79),
          "forces": (170, 130, 255), "mass": (255, 158, 107), "white": (255, 250, 245)}

PIECES = [  # name, tex, colour key, label
    ("momentum", r"$\rho\left(\dfrac{\partial \mathbf{u}}{\partial t} + (\mathbf{u}\cdot\nabla)\,\mathbf{u}\right)$",
     "momentum", "mass × acceleration"),
    ("eq1", r"$=$", "white", ""),
    ("pressure", r"$-\nabla p$", "pressure", "pressure"),
    ("plus1", r"$+$", "white", ""),
    ("viscosity", r"$\mu\,\nabla^{2}\mathbf{u}$", "viscosity", "viscosity"),
    ("plus2", r"$+$", "white", ""),
    ("forces", r"$\mathbf{f}$", "forces", "outside forces"),
    ("mass", r"$\nabla\cdot\mathbf{u} \;=\; 0$", "mass", "nothing appears or vanishes"),
]


def render_tex(tex, size=128):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["mathtext.fontset"] = "stix"
    fig = plt.figure(figsize=(0.01, 0.01), dpi=100)
    t = fig.text(0, 0, tex, fontsize=size, color="white", va="bottom")
    fig.canvas.draw()
    bb = t.get_window_extent()
    plt.close(fig)
    w, h = int(bb.width) + 40, int(bb.height) + 40
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_alpha(0)
    fig.text(20 / w, 20 / h, tex, fontsize=size, color="white", va="bottom")
    fig.canvas.draw()
    a = np.asarray(fig.canvas.buffer_rgba()).copy()
    plt.close(fig)
    return Image.fromarray(a)


def label_img(text, size=64):
    f = ImageFont.truetype(NUNITO, size)
    try:
        f.set_variation_by_axes([600])
    except Exception:  # noqa: BLE001
        pass
    w = int(f.getlength(text)) + 30
    im = Image.new("RGBA", (w, size + 30), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((15, 10), text, font=f, fill=(255, 255, 255, 255))
    return im


def main():
    imgs = {}
    for name, tex, ck, lab in PIECES:
        im = render_tex(tex)
        im.save(OUT / f"{name}.png")
        imgs[name] = im
        if lab:
            li = label_img(lab)
            li.save(OUT / f"{name}_label.png")
            imgs[name + "_label"] = li
    # layout: line 1 = momentum ... forces, centred; line 2 = mass conservation
    gap = 56
    line1 = ["momentum", "eq1", "pressure", "plus1", "viscosity", "plus2", "forces"]
    w1 = sum(imgs[n].width for n in line1) + gap * (len(line1) - 1)
    x = (BW - w1) / 2
    y1 = 560
    layout = {}
    for n in line1:
        im = imgs[n]
        layout[n] = [x + im.width / 2, y1, im.width, im.height]
        x += im.width + gap
    im = imgs["mass"]
    layout["mass"] = [BW / 2, 1240, im.width, im.height]
    for name, _, ck, lab in PIECES:
        if lab:
            cx, cy, w, h = layout[name]
            li = imgs[name + "_label"]
            layout[name + "_label"] = [cx, cy + h / 2 + 70, li.width, li.height]
    meta = {"board": [BW, BH], "layout": layout, "colors": {n: COLORS[ck] for n, _, ck, _ in PIECES}}
    (OUT / "layout.json").write_text(json.dumps(meta, indent=1))
    # full coloured board (for the shatter)
    board = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    for name, _, ck, lab in PIECES:
        for key in (name, name + "_label") if lab else (name,):
            im = imgs[key]
            col = COLORS[ck]
            a = np.asarray(im)[..., 3]
            rgba = np.zeros((im.height, im.width, 4), np.uint8)
            rgba[..., :3] = col
            rgba[..., 3] = (a * (0.75 if key.endswith("_label") else 1.0)).astype(np.uint8)
            cx, cy, w, h = layout[key]
            board.alpha_composite(Image.fromarray(rgba), (int(cx - w / 2), int(cy - h / 2)))
    glow = board.filter(ImageFilter.GaussianBlur(14))
    board = Image.alpha_composite(glow, board)
    board.save(OUT / "board_full.png")
    print("eq textures ->", OUT, {k: [int(v) for v in layout[k][2:]] for k in layout})


if __name__ == "__main__":
    main()
