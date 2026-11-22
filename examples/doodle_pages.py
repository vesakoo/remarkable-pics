"""Template pages for doodles.py: thick arrows, speech bubbles, sticky notes, labels & banners,
shapes. Every element is a solid shape (opaque white base, optional colour) you can write in."""
import math

from doodles import (BLU, DARK, GRN, LGRY, ORG, PBLU, PGRN, PORG, PRED, PYEL, RED, YEL, D,
                     arc, bez, bumps, caption, dens, rot, rrect, smooth, star, title)


# ---- helpers -----------------------------------------------------------------------------------
def thick(c, w, hw=None, hl=None, tail="flat", both=False, w_end=None):
    """Outline polygon of a fat arrow along centre line `c` (shaft width w, head width hw,
    head length hl). tail: flat | notch | fish. w_end tapers the shaft from w to w_end."""
    hw = hw or 2 * w
    hl = hl or 0.9 * w
    w_end = w if w_end is None else w_end
    c = dens(c, 0.4)
    s = [0.0]
    for a, b in zip(c, c[1:]):
        s.append(s[-1] + math.dist(a, b))
    L = s[-1]

    def at(d):
        d = max(0.0, min(L, d))
        for i in range(1, len(c)):
            if s[i] >= d:
                a, b = c[i - 1], c[i]
                t = (d - s[i - 1]) / max(1e-9, s[i] - s[i - 1])
                tx, ty = b[0] - a[0], b[1] - a[1]
                tl = math.hypot(tx, ty) or 1.0
                return (a[0] + tx * t, a[1] + ty * t), (tx / tl, ty / tl)
        return c[-1], (1.0, 0.0)

    s0, s1 = (hl if both else 0.0), L - hl
    n = max(2, int((s1 - s0) / 0.5))
    left, right = [], []
    for i in range(n + 1):
        d = s0 + (s1 - s0) * i / n
        (px, py), (tx, ty) = at(d)
        ww = (w + (w_end - w) * (d - s0) / max(1e-9, s1 - s0)) / 2
        left.append((px - ty * ww, py + tx * ww))
        right.append((px + ty * ww, py - tx * ww))
    (px, py), (tx, ty) = at(s1)
    poly = left + [(px - ty * hw / 2, py + tx * hw / 2), c[-1], (px + ty * hw / 2, py - tx * hw / 2)]
    poly += right[::-1]
    (px, py), (tx, ty) = at(s0)
    if both:
        poly += [(px + ty * hw / 2, py - tx * hw / 2), c[0], (px - ty * hw / 2, py + tx * hw / 2)]
    elif tail == "notch":
        poly.append((px + tx * w * 0.6, py + ty * w * 0.6))
    elif tail == "fish":
        f = w * 0.95
        poly += [(px + ty * f - tx * 4, py - tx * f - ty * 4), (px - tx * 0.5, py - ty * 0.5),
                 (px - ty * f - tx * 4, py + tx * f - ty * 4)]
    return poly


def lines(d, x0, x1, ys, color="gray", w=0.35):
    for y in ys:
        d.ink([(x0, y), (x1, y)], w, color, wobble=0.08)


def steps(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def grid(d, items, cols, rows, dy):
    for i, (name, fn) in enumerate(items):
        cx, cy = cols[i % len(cols)], rows[i // len(cols)]
        d.at(cx, cy)
        fn(d)
        caption(d, name, cx, cy + dy)


def ell_bubble(cx, cy, rx, ry, g0, g1, tip):
    return arc(cx, cy, rx, g1, g0 + 360, ry, step=5) + [tip]


# ---- thick arrows ------------------------------------------------------------------------------
def page_arrows():
    d = D()
    title(d, "Arrows", "solid, wide enough to write in - lasso, rotate, stretch")

    def chevrons(d):
        for x, c in ((-17, PBLU), (-6, PGRN), (5, PORG)):
            d.shape([(x, -7), (x + 7, -7), (x + 12, 0), (x + 7, 7), (x, 7), (x + 5, 0)], c, 0.5)

    def quad(d):
        s, L, hl, h = 3.0, 13.5, 5.5, 6.5
        pts = []
        for k in range(4):
            pts += rot([(s, -s), (L - hl, -s), (L - hl, -h), (L, 0), (L - hl, h), (L - hl, s)], 90 * k)
        d.shape(pts, PYEL, 0.5)

    def shadow3d(d):
        a = thick([(-17, 0), (15, 0)], 9, 18, 10)
        d.shape([(x + 1.8, y + 1.8) for x, y in a], DARK, 0.4)
        d.shape(a)

    def striped(d):
        for x in (-17.5, -14):
            d.shape([(x, -4), (x + 2, -4), (x + 2, 4), (x, 4)], ORG, 0.4)
        d.shape(thick([(-10.5, 0), (17, 0)], 8, 17, 9), ORG, 0.5)

    def callout(d):
        d.shape([(-17, -11), (3, -11), (3, -4), (9, -4), (9, -9), (17, 0), (9, 9), (9, 4), (3, 4),
                 (3, 11), (-17, 11)], None, 0.55)

    def rank(d):
        for y, c in ((5, PGRN), (-2, GRN), (-9, "#2a9a45")):
            d.shape([(-11, y + 3), (0, y - 6), (11, y + 3), (11, y + 8), (0, y - 1), (-11, y + 8)], c, 0.5)

    def cycle(d):
        d.shape(thick(arc(0, 0, 10, 195, 335), 5, 10, 5.5), PBLU, 0.5)
        d.shape(thick(arc(0, 0, 10, 15, 155), 5, 10, 5.5), PORG, 0.5)

    def exchange(d):
        d.shape(thick([(-17, -5.5), (17, -5.5)], 5.5, 11, 6))
        d.shape(thick([(17, 6), (-17, 6)], 5.5, 11, 6), PBLU)

    kinds = [
        ("block", lambda d: d.shape(thick([(-17, 0), (17, 0)], 10, 19, 10))),
        ("notched", lambda d: d.shape(thick([(-17, 0), (17, 0)], 10, 19, 10, "notch"), PBLU)),
        ("two-way", lambda d: d.shape(thick([(-17, 0), (17, 0)], 9, 17, 8, both=True))),
        ("fishtail", lambda d: d.shape(thick([(-14, 0), (17, 0)], 8, 17, 9, "fish"), PYEL)),
        ("curved", lambda d: d.shape(thick(bez((-16, 9), (-8, -13), (8, -13), (16, 7)), 6.5, 13, 7), PORG)),
        ("u-turn", lambda d: d.shape(thick([(10, 11), (10, -1)] + arc(0, -1, 10, 0, -180)[1:] + [(-10, 9)],
                                          6, 13, 6.5), PGRN)),
        ("cycle", cycle),
        ("refresh", lambda d: d.shape(thick(arc(0, 0, 9.5, -50, 245), 5, 11, 6), PBLU)),
        ("growth", lambda d: d.shape(thick(smooth([(-17, 10), (-7, 1), (-1, 5), (15, -10)], 2, closed=False),
                                           5.5, 12, 7), PGRN)),
        ("swoosh", lambda d: d.shape(thick(bez((-17, 9), (-6, 11), (7, 5), (15, -9)), 1.5, 13, 7.5,
                                           w_end=7), PRED)),
        ("elbow", lambda d: d.shape(thick(smooth([(-17, -9), (7, -9), (7, 12)], 3, closed=False), 7, 14, 7),
                                    PBLU)),
        ("s-curve", lambda d: d.shape(thick(bez((-17, 7), (-6, -15), (4, 15), (17, -6)), 6, 12, 7),
                                      None, 0.55, wobble=0.3)),
        ("3d", shadow3d), ("four-way", quad), ("striped", striped), ("exchange", exchange),
        ("process", chevrons), ("step", lambda d: d.shape(
            [(-17, -9), (9, -9), (17, 0), (9, 9), (-17, 9), (-12, 0)], PYEL, 0.55)),
        ("callout", callout), ("level up", rank),
    ]
    grid(d, kinds, (30, 70, 110, 150), (46, 85, 124, 163, 202), 14)
    return d.page()


# ---- speech bubbles ----------------------------------------------------------------------------
def page_bubbles():
    d = D()
    title(d, "Speech bubbles", "solid white inside: write on top of anything")

    def cloud_speech(d):
        d.shape([(-8, 4), (-2, 4), (-13, 16)])
        d.shape(bumps(arc(0, -3, 18, 0, 330, 10, step=30), 0.3))

    def thought(d):
        d.shape(bumps(arc(0, -4, 17, 0, 324, 9.5, step=36), 0.32))
        d.shape(arc(-11, 9, 2.4))
        d.shape(arc(-15, 13.5, 1.4))

    def box(d):
        d.shape([(-9, 4), (-3, 4), (-13, 16)])
        d.shape(rrect(-20, -14, 20, 7, 4))

    def tilted(d):
        d.shape([(-10, 6), (-3, 6), (-13, 16)])
        d.shape([(-20, -11), (18, -15), (20, 8), (-18, 9)])

    def shout(d):
        d.shape([(x, y * 0.74) for x, y in star(21, 14, 11, rot=-80)], PYEL, 0.6)

    def lightning(d):
        d.shape([(-4, 2), (3, 2), (0, 8), (5, 8), (-8, 17), (-2, 10), (-7, 10)])
        d.shape(rrect(-20, -14, 20, 6, 4))

    def dialogue(d):
        d.shape(ell_bubble(7, -6, 14, 9, 50, 70, (20, 6)), PBLU)
        d.shape(ell_bubble(-6, 6, 14, 9, 110, 130, (-17, 17)))

    def whisper(d):
        pts = ell_bubble(0, -3, 19, 12, 60, 78, (13, 14))
        d.fill(pts)
        d.dashed(pts + [pts[0]], 0.5)

    def round_side(d):
        d.shape([(-9, 0), (-6, 8), (-21, 10)])
        d.shape(arc(3, -2, 14))

    def top_tail(d):
        d.shape([(5, -9), (12, -9), (15, -18)])
        d.shape(rrect(-20, -11, 20, 13, 3))
        d.ink(rrect(-18, -9, 18, 11, 2), 0.3, closed=True)

    def scallop(d):
        d.shape([(-8, 5), (-2, 5), (-14, 16)])
        d.shape(bumps(arc(0, -3, 19, 0, 340, 11, step=20), 0.18))

    def double_oval(d):
        d.shape(ell_bubble(0, -3, 20, 12, 100, 118, (-12, 15)), PORG)
        d.ink(arc(0, -3, 17.5, 0, 360, 9.5), 0.3, closed=True)

    kinds = [("oval", lambda d: d.shape(ell_bubble(0, -3, 20, 12, 100, 118, (-12, 15)))),
             ("cloud", cloud_speech), ("thought", thought), ("box", box), ("tilted", tilted),
             ("shout", shout), ("on the phone", lightning), ("dialogue", dialogue),
             ("whisper", whisper), ("round", round_side), ("framed", top_tail),
             ("scalloped", scallop)]
    grid(d, kinds, (33, 90, 147), (48, 90, 132, 174), 19)
    # one wide row: a long banner bubble and a double-line oval
    d.at(62, 214)
    d.shape([(-28, 3), (-21, 3), (-33, 10)])
    d.shape(rrect(-30, -8, 30, 5, 6.5))
    caption(d, "wide", 62, 222)
    d.at(140, 213, 0.75)
    double_oval(d)
    caption(d, "double line", 140, 226)
    return d.page()


# ---- sticky notes ------------------------------------------------------------------------------
def page_notes():
    d = D()
    title(d, "Sticky notes", "notes, lists and cards with solid backgrounds")
    ys = steps(-12, 14, 6)

    def taped(d):
        d.shape([(-17, -21), (17, -21), (17, 21), (-17, 21)])
        lines(d, -10, 11, ys)
        for cx, cy in ((-17, -21), (17, 21)):
            d.shape([(cx + x, cy + y) for x, y in rot([(-8, -2.5), (8, -2.5), (8, 2.5), (-8, 2.5)], -40)],
                    LGRY, 0.35)

    def folded(d):
        d.shape([(-19, -20), (19, -20), (19, 22), (-12, 22), (-19, 15)])
        d.shape([(-19, 15), (-12, 15), (-12, 22)], LGRY, 0.4)
        d.shape([(-7, -23.5), (7, -23.5), (7, -18), (-7, -18)], DARK, 0.4)
        lines(d, -13, 13, steps(-12, 10, 5))

    def clipped(d):
        d.shape([(-16, -17), (21, -17), (21, 22), (-16, 22)])
        d.shape([(-20, -20), (18, -20), (18, 19), (-20, 19)])
        lines(d, -12, 13, steps(-11, 13, 5))
        d.ink(rrect(-17, -25, -12, -8, 2.5), 0.55, closed=True)
        d.ink(rrect(-15.6, -23, -13.4, -12, 1.1), 0.45, closed=True)

    def checklist(d):
        d.shape([(-16, -18), (22, -18), (22, 24), (-16, 24)], DARK, 0.4)
        d.shape([(-19, -21), (19, -21), (19, 21), (-19, 21)])
        d.shape([(-3, -25), (3, -25), (3, -17), (-3, -17)], LGRY, 0.4)
        for y in steps(-13, 15, 6):
            d.ink(arc(-13.5, y, 1.3), 0.4, closed=True, wobble=0)
            d.ink([(-10, y), (14, y)], 0.35, "gray", wobble=0.08)

    def clipboard(d):
        d.shape(rrect(-18, -22, 18, 25, 2.2), "#d9a066", 0.55)
        d.shape([(-15, -17), (15, -17), (15, 22), (-15, 22)])
        d.shape(rrect(-7, -25.5, 7, -18.5, 1.5), GRY_, 0.5)
        d.ink(arc(0, -23, 1.1), 0.4, closed=True, wobble=0)
        for y in steps(-11, 16, 6):
            d.ink(arc(-10.5, y, 1.2), 0.4, closed=True, wobble=0)
            d.ink([(-7.5, y), (11, y)], 0.35, "gray", wobble=0.08)

    def pinned(d):
        d.shape(rot([(-17, -19), (17, -19), (17, 21), (-17, 21)], 7))
        d.shape(rot([(-17, -19), (17, -19), (17, 21), (-17, 21)], -4))
        d.shape([(-17, -20), (17, -20), (17, 20), (-17, 20)])
        lines(d, -11, 12, steps(-10, 14, 5))
        d.ink([(0, -17), (1.5, -12.5)], 0.5, wobble=0)
        d.shape(arc(0, -19, 2.6), RED, 0.45)

    def sticky(d):
        d.shape([(-18, -18), (18, -18), (18, 11), (11, 18), (-18, 18)], PYEL, 0.5)
        d.shape([(18, 11), (11, 18), (11, 11)], YEL, 0.4)

    def notebook(d):
        torn = [(x, 23 + (1.2 if i % 2 else -0.6)) for i, x in enumerate(steps(19, -19, 15))]
        d.shape([(-19, -20), (19, -20)] + torn)
        lines(d, -15, 15, steps(-8, 18, 6), "blue", 0.25)
        d.ink([(-12, -20), (-12, 21.5)], 0.3, "red", wobble=0.05)
        for x in steps(-14, 14, 6):
            d.shape(arc(x, -16.5, 1.1), "white", 0.35)
            d.ink(arc(x, -18.5, 2.0, 90, 270, 3.0), 0.55, wobble=0)

    def card(d):
        d.shape([(-22, -15), (22, -15), (22, 15), (-22, 15)])
        d.ink([(-22, -8), (22, -8)], 0.35, "red", wobble=0.05)
        lines(d, -19, 19, steps(-2, 11, 4), "blue", 0.25)

    kinds = [("taped", taped), ("folded corner", folded), ("paper clip", clipped),
             ("checklist", checklist), ("clipboard", clipboard), ("pinned stack", pinned),
             ("sticky", sticky), ("notebook page", notebook), ("index card", card)]
    grid(d, kinds, (34, 90, 146), (62, 131, 200), 29)
    return d.page()


GRY_ = "#9e9e9e"


# ---- labels & banners ----------------------------------------------------------------------------
def ribbon_ends(d, front, y0, y1, xe, fold=True, color="white"):
    """Folded ribbon tails behind a band whose ends are at x=±xe (band from y0 to y1)."""
    for s in (-1, 1):
        m = lambda pts: [(s * x, y) for x, y in pts]
        h = y1 - y0
        d.shape(m([(-xe + 6, y0 + 4), (-xe - 8, y0 + 4), (-xe - 4, y0 + 4 + h / 2),
                   (-xe - 8, y1 + 4), (-xe + 6, y1 + 4)]), color, 0.5)
        if fold:
            d.shape(m([(-xe, y1), (-xe + 6, y1), (-xe + 6, y1 + 4)]), DARK, 0.4)
    d.shape(front, color, 0.55)


def page_labels():
    d = D()
    title(d, "Labels & banners", "ribbons, tags and plaques - solid, ready to letter")

    def banner(d):
        ribbon_ends(d, [(-30, -7), (30, -7), (30, 5), (-30, 5)], -7, 5, 30)

    def wavy(d):
        top = [(x, -7 + 3 * math.sin(math.pi * x / 30)) for x in steps(-30, 30, 31)]
        bot = [(x, y + 12) for x, y in top[::-1]]
        ribbon_ends(d, top + bot, -7, 5, 30)

    def arched(d):
        for s in (-1, 1):
            m = lambda pts: [(s * x, y) for x, y in pts]
            d.shape(m([(-24, 1), (-38, 6), (-33, 10), (-36, 16), (-22, 12)]), None, 0.5)
            d.shape(m([(-26.3, 5.6), (-22, 12), (-21, 6)]), DARK, 0.4)
        top = arc(0, 58, 64, -117, -63, step=2)
        bot = arc(0, 58, 52, -63, -117, step=2)
        d.shape(top + bot, None, 0.55)

    def rosette(d):
        for s in (-1, 1):
            m = lambda pts: [(s * x, y) for x, y in pts]
            d.shape(m([(-1, 2), (-7, 0), (-11, 19), (-7, 16), (-4, 20)]), PRED, 0.45)
        d.shape(bumps(arc(0, -5, 12, 0, 340, step=20), 0.22), PYEL, 0.5)
        d.shape(arc(0, -5, 9))

    def tag(d):
        t = rot([(-6, -14), (6, -14), (6, 12), (-6, 12), (-11, -1)], 0)
        pts = rot([(0, -16), (9, -9), (9, 13), (-9, 13), (-9, -9)], 40)
        d.shape(pts)
        hx, hy = rot([(0, -9.5)], 40)[0]
        d.shape(arc(hx, hy, 1.5), None, 0.4)
        d.ink(bez((hx, hy), (hx + 3, hy - 9), (hx + 12, hy - 6), (hx + 6, hy + 2)), 0.45)

    def pennant(d):
        d.shape([(-10, -20), (10, -20), (10, 20), (0, 12), (-10, 20)], PBLU)

    def plaque(d):
        a, b, r = 26, 11, 4
        pts = ([(-a + r, -b), (a - r, -b)] + arc(a, -b, r, 180, 90) + [(a, b - r)] + arc(a, b, r, 270, 180)
               + [(-a + r, b)] + arc(-a, b, r, 0, -90) + [(-a, -b + r)] + arc(-a, -b, r, 90, 0))
        d.shape(pts)
        d.ink([(x * 0.88, y * 0.78) for x, y in pts], 0.3, closed=True)

    def hexa(d):
        d.shape(smooth([(-26, 0), (-17, -11), (17, -11), (26, 0), (17, 11), (-17, 11)], 1), PGRN)

    def seal(d):
        d.shape(bumps(arc(0, 0, 13, 0, 337.5, step=22.5), 0.25))
        d.dashed(arc(0, 0, 10), 0.4)

    def rod(d):
        d.ink([(-27, 0), (27, 0)], 0.5)
        d.shape(rrect(-20, -6.5, 20, 6.5, 6.5))

    def dashed_pill(d):
        d.shape(rrect(-26, -9, 26, 9, 9))
        d.dashed(rrect(-23.5, -6.5, 23.5, 6.5, 6.5) + [(-16.99, -6.5)], 0.4)

    def arch(d):
        pts = [(-22, 12), (22, 12), (22, -3)] + arc(0, -3, 22, 0, -180, 10)[1:] + [(-22, -3)]
        d.shape(pts, PORG)
        inner = [(-19, 9.5), (19, 9.5), (19, -3)] + arc(0, -3, 19, 0, -180, 7.5)[1:] + [(-19, -3)]
        d.fill(inner)
        d.dashed(inner + [inner[0]], 0.4)

    rows = [((62, 50, banner, "banner"), (148, 50, rosette, "rosette")),
            ((62, 92, wavy, "wavy ribbon"), (148, 92, tag, "tag")),
            ((62, 134, arched, "arched ribbon"), (148, 134, pennant, "pennant")),
            ((38, 176, plaque, "plaque"), (96, 176, hexa, "badge"), (150, 176, seal, "seal")),
            ((38, 212, rod, "scroll bar"), (96, 212, dashed_pill, "stitched"), (150, 212, arch, "arch"))]
    for row in rows:
        for cx, cy, fn, name in row:
            d.at(cx, cy)
            fn(d)
            dy = {"rosette": 23, "pennant": 23.5, "tag": 19.5, "arched ribbon": 19.5}.get(name, 15)
            caption(d, name, cx, cy + dy)
    return d.page()


# ---- shapes --------------------------------------------------------------------------------------
def poly_n(n, r, rot0=-90.0, rx=1.0):
    return [(r * rx * math.cos(math.radians(rot0 + 360 * i / n)), r * math.sin(math.radians(rot0 + 360 * i / n)))
            for i in range(n)]


def page_shapes():
    d = D()
    title(d, "Shapes", "solid blocks for diagrams and boards")

    def cylinder(d):
        d.shape([(12, -8)] + arc(0, 8, 12, 0, 180, 4) + [(-12, -8)])
        d.shape(arc(0, -8, 12, 0, 360, 4))

    def heart(d):
        pts = []
        for i in range(60):
            t = 2 * math.pi * i / 60
            pts.append((0.7 * 16 * math.sin(t) ** 3,
                        -0.7 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) - 1))
        d.shape(pts)

    def shield(d):
        d.shape([(-11, -11), (11, -11), (11, 0)] + bez((11, 0), (11, 7), (4, 10), (0, 13))[1:]
                + bez((0, 13), (-4, 10), (-11, 7), (-11, 0))[1:])

    def cloud(d):
        d.shape(bumps(arc(0, 0, 15, 0, 320, 8, step=40), 0.3))

    kinds = [
        ("rounded", lambda d: d.shape(rrect(-12, -12, 12, 12, 4))),
        ("card", lambda d: d.shape(rrect(-17, -10, 17, 10, 4))),
        ("triangle", lambda d: d.shape([(0, -13), (14, 11), (-14, 11)])),
        ("arch", lambda d: d.shape([(-12, 12), (12, 12), (12, -1)] + arc(0, -1, 12, 0, -180)[1:] + [(-12, -1)])),
        ("rectangle", lambda d: d.shape([(-17, -10), (17, -10), (17, 10), (-17, 10)])),
        ("burst", lambda d: d.shape(star(13, 9.5, 12))),
        ("wavy circle", lambda d: d.shape(bumps(poly_n(16, 11.5), 0.18))),
        ("octagon", lambda d: d.shape(poly_n(8, 12.5, -67.5))),
        ("cut corners", lambda d: d.shape([(-13, -10), (13, -10), (17, -6), (17, 6), (13, 10), (-13, 10),
                                          (-17, 6), (-17, -6)])),
        ("pentagon", lambda d: d.shape(poly_n(5, 13))),
        ("hexagon", lambda d: d.shape(poly_n(6, 13, 0, 1.15))),
        ("circle", lambda d: d.shape(arc(0, 0, 12))),
        ("diamond", lambda d: d.shape([(0, -13), (15, 0), (0, 13), (-15, 0)])),
        ("parallelogram", lambda d: d.shape([(-12, -10), (18, -10), (12, 10), (-18, 10)])),
        ("cylinder", cylinder), ("heart", heart), ("shield", shield), ("cloud", cloud),
        ("trapezoid", lambda d: d.shape([(-10, -10), (10, -10), (17, 10), (-17, 10)])),
        ("star", lambda d: d.shape(star(13.5, 5.6))),
    ]
    grid(d, kinds, (30, 70, 110, 150), (46, 84, 122, 160, 198), 15)
    d.at(90, 224)
    d.shape(rrect(-75, -3.5, 75, 3.5, 3.5))
    return d.page()
