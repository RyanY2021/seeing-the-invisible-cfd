"""V04 holographic cards: neon line-art icons with real potential-flow streamlines.

For each card writes cache/v2/cards/<name>_icon.png (RGBA neon line art) and <name>_flow.png
(R = streamline mask, G = normalised arc length along the line, B = line id / 255) so a Blender shader can run
glowing dashes along the streamlines (the flow 'moves' on the card).

Streamlines: Laplace equation for the stream function (psi = y far away, psi = const on the body), solved on a
grid with scipy, contoured with matplotlib.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

from common import cache_dir

CW, CH = 1024, 640
OUT = cache_dir("v2/cards")


def potential_streamlines(mask, n_lines=13, circulation=0.0):
    """mask: (ny, nx) bool body. returns list of (k, 2) polylines in grid coords (x, y)"""
    ny, nx = mask.shape
    idx = -np.ones((ny, nx), int)
    interior = np.zeros((ny, nx), bool)
    interior[1:-1, 1:-1] = True
    interior &= ~mask
    idx[interior] = np.arange(interior.sum())
    n = interior.sum()
    A = lil_matrix((n, n))
    b = np.zeros(n)
    yy, xx = np.mgrid[0:ny, 0:nx]
    psi_far = (yy - ny / 2).astype(float)
    # body value: psi of the stagnation streamline (0 = centre line) + optional circulation shift
    body_val = circulation
    ii = np.argwhere(interior)
    for k, (y, x) in enumerate(ii):
        A[k, k] = -4
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            y2, x2 = y + dy, x + dx
            if interior[y2, x2]:
                A[k, idx[y2, x2]] = 1
            elif mask[y2, x2]:
                b[k] -= body_val
            else:
                b[k] -= psi_far[y2, x2]
    sol = spsolve(A.tocsr(), b)
    psi = psi_far.copy()
    psi[interior] = sol
    psi[mask] = body_val
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    levels = np.linspace(-ny * 0.42, ny * 0.42, n_lines)
    cs = plt.contour(np.arange(nx), np.arange(ny), psi, levels=levels)
    lines = []
    for segs in cs.allsegs:
        for s in segs:
            if len(s) > 20:
                lines.append(s)
    plt.close("all")
    return lines


def draw_card(name, outline_polys, lines, color, fill_polys=(), extra=None, grid=(300, 150), line_w=5):
    """outline_polys/lines in grid coords -> card pixels"""
    gx, gy = grid
    sx, sy = CW / gx, CH / gy

    def P(p):
        return [(float(x) * sx, CH - float(y) * sy) for x, y in p]

    icon = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    col = tuple(int(c) for c in color)
    for poly in fill_polys:
        d.polygon(P(poly), fill=col + (60,))
    for poly in outline_polys:
        pts = P(poly)
        d.line(pts + [pts[0]], fill=col + (255,), width=line_w, joint="curve")
    if extra:
        extra(d, sx, sy)
    glow = icon.filter(ImageFilter.GaussianBlur(10))
    icon = Image.alpha_composite(glow, icon)
    icon.save(OUT / f"{name}_icon.png")
    # flow texture: R mask, G arc-length param, B line id
    flow = np.zeros((CH, CW, 3), np.uint8)
    for li, ln in enumerate(lines):
        pts = np.array(P(ln))
        seg = np.hypot(*np.diff(pts, axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        L = s[-1] if s[-1] > 0 else 1
        im = Image.new("RGB", (CW, CH), (0, 0, 0))
        dd = ImageDraw.Draw(im)
        for k in range(len(pts) - 1):
            g = int(255 * s[k] / L)
            dd.line([tuple(pts[k]), tuple(pts[k + 1])], fill=(255, g, (li * 37) % 255), width=7)
        a = np.asarray(im)
        m = a[..., 0] > 0
        flow[m] = a[m]
    Image.fromarray(flow).save(OUT / f"{name}_flow.png")


def joukowski_airfoil(gx, gy, chord=150, alpha=8.0):
    """mask + outline of a cambered Joukowski airfoil centred in the grid"""
    t = np.linspace(0, 2 * np.pi, 400)
    c = 1.0
    zc = -0.08 + 0.08j
    r = abs(c - zc)
    z = zc + r * np.exp(1j * t)
    w = z + c * c / z
    w = w * np.exp(-1j * np.radians(alpha))
    w = (w - w.real.mean()) * chord / (w.real.max() - w.real.min())
    poly = np.stack([w.real + gx * 0.42, w.imag + gy / 2], -1)
    from matplotlib.path import Path
    yy, xx = np.mgrid[0:gy, 0:gx]
    mask = Path(poly).contains_points(np.stack([xx.ravel(), yy.ravel()], -1)).reshape(gy, gx)
    return mask, poly


def car_profile(gx, gy):
    from car_sdf import car_sdf
    xs = np.linspace(-0.6, 5.1, gx)
    zs = np.linspace(-0.0, 2.85, gy) - 0.0
    X, Z = np.meshgrid(xs, zs)
    sdf = car_sdf(X.ravel(), np.zeros(X.size), Z.ravel()).reshape(gy, gx)
    mask = sdf < 0
    mask[:4, :] = True                       # the ground
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cs = plt.contour(np.arange(gx), np.arange(gy), sdf, levels=[0.0])
    polys = [s for s in cs.allsegs[0] if len(s) > 30]
    plt.close("all")
    return mask, polys


def main():
    gx, gy = 300, 150
    # 1 wing (magenta)
    mask, poly = joukowski_airfoil(gx, gy)
    lines = potential_streamlines(mask, 15, circulation=6.0)
    draw_card("wing", [poly], lines, (255, 79, 216), fill_polys=[poly])
    # 2 car (cyan)
    mask, polys = car_profile(gx, gy)
    lines = potential_streamlines(mask, 14)
    lines = [ln for ln in lines if ln[:, 1].min() > 6]

    def ground(d, sx, sy):
        d.line([(0, CH - 4 * sy), (CW, CH - 4 * sy)], fill=(59, 232, 255, 160), width=3)
    draw_card("car", polys, lines, (59, 232, 255), fill_polys=polys, extra=ground)
    # 3 offshore turbine (peach): tower + blades + sea, wake streamlines with a helical wiggle
    def turbine(d, sx, sy):
        c = (255, 158, 107, 255)
        hub = (CW * 0.30, CH * 0.33)
        d.line([(hub[0], hub[1]), (hub[0], CH * 0.80)], fill=c, width=7)
        for k in range(3):
            a = np.radians(90 + 120 * k + 15)
            d.line([hub, (hub[0] + 150 * np.cos(a), hub[1] - 150 * np.sin(a))], fill=c, width=6)
        d.ellipse([hub[0] - 10, hub[1] - 10, hub[0] + 10, hub[1] + 10], fill=c)
        for k in range(4):
            y = CH * 0.80 + k * 18
            pts = [(x, y + 5 * np.sin(x / 40 + k)) for x in np.linspace(0, CW, 60)]
            d.line(pts, fill=(255, 158, 107, 150 - 30 * k), width=3)
    lines = []
    for k in range(9):
        y0 = gy * (0.30 + 0.075 * k)
        x = np.linspace(0, gx, 240)
        wig = np.where(x > gx * 0.30, 3.5 * np.sin((x - gx * 0.3) / 6 + k) * np.clip((x - gx * 0.3) / 40, 0, 1), 0)
        lines.append(np.stack([x, (gy - y0) + wig * (1 if 2 < k < 7 else 0.2)], -1))
    draw_card("offshore", [], lines, (255, 158, 107), extra=turbine)
    # 4 globe (lime): circle + graticule, swirling wind spirals as streamlines
    def globe(d, sx, sy):
        c = (198, 255, 79, 255)
        cx, cy, r = CW / 2, CH / 2, CH * 0.40
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=6)
        for k in (-0.5, 0, 0.5):
            d.arc([cx - r, cy + k * r - r * 0.25, cx + r, cy + k * r + r * 0.25], 0, 180, fill=(198, 255, 79, 110), width=2)
        d.ellipse([cx - r * 0.45, cy - r, cx + r * 0.45, cy + r], outline=(198, 255, 79, 110), width=2)
    raw = []
    for (cx, cy, sgn) in ((0.42, 0.62, 1), (0.60, 0.40, -1)):
        th = np.linspace(0.3, 3.4 * np.pi, 300)
        rr = 2 + 2.2 * th
        raw.append(np.stack([gx * cx + rr * np.cos(sgn * th) * 0.78, gy * cy + rr * np.sin(sgn * th)], -1))
    for k in range(6):
        x = np.linspace(gx * 0.2, gx * 0.8, 200)
        raw.append(np.stack([x, gy * (0.22 + 0.11 * k) + 5 * np.sin(x / 16 + 1.7 * k)], -1))
    # keep only the parts inside the globe (circle of radius 0.40*CH px, aspect-corrected)
    lines = []
    sxp, syp = CW / gx, CH / gy
    for ln in raw:
        px, py = ln[:, 0] * sxp - CW / 2, ln[:, 1] * syp - CH / 2
        inside = px ** 2 + py ** 2 < (CH * 0.37) ** 2
        cur = []
        for pt, ok in zip(ln, inside):
            if ok:
                cur.append(pt)
            elif len(cur) > 10:
                lines.append(np.array(cur))
                cur = []
            else:
                cur = []
        if len(cur) > 10:
            lines.append(np.array(cur))
    draw_card("globe", [], lines, (198, 255, 79), extra=globe)
    # 5 heart (red-peach): heart outline, flow lines through a vessel inside
    t = np.linspace(0, 2 * np.pi, 400)
    hx = 16 * np.sin(t) ** 3
    hy = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    heart = np.stack([gx / 2 + hx * 3.6, gy / 2 + 4 + hy * 3.6], -1)
    lines = []
    for k in range(7):
        x = np.linspace(0, gx, 260)
        y = gy * 0.5 + (k - 3) * 5 + 22 * np.exp(-((x - gx / 2) / 45) ** 2) * np.sign(k - 3 + 0.01) * 0.0 \
            + 6 * np.sin(x / 25) * np.exp(-((x - gx / 2) / 80) ** 2)
        lines.append(np.stack([x, y], -1))
    draw_card("heart", [heart], lines, (255, 110, 120), fill_polys=[heart])
    print("cards ->", OUT)


if __name__ == "__main__":
    main()
