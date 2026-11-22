"""Presentation doodles: people, arrows, speech bubbles & frames, idea icons (sketchnote style).

    .venv/bin/python examples/doodles.py        # -> out/symbols/doodles/

Every doodle is plain ink with a slight hand-drawn wobble and a few accent fills, so on the
tablet you can lasso one, copy it into your slides or notes and scale it.
"""
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

from quantum_gates import glyphs, shift  # noqa: E402
from rmdraw.model import Document, Stroke  # noqa: E402
from rmdraw.shapes_json import from_dict  # noqa: E402

NAME = "Presentation doodles"
# accent fills, one step stronger than on screen (the tablet mutes colours)
YEL, BLU, RED, GRN, ORG = "#ffc400", "#5f9dff", "#ff4f4f", "#3fbf5a", "#ff7a00"
PBLU, PYEL, PGRN, PRED, PORG = "#b9d4ff", "#ffe066", "#9fe0aa", "#ff9b9b", "#ffc98a"
DRED, GRY = "#c62828", "#a8a8a8"


# ---- geometry ----------------------------------------------------------------------------
def arc(cx, cy, r, a0=0.0, a1=360.0, ry=None, step=6.0):
    ry = r if ry is None else ry
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


def bez(*p, n=28):
    """Cubic chain p0 c1 c2 p3 [c c p ...]."""
    out = []
    for j in range(0, len(p) - 1, 3):
        a, b, c, d = p[j:j + 4]
        for i in range(0 if j == 0 else 1, n + 1):
            t = i / n
            u = 1 - t
            out.append((u ** 3 * a[0] + 3 * u * u * t * b[0] + 3 * u * t * t * c[0] + t ** 3 * d[0],
                        u ** 3 * a[1] + 3 * u * u * t * b[1] + 3 * u * t * t * c[1] + t ** 3 * d[1]))
    return out


def smooth(pts, n=3, closed=True):
    for _ in range(n):
        src = pts + [pts[0]] if closed else pts
        out = [] if closed else [pts[0]]
        for (ax, ay), (bx, by) in zip(src, src[1:]):
            out += [(0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by),
                    (0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by)]
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def bumps(pts, k=0.45, closed=True, n=10):
    """Replace each edge by an outward bulge (clouds, puzzle knobs); k<0 bulges inward."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    src = pts + [pts[0]] if closed else pts
    out = []
    for a, b in zip(src, src[1:]):
        L = math.dist(a, b)
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (mx - cx) * nx + (my - cy) * ny < 0:
            nx, ny = -nx, -ny
        for i in range(n):
            t = i / n
            h = k * L * math.sin(math.pi * t)
            out.append((a[0] + (b[0] - a[0]) * t + nx * h, a[1] + (b[1] - a[1]) * t + ny * h))
    return out


def star(r, ri, n=5, rot=-90.0, rx=1.0):
    return [((r if i % 2 == 0 else ri) * rx * math.cos(math.radians(rot + 180 * i / n)),
             (r if i % 2 == 0 else ri) * math.sin(math.radians(rot + 180 * i / n)))
            for i in range(2 * n)]


def rrect(x0, y0, x1, y1, r):
    return (arc(x1 - r, y0 + r, r, -90, 0) + arc(x1 - r, y1 - r, r, 0, 90)
            + arc(x0 + r, y1 - r, r, 90, 180) + arc(x0 + r, y0 + r, r, 180, 270))


def rot(pts, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def dens(pts, step=0.6):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1)]
    return out


def wob(pts, seed, amp, closed):
    """Smooth hand-drawn wobble along the normal (periodic for closed paths, tapered at ends)."""
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.dist(a, b))
    L = s[-1]
    if L < 1.0:
        return pts
    rnd = random.Random(seed)
    waves = []
    for wl, a in ((16.0, 1.0), (6.0, 0.45)):
        cyc = max(1, round(L / wl)) if closed else L / wl
        waves.append((cyc, a * amp, rnd.uniform(0, 2 * math.pi)))
    out, n = [], len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[i - 1] if i > 0 else (pts[-2] if closed else pts[0])
        b = pts[i + 1] if i < n - 1 else (pts[1] if closed else pts[-1])
        tx, ty = b[0] - a[0], b[1] - a[1]
        tl = math.hypot(tx, ty) or 1.0
        off = sum(A * math.sin(2 * math.pi * c * s[i] / L + ph) for c, A, ph in waves)
        if not closed:
            off *= min(1.0, s[i] / 3.0, (L - s[i]) / 3.0)
        out.append((x - ty / tl * off, y + tx / tl * off))
    return out


# ---- the page collector ------------------------------------------------------------------
class D:
    """One page: fills (rmdraw shape items) underneath, ink strokes on top. Draws in local
    coordinates placed with at(cx, cy, k)."""

    def __init__(self):
        self.items, self.strokes, self.n = [], [], 0
        self.at(0, 0)

    def at(self, cx, cy, k=1.0):
        self.ox, self.oy, self.k = cx, cy, k
        return self

    def T(self, pts):
        return [(self.ox + self.k * x, self.oy + self.k * y) for x, y in pts]

    def ink(self, pts, w=0.5, color="black", closed=False, wobble=0.2, pen="fineliner"):
        pts = self.T(pts)
        if closed:
            pts = pts + [pts[0]]
        pts = dens(pts)
        if wobble:
            pts = wob(pts, self.n, wobble, closed)
            self.n += 1
        self.strokes.append(Stroke(pts, pen=pen, color=color, width_mm=w))

    def fill(self, pts, color):
        self.items.append({"type": "polyline", "closed": True, "outline": False,
                           "points": [[round(x, 3), round(y, 3)] for x, y in self.T(pts)],
                           "fill": {"color": color}})

    def shape(self, pts, fill=None, w=0.5, color="black"):
        if fill:
            self.fill(pts, fill)
        self.ink(pts, w, color, closed=True)

    def dot(self, x, y, w=1.0, color="black"):
        (x, y), = self.T([(x, y)])
        self.strokes.append(Stroke([(x - 0.12, y), (x + 0.12, y)], color=color, width_mm=w))

    def head(self, tip, ang, s=2.8, w=0.5, color="black"):
        for side in (-1, 1):
            a = ang + math.pi + side * math.radians(28)
            self.ink([(tip[0] + s * math.cos(a), tip[1] + s * math.sin(a)), tip], w, color, wobble=0)

    def arrow(self, pts, w=0.5, color="black", both=False, s=2.8, pen="fineliner"):
        self.ink(pts, w, color, pen=pen)
        ends = [(pts[-1], _back(pts[::-1]))] + ([(pts[0], _back(pts))] if both else [])
        for tip, back in ends:
            self.head(tip, math.atan2(tip[1] - back[1], tip[0] - back[0]), s, w, color)

    def dashed(self, pts, w=0.45, color="black", on=1.6, off=1.2):
        pts = dens(pts, 0.25)
        seg, run_, on_ = [pts[0]], 0.0, True
        for a, b in zip(pts, pts[1:]):
            run_ += math.dist(a, b)
            if on_:
                seg.append(b)
            if run_ >= (on if on_ else off):
                if on_ and len(seg) > 1:
                    self.ink(seg, w, color, wobble=0)
                on_, run_, seg = not on_, 0.0, [b]
        if on_ and len(seg) > 1:
            self.ink(seg, w, color, wobble=0)

    def text(self, s, x, y, h, color="black", w=None, hand=True, align="center"):
        """Text centred on x with its cap top at y (local coordinates)."""
        (x, y), = self.T([(x, y)])
        h *= self.k
        st, adv = glyphs(s, 0, 0, h, "futural", color, w or max(0.22, h * 0.1), hand=hand)
        dx = {"center": -adv / 2, "left": 0.0}[align]
        self.strokes += shift(st, x + dx, y)

    def page(self):
        return self.items, self.strokes


def caption(d, s, x, y):
    d.at(0, 0)
    d.text(s, x, y, 2.6, color="gray", w=0.25)


def title(d, s, sub):
    d.at(0, 0)
    d.text(s, 90, 10, 7, w=0.6)
    d.text(sub, 90, 21, 2.8, color="gray", w=0.25)


def _back(pts, dist=2.5):
    """Point `dist` mm along the path from pts[0] (gives a stable arrowhead direction)."""
    run_ = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if run_ + L >= dist:
            t = (dist - run_) / L
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        run_ += L
    return pts[-1]


def arc_arrow_head(d, pts, s=2.8, w=0.5, color="black"):
    tip, back = pts[-1], _back(pts[::-1])
    d.head(tip, math.atan2(tip[1] - back[1], tip[0] - back[0]), s, w, color)


# ---- people -------------------------------------------------------------------------------
def face(d, cx, cy, r, mood="smile", look=(0.0, 0.0)):
    ex, ey, dw = 0.36 * r, -0.18 * r, max(0.7, 0.16 * r)
    lx, ly = look[0] * r, look[1] * r
    w = max(0.35, 0.06 * r)
    if mood == "laugh":
        for sx in (-1, 1):
            d.ink(arc(cx + sx * ex, cy + ey + 0.1 * r, 0.16 * r, 200, 340), w, wobble=0)
    elif mood == "wink":
        d.dot(cx - ex, cy + ey, dw)
        d.ink(arc(cx + ex, cy + ey + 0.1 * r, 0.16 * r, 200, 340), w, wobble=0)
    elif mood == "surprised":
        for sx in (-1, 1):
            d.ink(arc(cx + sx * ex, cy + ey, 0.13 * r), w, wobble=0)
    else:
        for sx in (-1, 1):
            d.dot(cx + sx * ex + lx, cy + ey + ly, dw)
    if mood in ("smile", "wink"):
        d.ink(arc(cx, cy + 0.02 * r, 0.5 * r, 30, 150), w, wobble=0)
    elif mood == "laugh":
        m = arc(cx, cy + 0.15 * r, 0.45 * r, 0, 180)
        if r > 5:
            d.fill(m, RED)
        d.ink(m, w, closed=True, wobble=0)
    elif mood == "sad":
        d.ink(arc(cx, cy + 0.8 * r, 0.42 * r, 215, 325), w, wobble=0)
    elif mood == "surprised":
        d.ink(arc(cx, cy + 0.42 * r, 0.17 * r), w, wobble=0)
    elif mood == "flat":
        d.ink([(cx - 0.28 * r, cy + 0.42 * r), (cx + 0.28 * r, cy + 0.34 * r)], w, wobble=0)
    if mood == "angry":
        for sx in (-1, 1):
            d.ink([(cx + sx * 0.55 * r, cy - 0.5 * r), (cx + sx * 0.18 * r, cy - 0.32 * r)], w, wobble=0)
        d.ink(arc(cx, cy + 0.8 * r, 0.42 * r, 215, 325), w, wobble=0)


def _limb(start, spec, l1, l2):
    if isinstance(spec[0], tuple):
        return [start, spec[0], spec[1]]
    a1, a2 = map(math.radians, spec)
    e = (start[0] + l1 * math.cos(a1), start[1] + l1 * math.sin(a1))
    return [start, e, (e[0] + l2 * math.cos(a2), e[1] + l2 * math.sin(a2))]


STAND = ((80, 92), (100, 88))


def person(d, arms, legs=STAND, body=BLU, mood="smile", look=(0.0, 0.0)):
    """Sketchnote person in local coords: head top about y=-17, feet at y=12."""
    torso = smooth([(-2.8, -8.8), (2.8, -8.8), (4.0, 2.4), (-4.0, 2.4)], 2)
    d.shape(torso, body)
    d.ink(arc(0, -13.4, 3.6), closed=True)
    face(d, 0, -13.4, 3.6, mood, look)
    for s, spec in zip(((2.5, -7.9), (-2.5, -7.9)), arms):
        d.ink(_limb(s, spec, 5.0, 4.6), 0.6)
    for (hx, hy), spec, fd in zip(((1.9, 2.2), (-1.9, 2.2)), legs, (1, -1)):
        p = _limb((hx, hy), spec, 5.0, 5.0)
        d.ink(p + [(p[-1][0] + 1.9 * fd, p[-1][1])], 0.6)


def bulb(d, rays=True):
    """Light bulb, centre of glass at (0,-4), base to y=9."""
    glass = arc(0, -4, 6.5, 125, 415) + [(3.2, 4.6), (-3.2, 4.6)]
    d.shape(glass, YEL)
    d.ink([(-1.8, 4.4), (-1.2, -1.0), (-0.4, -2.6), (0.4, -1.0), (1.2, -2.6), (1.8, -1.0), (1.8, 4.4)],
          0.35, wobble=0.1)
    d.shape(rrect(-3.3, 4.6, 3.3, 8.2, 0.8), GRY)
    d.ink([(-3.3, 6.4), (3.3, 6.4)], 0.35)
    d.ink(arc(0, 8.2, 1.8, 0, 180), 0.45)
    if rays:
        for a in (-160, -125, -90, -55, -20):
            r = math.radians(a)
            d.ink([(8.6 * math.cos(r), -4 + 8.6 * math.sin(r)),
                   (11.2 * math.cos(r), -4 + 11.2 * math.sin(r))], 0.5, wobble=0)


def page_people():
    d = D()
    title(d, "People", "presentation doodles - lasso, copy, scale")
    cols, rows = (28, 68, 112, 152), (62, 114, 166)
    poses = [
        ("standing", lambda: person(d, ((70, 95), (110, 85)))),
        ("waving", lambda: person(d, ((-35, -85), (110, 85)), body=ORG)),
        ("cheering", lambda: person(d, ((-55, -75), (-125, -105)), ((70, 90), (110, 90)),
                                    body=GRN, mood="laugh")),
        ("pointing", lambda: person(d, ((-4, -2), (110, 85)), body=RED)),
        ("thinking", lambda: (person(d, (((4.4, -4.0), (1.6, -9.4)), (110, 85)), mood="flat",
                                     look=(-0.12, -0.12)),
                              [d.ink(arc(x, y, r), 0.4, closed=True)
                               for x, y, r in ((-5.5, -19, 0.6), (-7.5, -22, 0.9), (-10.5, -25.5, 1.4))])),
        ("shrugging", lambda: person(d, ((15, -75), (165, -105)), body=ORG, mood="flat")),
        ("walking", lambda: person(d, ((60, 75), (125, 105)), ((62, 100), (112, 96)), body=GRN)),
        ("big idea", lambda: (person(d, ((-40, -95), (110, 85)), body=RED, mood="surprised"),
                              d.at(d.ox + 9 * d.k, d.oy - 22.5 * d.k, 0.45), bulb(d))),
        ("question", lambda: (person(d, ((30, 150), (150, 30)), body=BLU, mood="flat"),
                              d.text("?", 8, -27, 8, w=0.7))),
        ("presenting", presenter),
        ("at the desk", desk),
        ("team", team),
    ]
    for i, (name, fn) in enumerate(poses):
        cx, cy = cols[i % 4], rows[i // 4]
        d.at(cx, cy)
        _CUR[0] = d
        fn()
        caption(d, name, cx, cy + 15.5)
    moods = ("smile", "laugh", "wink", "surprised", "flat", "sad", "angry")
    for i, m in enumerate(moods):
        cx = 20 + i * 23.3
        d.at(cx, 207)
        d.ink(arc(0, 0, 8.5), 0.55, closed=True)
        face(d, 0, 0, 8.5, m)
        caption(d, {"flat": "meh"}.get(m, m), cx, 219)
    return d.page()


_CUR = [None]


def presenter():
    d = _CUR[0]
    cx, cy = d.ox, d.oy
    d.at(cx + 8, cy)
    d.ink([(-7, -18), (11, -18), (11, -1), (-7, -1)], 0.5, closed=True)
    d.ink([(-2, -1), (-5, 12)], 0.5)
    d.ink([(6, -1), (9, 12)], 0.5)
    for x, h, c in ((-4, 5, BLU), (0, 9, GRN), (4, 13, ORG)):
        d.shape([(x, -3), (x + 3, -3), (x + 3, -3 - h), (x, -3 - h)], c, 0.35)
    d.at(cx - 9, cy + 1.5, 0.9)
    person(d, ((-15, -15), (110, 85)), body=RED)
    d.at(cx, cy)


def desk():
    d = _CUR[0]
    d.shape([(-17, 0), (17, 0), (17, 3), (-17, 3)], ORG, 0.5)
    d.ink([(-15, 3), (-15, 12)], 0.6)
    d.ink([(15, 3), (15, 12)], 0.6)
    # person behind the desk (upper body only)
    d.shape([(-9.4, -8.8), (-3.8, -8.8), (-2.8, 0), (-10.4, 0)], BLU)
    d.ink(arc(-6.6, -13.4, 3.6), closed=True)
    face(d, -6.6, -13.4, 3.6, "smile", (0.12, 0.08))
    d.ink([(-4.2, -7.8), (-1.0, -3.2), (4.0, -1.0)], 0.6)
    d.ink([(-9.0, -7.8), (-10.6, -3.0), (-7.0, -0.8)], 0.6)
    # laptop
    d.shape([(4, -12), (14, -12), (14, -1.6), (4, -1.6)], PBLU, 0.5)
    d.shape([(2.4, -1.6), (15.6, -1.6), (16.6, 0), (1.4, 0)], GRY, 0.45)
    d.ink([(6.5, -8.5), (9, -6), (11.5, -9.5)], 0.35, wobble=0.1)


def team():
    d = _CUR[0]
    cx, cy = d.ox, d.oy
    for dx, k, c, m in ((-11, 0.72, ORG, "smile"), (11, 0.72, GRN, "smile"), (0, 0.82, BLU, "laugh")):
        d.at(cx + dx, cy + 12 * (1 - k), k)
        person(d, ((70, 95), (110, 85)), body=c, mood=m)
    d.at(cx, cy)


# ---- arrows ---------------------------------------------------------------------------------
def page_arrows():
    d = D()
    title(d, "Arrows", "connect ideas: lasso an arrow, rotate and stretch it")
    cols, rows = (30, 70, 110, 150), (46, 85, 124, 163, 202)

    def straight():
        d.arrow([(-14, 0), (14, 0)])

    def curved():
        d.arrow(bez((-14, 6), (-6, -13), (6, -13), (14, 6)))

    def s_curve():
        d.arrow(bez((-14, -6), (-2, -14), (2, 14), (14, 6)))

    def zigzag():
        d.arrow([(-14, -6), (-7, 6), (-1, -5), (6, 7), (14, -5)])

    def loop():
        pts = []
        for i in range(81):
            t = i / 80
            pts.append((-14 + 28 * t + 7 * math.sin(2 * math.pi * t), 5 - 11 * math.sin(math.pi * t) ** 2))
        d.arrow(pts)

    def double():
        d.arrow([(-14, 0), (14, 0)], both=True)

    def u_turn():
        d.arrow([(8, 9), (8, -1)] + arc(0, -1, 8, 0, -180)[1:] + [(-8, 9)])

    def cycle():
        for i in range(3):
            a0 = i * 120 - 80
            pts = arc(0, 0, 9, a0, a0 + 92, step=4)
            d.ink(pts)
            arc_arrow_head(d, pts, 2.4)

    def block():
        d.shape([(-14, -4), (3, -4), (3, -9.5), (14, 0), (3, 9.5), (3, 4), (-14, 4)], ORG, 0.6)

    def dashed():
        pts = bez((-14, -6), (-4, 10), (4, 10), (14, -6))
        d.dashed(pts)
        arc_arrow_head(d, pts)

    def branch():
        d.ink([(-14, 0), (-5, 0)])
        for y in (-9, 0, 9):
            d.arrow(bez((-5, 0), (3, 0), (4, y), (14, y)))

    def merge():
        for y in (-9, 0, 9):
            d.ink(bez((-14, y), (-4, y), (-3, 0), (5, 0)))
        d.arrow([(5, 0), (14, 0)])

    def spiral():
        pts = []
        for i in range(120):
            th = i / 119 * 3.3 * math.pi
            r = 0.6 + 2.7 * th / math.pi
            pts.append((r * math.cos(th), r * math.sin(th) * 0.9))
        d.arrow(pts)

    def trend():
        d.ink([(-13, -10), (-13, 8), (14, 8)], 0.4, "gray")
        d.arrow([(-11, 5), (-5, -0.5), (0, 2), (6, -4), (12, -9)], 0.6, s=3)

    def elbow():
        d.arrow(smooth([(-14, -8), (0, -8), (0, 8), (14, 8)], 3, closed=False))

    def bounce():
        pts, x0 = [], -14
        for x1, h in ((-3, 12), (6, 7), (12, 3.5)):
            for i in range(1, 21):
                t = i / 20
                pts.append((x0 + (x1 - x0) * t, 7 - h * math.sin(math.pi * t)))
            x0 = x1
        d.arrow([(-14, 7)] + pts[:-1] + [(14.5, 6.4)])
        d.ink([(-15, 8.5), (15, 8.5)], 0.35, "gray")

    def exchange():
        d.arrow([(-13, -3.5), (13, -3.5)])
        d.arrow([(13, 3.5), (-13, 3.5)])

    def burst():
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            d.arrow([(3.5 * math.cos(a), 3.5 * math.sin(a)), (11 * math.cos(a), 11 * math.sin(a))], s=2.2)
        d.shape(arc(0, 0, 2.2), YEL, 0.45)

    def chevrons():
        for x, c in ((-14, BLU), (-4.5, GRN), (5, ORG)):
            d.shape([(x, -5.5), (x + 6, -5.5), (x + 9.5, 0), (x + 6, 5.5), (x, 5.5), (x + 3.5, 0)], c, 0.45)

    def marker():
        pts = bez((-14, 7), (-6, -10), (2, 12), (13, -6))
        d.arrow(pts, 1.2, "red", s=3.4, pen="marker")

    kinds = [("straight", straight), ("curved", curved), ("s-curve", s_curve), ("zigzag", zigzag),
             ("loop", loop), ("two-way", double), ("u-turn", u_turn), ("cycle", cycle),
             ("block", block), ("dashed", dashed), ("branch", branch), ("merge", merge),
             ("spiral", spiral), ("growth", trend), ("elbow", elbow), ("bounce", bounce),
             ("exchange", exchange), ("burst", burst), ("process", chevrons), ("marker", marker)]
    for i, (name, fn) in enumerate(kinds):
        cx, cy = cols[i % 4], rows[i // 4]
        d.at(cx, cy)
        fn()
        caption(d, name, cx, cy + 13.5)
    return d.page()


# ---- speech bubbles & frames ------------------------------------------------------------------
def ell_bubble(cx, cy, rx, ry, g0, g1, tip):
    return arc(cx, cy, rx, g1, g0 + 360, ry, step=5) + [tip]


def page_bubbles():
    d = D()
    title(d, "Bubbles & frames", "write inside them - or lasso and resize")
    cols, rows = (33, 90, 147), (50, 94, 138, 182)

    def speech():
        d.shape(ell_bubble(0, -3, 19, 11.5, 105, 122, (-13, 13)), PBLU, 0.55)

    def box_speech():
        r, x0, y0, x1, y1 = 4, -19, -13, 19, 7
        pts = (arc(x1 - r, y0 + r, r, -90, 0) + arc(x1 - r, y1 - r, r, 0, 90)
               + [(-6, y1), (-14, 14), (-11, y1)]
               + arc(x0 + r, y1 - r, r, 90, 180) + arc(x0 + r, y0 + r, r, 180, 270))
        d.shape(pts, None, 0.55)

    def thought():
        d.shape(bumps(arc(2, -4, 17, 0, 324, 9.5, step=36), 0.32), None, 0.5)
        d.shape(arc(-12, 9, 2.2), None, 0.45)
        d.shape(arc(-16, 13.5, 1.3), None, 0.45)

    def shout():
        pts = star(19, 13, 9, rot=-80, rx=1.05)
        pts = [(x, y * 0.72) for x, y in pts]
        d.shape(pts, YEL, 0.6)

    def whisper():
        pts = ell_bubble(0, -3, 19, 11.5, 60, 78, (13, 13))
        d.dashed(pts + [pts[0]], 0.45)

    def dialogue():
        d.shape(ell_bubble(-8, -6, 11, 7, 110, 132, (-16, 5)), PBLU, 0.5)
        d.shape(ell_bubble(9, 7, 11, 7, 48, 70, (18, 16)), PORG, 0.5)

    def banner():
        for s in (-1, 1):
            m = lambda pts: [(s * x, y) for x, y in pts]
            d.fill(m([(-18, -2), (-26, -2), (-23, 3), (-26, 8), (-14, 8), (-14, 4), (-18, 4)]), DRED)
            d.fill(m([(-18, 4), (-14, 4), (-14, 8)]), "#7a1010")
            d.ink(m([(-18, -2), (-26, -2), (-23, 3), (-26, 8), (-14, 8), (-14, 4)]), 0.5)
            d.ink(m([(-18, 4), (-14, 8)]), 0.4)
        d.shape([(-18, -7), (18, -7), (18, 4), (-18, 4)], RED, 0.55)

    def sticky():
        note = rot([(-14, -14), (14, -14), (14, 8), (8, 14), (-14, 14)], -4)
        d.shape(note, PYEL, 0.5)
        fold = rot([(14, 8), (8, 14), (8, 8)], -4)
        d.shape(fold, YEL, 0.4)
        d.fill(rot([(-6, -17), (6, -17), (6, -11), (-6, -11)], 3), "#cfcfcf")
        d.ink(rot([(-6, -17), (6, -17), (6, -11), (-6, -11)], 3), 0.3, "gray", closed=True)

    def frame():
        d.ink([(-20, -11), (20, -11), (20, 11), (-20, 11)], 0.6, closed=True)
        d.ink([(-18.2, -9.2), (18.2, -9.2), (18.2, 9.2), (-18.2, 9.2)], 0.3, closed=True)
        for x in (-20, 20):
            for y in (-11, 11):
                d.shape([(x, y - 2), (x + 2, y), (x, y + 2), (x - 2, y)], BLU, 0.4)

    def scroll():
        d.fill([(-14, -10), (14, -10), (14, 10), (-14, 10)], "#ffe2a8")
        for s in (-1, 1):
            d.shape(arc(s * 15, 0, 2.5, 0, 360, 11), "#e8b86a", 0.5)
        d.ink([(-13.96, -10), (13.96, -10)], 0.5)
        d.ink([(-13.96, 10), (13.96, 10)], 0.5)

    def tag():
        d.shape([(-18, 0), (-11, -9), (18, -9), (18, 9), (-11, 9)], PGRN, 0.55)
        d.shape(arc(-11, 0, 1.7), "white", 0.45)
        d.ink(bez((-11, 0), (-16, -6), (-20, -2), (-21, -10)), 0.4)

    def badges():
        for y, c, n in ((-10, BLU, "1"), (0, ORG, "2"), (10, GRN, "3")):
            d.shape(arc(-14, y, 4), c, 0.5)
            d.text(n, -14, y - 2.3, 4.6, w=0.45, hand=False)
            d.ink([(-7, y), (19, y)], 0.35, "gray")

    kinds = [("speech", speech), ("speech box", box_speech), ("thought", thought),
             ("shout", shout), ("whisper", whisper), ("dialogue", dialogue),
             ("banner", banner), ("sticky note", sticky), ("title frame", frame),
             ("scroll", scroll), ("tag", tag), ("numbered list", badges)]
    for i, (name, fn) in enumerate(kinds):
        cx, cy = cols[i % 3], rows[i // 3]
        d.at(cx, cy)
        fn()
        caption(d, name, cx, cy + 17.5)

    # emphasis row
    y = 214
    d.at(33, y)
    d.ink([(-17, 0), (17, 0)], 5.0, "hl_yellow", pen="highlighter", wobble=0)
    d.ink(bez((-18, 5), (-6, 3.5), (6, 4), (18, 3), n=20), 0.7)
    d.ink(bez((-18, 7.5), (-8, 6.5), (4, 7), (12, 6.3), n=20), 0.4)
    caption(d, "highlight & underline", 33, y + 10)
    d.at(90, y)
    d.ink(bez((-12, -7), (-15, -7), (-12, 0), (-16, 0)) + bez((-16, 0), (-12, 0), (-15, 7), (-12, 7))[1:], 0.55)
    d.ink(bez((12, -7), (15, -7), (12, 0), (16, 0)) + bez((16, 0), (12, 0), (15, 7), (12, 7))[1:], 0.55)
    d.ink([(-5, -7), (-7, -7), (-7, 7), (-5, 7)], 0.55)
    d.ink([(5, -7), (7, -7), (7, 7), (5, 7)], 0.55)
    caption(d, "braces & brackets", 90, y + 10)
    d.at(147, y)
    d.ink([(-20, -4), (-3, -4)], 0.45)
    d.ink([(3, -4), (20, -4)], 0.45)
    d.shape([(0, -6.5), (2.5, -4), (0, -1.5), (-2.5, -4)], BLU, 0.4)
    for i in range(9):
        d.dot(-16 + i * 4, 2, 0.9)
    for i in range(5):
        d.at(147 - 12 + i * 6, y + 6.5, 0.22)
        d.shape(star(10, 4.2), YEL, 0.3)
    caption(d, "dividers", 147, y + 10)
    return d.page()


# ---- idea icons -------------------------------------------------------------------------------
def page_icons():
    d = D()
    title(d, "Idea icons", "small symbols for slides, mind maps and sketchnotes")

    def gear():
        pts = []
        for i in range(8):
            a = i * 45
            pts += [(r * math.cos(math.radians(a + da)), r * math.sin(math.radians(a + da)))
                    for da, r in ((-15, 6.8), (-8, 9.4), (8, 9.4), (15, 6.8))]
        d.shape(pts, PBLU, 0.5)
        d.shape(arc(0, 0, 2.8), "white", 0.5)

    def rocket():
        for s in (-1, 1):
            d.shape([(s * 4.4, 0), (s * 8.4, 7), (s * 4.4, 5.6)], RED, 0.45)
        d.shape([(-2.6, 5.8), (0, 11.5), (2.6, 5.8)], ORG, 0.45)
        d.shape(smooth([(0, -13), (4.6, -5), (4.6, 5.8), (-4.6, 5.8), (-4.6, -5)], 2), None, 0.55)
        d.shape(arc(0, -3, 2.0), BLU, 0.45)

    def target():
        for r, c in ((9.5, RED), (6.3, "white"), (3.1, RED)):
            d.shape(arc(0, 0, r), c, 0.45)
        d.ink([(10, -10), (0.6, -0.6)], 0.6, wobble=0)
        d.ink([(10, -10), (10, -6.5)], 0.45, wobble=0)
        d.ink([(10, -10), (6.5, -10)], 0.45, wobble=0)

    def trophy():
        d.ink(arc(-6.2, -5.5, 3, 90, 270), 0.5)
        d.ink(arc(6.2, -5.5, 3, -90, 90), 0.5)
        d.shape(smooth([(-6.8, -9.5), (6.8, -9.5), (6.2, -3), (3, 1.2), (-3, 1.2), (-6.2, -3)], 2), YEL, 0.5)
        d.shape([(-1.3, 1.0), (1.3, 1.0), (1.3, 5), (-1.3, 5)], None, 0.45)
        d.shape(rrect(-5.5, 5, 5.5, 8.6, 0.8), ORG, 0.5)

    def star_():
        d.shape(star(10.5, 4.4), YEL, 0.55)

    def heart():
        pts = []
        for i in range(60):
            t = 2 * math.pi * i / 60
            pts.append((0.6 * 16 * math.sin(t) ** 3,
                        -0.6 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) - 1))
        d.shape(pts, RED, 0.55)

    def check():
        d.ink(rrect(-8.5, -8.5, 8.5, 8.5, 1.5), 0.5, closed=True)
        d.ink([(-5, -0.5), (-1.5, 4.5), (7.5, -9)], 1.2, "green", pen="marker")

    def cross():
        d.shape(arc(0, 0, 9), PRED, 0.5)
        d.ink([(-4.5, -4.5), (4.5, 4.5)], 1.2, "red", pen="marker")
        d.ink([(-4.5, 4.5), (4.5, -4.5)], 1.2, "red", pen="marker")

    def magnifier():
        d.shape(arc(-2.2, -2.2, 6.3), PBLU, 0.6)
        d.ink(arc(-2.2, -2.2, 4, 200, 250), 0.4, wobble=0)
        d.ink([(2.6, 2.6), (9, 9)], 2.0, wobble=0)

    def clock():
        d.ink(arc(0, 0, 9.5), 0.55, closed=True)
        for i in range(12):
            a = math.radians(i * 30)
            r0 = 7.4 if i % 3 else 6.6
            d.ink([(r0 * math.cos(a), r0 * math.sin(a)), (8.4 * math.cos(a), 8.4 * math.sin(a))], 0.35, wobble=0)
        d.ink([(0, 0), (0, -6)], 0.6, wobble=0)
        d.ink([(0, 0), (4.4, 2.2)], 0.6, wobble=0)
        d.dot(0, 0, 1.2)

    def calendar():
        d.shape([(-9, -7.5), (9, -7.5), (9, -2.5), (-9, -2.5)], RED, 0.5)
        d.ink([(-9, -2.5), (-9, 10), (9, 10), (9, -2.5)], 0.5)
        for x in (-5, 5):
            d.ink([(x, -10), (x, -5.5)], 0.8, wobble=0)
        for r in range(3):
            for c in range(4):
                d.dot(-6 + c * 4, 1 + r * 3.5, 0.8)
        d.ink(arc(2, 4.5, 1.9), 0.45, "red", closed=True)

    def bars():
        d.ink([(-10, -10), (-10, 9), (10, 9)], 0.45)
        for x, h, c in ((-8, 5, BLU), (-3, 9, GRN), (2, 13, ORG)):
            d.shape([(x, 9), (x + 4, 9), (x + 4, 9 - h), (x, 9 - h)], c, 0.4)
        d.arrow([(-9, 0), (-3, -4), (2, -6.5), (9.5, -11)], 0.5, s=2.4)

    def pie():
        d.shape(arc(0, 0, 9.5), BLU, 0.5)
        d.shape([(0, 0)] + arc(0, 0, 9.5, -90, 20), ORG, 0.5)

    def coin():
        d.shape(arc(0, 0, 9.5), YEL, 0.55)
        d.ink(arc(0, 0, 7.4), 0.35, closed=True)
        d.text("$", 0, -5, 10, w=0.6, hand=False)

    def cloud():
        base = [(-9, 4), (-10, -1), (-5, -5), (0, -8), (6, -5), (10, -1), (9, 4)]
        top = bumps(base, 0.35, closed=False)
        d.shape(top + [(9, 4)], PBLU, 0.5)

    def lock():
        d.ink([(-4.6, -1)] + arc(0, -4, 4.6, 180, 360) + [(4.6, -1)], 0.9)
        d.shape(rrect(-7, -1, 7, 10, 1.2), YEL, 0.55)
        d.shape(arc(0, 3.4, 1.4), "white", 0.4)
        d.ink([(0, 4.6), (0, 7)], 0.8, wobble=0)

    def document():
        d.ink([(3, -10), (-7, -10), (-7, 10), (8, 10), (8, -5), (3, -10), (3, -5), (8, -5)], 0.5)
        for y in (-5, -2, 1, 4, 7):
            d.ink([(-4.5, y), (4.5 if y > -5 else 0.5, y)], 0.35, "gray")

    def envelope():
        d.shape([(-10, -7), (10, -7), (10, 7), (-10, 7)], PYEL, 0.55)
        d.ink([(-10, -7), (0, 1.5), (10, -7)], 0.5)
        d.ink([(-10, 7), (-3, 0)], 0.35)
        d.ink([(10, 7), (3, 0)], 0.35)

    def flag():
        top = bez((-7, -10), (-1, -13), (3, -7), (10, -9.5))
        bot = bez((10, -1.5), (3, 1), (-1, -5), (-7, -2))
        d.shape(top + bot, RED, 0.5)
        d.ink([(-7, -11), (-7, 11)], 0.8, wobble=0.1)

    def puzzle():
        sq = [(-7, -7), (-2, -7), (2, -7), (7, -7), (7, -2), (7, 2), (7, 7), (-7, 7), (-7, 2), (-7, -2)]
        pts = []
        for a, b, k in zip(sq, sq[1:] + sq[:1], (0, 0.55, 0, 0, 0.55, 0, 0, 0, -0.55, 0)):
            pts += bumps([a, b], k, closed=False, n=12) if k else [a]
        d.shape(pts, PGRN, 0.55)

    def warning():
        d.shape(smooth([(0, -11), (10.5, 8), (-10.5, 8)], 2), YEL, 0.6)
        d.ink([(0, -4.5), (0, 2.5)], 1.1, wobble=0)
        d.dot(0, 5.2, 1.3)

    def question():
        d.shape(arc(0, 0, 9.5), PBLU, 0.55)
        d.text("?", 0, -6, 12, w=0.8, hand=False)

    def lightning():
        d.shape([(2.5, -11), (-6.5, 1.5), (-0.6, 1.5), (-3.5, 11.5), (6.5, -2.2), (0.6, -2.2)], YEL, 0.55)

    def globe():
        d.shape(arc(0, 0, 9.5), PBLU, 0.55)
        d.ink(arc(0, 0, 4.2, -90, 270, 9.5), 0.4, closed=False)
        d.ink([(0, -9.5), (0, 9.5)], 0.4, wobble=0.1)
        d.ink([(-9.5, 0), (9.5, 0)], 0.4, wobble=0.1)
        for y in (-5, 5):
            w = math.sqrt(9.5 ** 2 - y ** 2)
            d.ink(bez((-w, y), (-w / 2, y + 1.2), (w / 2, y + 1.2), (w, y)), 0.35)

    def mountain():
        d.ink([(-1, -7), (-1, -12.5)], 0.5, wobble=0)
        d.shape([(-1, -12.5), (4.5, -11), (-1, -9.3)], RED, 0.4)
        d.shape([(-10.5, 9), (-1, -7), (10.5, 9)], GRY, 0.55)
        snow = [(-1, -7), (-3.95, -2), (-2, -3.2), (-0.5, -1.2), (1, -3.2), (2.6, -2)]
        d.fill(snow, "white")
        d.ink(snow[1:], 0.4)

    def key():
        d.shape(arc(-5, 0, 4.2), YEL, 0.55)
        d.shape(arc(-6, 0, 1.4), "white", 0.4)
        d.ink([(-0.8, 0), (10, 0)], 0.8, wobble=0.1)
        d.ink([(6, 0), (6, 3.2)], 0.8, wobble=0)
        d.ink([(8.8, 0), (8.8, 2.4)], 0.8, wobble=0)

    def megaphone():
        d.shape([(-9, -3), (-5.5, -3), (-5.5, 3), (-9, 3)], GRY, 0.45)
        d.shape([(-5.5, -3), (5.5, -8.5), (5.5, 8.5), (-5.5, 3)], ORG, 0.5)
        d.ink(arc(5.5, 0, 1.5, 0, 360, 8.5), 0.45, closed=True)
        d.ink([(-3, 2), (-2, 7.5), (0.5, 7.5), (0, 0.8)], 0.45)
        for r in (5.5, 8):
            d.ink(arc(5.5, 0, r, -32, 32), 0.45)

    def hourglass():
        d.ink([(-7.5, -10.5), (7.5, -10.5)], 0.9, wobble=0)
        d.ink([(-7.5, 10.5), (7.5, 10.5)], 0.9, wobble=0)
        d.shape([(-4.8, 9.8), (0, 5), (4.8, 9.8)], YEL, 0.3)
        d.shape([(-2.6, -4.2), (2.6, -4.2), (0, -1.2)], YEL, 0.3)
        d.ink([(0, -1.2), (0, 5)], 0.3, wobble=0)
        d.ink(smooth([(-6, -10.5), (6, -10.5), (1, 0), (6, 10.5), (-6, 10.5), (-1, 0)], 2), 0.5, closed=True)

    def group():
        for x, c in ((-7.2, ORG), (0, BLU), (7.2, GRN)):
            d.shape(arc(x, 5.2, 3.3, 180, 360, 4.4), c, 0.45)
            d.ink(arc(x, -2.2, 2.6), 0.5, closed=True)

    def idea():
        bulb(d, rays=True)

    icons = [("idea", idea), ("settings", gear), ("launch", rocket), ("goal", target), ("win", trophy),
             ("star", star_), ("love", heart), ("done", check), ("no", cross), ("search", magnifier),
             ("time", clock), ("date", calendar), ("growth", bars), ("share", pie), ("money", coin),
             ("cloud", cloud), ("secure", lock), ("document", document), ("message", envelope),
             ("milestone", flag), ("fit", puzzle), ("warning", warning), ("question", question),
             ("energy", lightning), ("global", globe), ("summit", mountain), ("key", key),
             ("announce", megaphone), ("deadline", hourglass), ("team", group)]
    for i, (name, fn) in enumerate(icons):
        cx, cy = 26 + (i % 5) * 32, 44 + (i // 5) * 34
        d.at(cx, cy)
        fn()
        caption(d, name, cx, cy + 13)
    return d.page()


def build() -> Document:
    pages = [page_people(), page_arrows(), page_bubbles(), page_icons()]
    doc = from_dict({"name": NAME, "pages": [items for items, _ in pages]})
    for page, (_, strokes) in zip(doc.pages, pages):
        page.strokes.extend(strokes)
    return doc


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    from build_gallery import OUT, publish
    publish(build(), OUT / "symbols" / "doodles", "doodles")
