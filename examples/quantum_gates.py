"""Quantum circuit symbol library: gates, kets/bras, Bell states, Bloch spheres, 1-6 qubit templates.

    .venv/bin/python examples/quantum_gates.py        # -> out/symbols/quantum-gates/

Theme follows a classic circuit-composer palette: light-blue rounded gate tiles with a blue
border and bold black labels; black control dots, open controls, (+) targets and swap crosses.
Everything is sized to the templates: gate tiles are GATE mm, qubit wires are ROW mm apart,
so a lassoed gate pastes straight onto a wire and multi-qubit gates span the right rows.
"""
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from HersheyFonts import HersheyFonts  # noqa: E402

from rmdraw.model import Document, Stroke  # noqa: E402
from rmdraw.shapes_json import from_dict  # noqa: E402

NAME = "Quantum gates & symbols"
TILE = "#8ab8ff"   # gate fill (one step stronger than on screen: the tablet mutes colours)
EDGE = "blue"      # gate border pen
GATE = 11.0        # gate tile size, mm
ROW = 20.0         # wire spacing, mm
STEP = 15.0        # column spacing in templates, mm
DOT = 1.9          # control dot radius
TGT = 3.6          # target (+) radius

_FONTS = {}
_CAP_TOP, _BASE = -12.0, 9.0


def _font(name):
    if name not in _FONTS:
        f = HersheyFonts()
        f.load_default_font(name)
        _FONTS[name] = f
    return _FONTS[name]


class Ink:
    """Collects one page: shape items (rmdraw JSON) underneath, pen strokes (text, symbols) on top."""

    def __init__(self):
        self.items, self.strokes = [], []

    # ---- shapes -------------------------------------------------------------------------
    def rect(self, x, y, w, h, fill=TILE, edge=EDGE, rx=1.3, width=0.5, outline=True):
        it = {"type": "rect", "x": x, "y": y, "w": w, "h": h, "rx": rx, "color": edge,
              "width_mm": width}
        if fill:
            it["fill"] = {"color": fill}
        if not outline:
            it["outline"] = False
        self.items.append(it)

    def line(self, pts, width=0.45, color="black"):
        self.items.append({"type": "polyline", "points": [list(p) for p in pts],
                           "width_mm": width, "color": color})

    def dashed(self, a, b, width=0.35, color="gray", on=1.4, off=1.1):
        L = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        t = 0.0
        while t < L:
            t1 = min(t + on, L)
            self.line([(a[0] + ux * t, a[1] + uy * t), (a[0] + ux * t1, a[1] + uy * t1)],
                      width, color)
            t = t1 + off

    def circle(self, cx, cy, r, fill=None, width=0.45):
        it = {"type": "circle", "cx": cx, "cy": cy, "r": r, "width_mm": width}
        if fill:
            it["fill"] = {"color": fill}
        self.items.append(it)

    # ---- quantum symbols ---------------------------------------------------------------
    def control(self, cx, cy, open_=False):
        self.circle(cx, cy, DOT, fill="white" if open_ else "black")

    def target(self, cx, cy):
        self.circle(cx, cy, TGT, fill="white", width=0.5)
        self.line([(cx - TGT, cy), (cx + TGT, cy)], 0.5)
        self.line([(cx, cy - TGT), (cx, cy + TGT)], 0.5)

    def cross(self, cx, cy, s=2.6):
        self.line([(cx - s, cy - s), (cx + s, cy + s)], 0.7)
        self.line([(cx - s, cy + s), (cx + s, cy - s)], 0.7)

    def meter(self, cx, cy, w=11.0, h=8.5):
        self.rect(cx - w / 2, cy - h / 2, w, h, fill="white", edge="black", rx=1.0, width=0.45)
        r = w * 0.32
        self.items.append({"type": "arc", "cx": cx, "cy": cy + h * 0.3, "r": r,
                           "start_deg": 195, "end_deg": 345, "width_mm": 0.4})
        self.line([(cx, cy + h * 0.3), (cx + r * 0.75, cy - h * 0.3)], 0.4)

    def gate(self, cx, cy, label, w=GATE, h=GATE, size=None):
        self.rect(cx - w / 2, cy - h / 2, w, h)
        self.label(label, cx, cy, size or (4.6 if len(_plain(label)) <= 1 else
                                          3.6 if len(_plain(label)) == 2 else 2.6))

    # ---- text ----------------------------------------------------------------------------
    def label(self, segs, cx, cy, h, color="black", width=None):
        """Bold label centred on (cx, cy)."""
        st, w = run(segs, 0, 0, h, color, width or max(0.3, h * 0.12))
        self.strokes += shift(st, cx - w / 2, cy - h / 2)

    def text(self, segs, x, y, h, align="left", color="black", width=None):
        st, w = run(segs, 0, 0, h, color, width or max(0.22, h * 0.1))
        dx = {"left": x, "center": x - w / 2, "right": x - w}[align]
        self.strokes += shift(st, dx, y)
        return w

    def page(self):
        return self.items, self.strokes


def _plain(segs):
    return segs if isinstance(segs, str) else "".join(
        s if isinstance(s, str) else ("" if s[0] in ("dag", "sqrt") else s[1]) for s in segs)


def shift(strokes, dx, dy):
    return [Stroke([(x + dx, y + dy) for x, y in s.points], pen=s.pen, color=s.color,
                   width_mm=s.width_mm) for s in strokes]


def _chaikin(pts, n=2):
    for _ in range(n):
        if len(pts) < 3:
            return pts
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            out += [(0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by),
                    (0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by)]
        out.append(pts[-1])
        pts = out
    return pts


def _handify(polys, ch, i, k):
    """Casual hand-lettering look: round corners, slant, small per-letter wobble (deterministic)."""
    rnd = random.Random(f"{ch}|{i}")
    rot = math.radians(rnd.uniform(-4.0, 4.0))
    sc = rnd.uniform(0.95, 1.05)
    dy = rnd.uniform(-0.9, 0.9)
    out = []
    for p in polys:
        q = []
        for px, py in _chaikin(p):
            py2 = py - 0.0
            px, py2 = px * math.cos(rot) - py2 * math.sin(rot), px * math.sin(rot) + py2 * math.cos(rot)
            px, py2 = px * sc, py2 * sc + dy
            px += (_BASE - py2) * 0.12        # slant
            q.append((px, py2))
        out.append(q)
    return out


HAND = [False]   # set HAND[0] = True to letter text by hand


def glyphs(s, x, y, h, font, color, width, hand=None):
    """Hershey text with its cap top at y; returns (strokes, advance).

    hand=True gives a casual hand-lettered look (rounded, slanted, slightly uneven)."""
    f = _font(font)
    k = h / (_BASE - _CAP_TOP)
    hand = HAND[0] if hand is None else hand
    out, cx = [], x
    for n, ch in enumerate(s):
        gs = list(f.glyphs_for_text(ch))
        if not gs:
            cx += 8 * k
            continue
        polys = []
        for a, b in f.lines_for_text(ch):
            a, b = (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
            if polys and math.dist(polys[-1][-1], a) < 1e-6:
                polys[-1].append(b)
            else:
                polys.append([a, b])
        if hand:
            polys = _handify(polys, ch, n + int(cx * 7), k)
        for p in polys:
            out.append(Stroke([(cx + px * k, y + (py - _CAP_TOP) * k) for px, py in p],
                              color=color, width_mm=width))
        cx += gs[0].char_width * k
    return out, cx - x


def run(segs, x, y, h, color="black", width=0.3):
    """Draw a list of segments left to right; returns (strokes, total width).

    A segment is plain text, or a tuple: ("greek", "b") Greek letters (b=beta, F=Phi, Y=Psi),
    ("sub", "00") subscript, ("dag",) dagger, ("sqrt", inner_segs) square root,
    ("ket", inner_segs) |...>, ("bra", inner_segs) <...|.
    """
    if isinstance(segs, str):
        segs = [segs]
    out, cx = [], x
    pad = h * 0.18
    for seg in segs:
        if isinstance(seg, str):
            st, w = glyphs(seg, cx, y, h, "futural", color, width)
        elif seg[0] == "greek":
            st, w = glyphs(seg[1], cx, y, h, "greek", color, width)
        elif seg[0] in ("sub", "sup"):
            yy = y + h * 0.55 if seg[0] == "sub" else y - h * 0.32
            if isinstance(seg[1], str):
                st, w = glyphs(seg[1], cx, yy, h * 0.62, "futural", color, width * 0.85)
            else:
                st, w = run(seg[1], cx, yy, h * 0.62, color, width * 0.85)
            w += h * 0.08
        elif seg[0] == "dag":
            s = h * 0.62
            x0 = cx + h * 0.22
            st = [Stroke([(x0, y - h * 0.25), (x0, y - h * 0.25 + s)], color=color, width_mm=width),
                  Stroke([(x0 - s * 0.32, y - h * 0.25 + s * 0.3),
                          (x0 + s * 0.32, y - h * 0.25 + s * 0.3)], color=color, width_mm=width)]
            w = h * 0.5
        elif seg[0] == "sqrt":
            inner, iw = run(seg[1], cx + h * 0.75, y, h, color, width)
            top = y - h * 0.22
            st = [Stroke([(cx, y + h * 0.55), (cx + h * 0.2, y + h * 0.45),
                          (cx + h * 0.45, y + h * 1.05), (cx + h * 0.65, top),
                          (cx + h * 0.75 + iw + h * 0.1, top)], color=color, width_mm=width)] + inner
            w = h * 0.85 + iw
        elif seg[0] in ("ket", "bra"):
            lo, hi = y - h * 0.28, y + h * 1.28
            bw = h * 0.38
            if seg[0] == "ket":
                inner, iw = run(seg[1], cx + pad * 2, y, h, color, width)
                xe = cx + pad * 2 + iw + pad
                st = [Stroke([(cx + pad, lo), (cx + pad, hi)], color=color, width_mm=width),
                      Stroke([(xe, lo), (xe + bw, (lo + hi) / 2), (xe, hi)], color=color,
                             width_mm=width)] + inner
                w = xe + bw + pad - cx
            else:
                inner, iw = run(seg[1], cx + pad + bw + pad, y, h, color, width)
                xb = cx + pad + bw + pad + iw + pad
                st = [Stroke([(cx + pad + bw, lo), (cx + pad, (lo + hi) / 2), (cx + pad + bw, hi)],
                             color=color, width_mm=width),
                      Stroke([(xb, lo), (xb, hi)], color=color, width_mm=width)] + inner
                w = xb + pad - cx
        else:
            raise ValueError(seg)
        out += st
        cx += w
    return out, cx - x


def ket(*s):
    return ("ket", list(s))


def bra(*s):
    return ("bra", list(s))


# ---- page 1: gates ------------------------------------------------------------------------
SINGLE = [
    ["H", "X", "Y", "Z", "S", "T", "SX", "B", "I", "P"],
    [["S", ("dag",)], ["T", ("dag",)], ["SX", ("dag",)], "RX", "RY", "RZ", "U", "M",
     [ket("0")], None],
]


def page_gates():
    p = Ink()
    p.text("Quantum gates", 90, 10, 6.5, align="center", width=0.6)
    p.text("Lasso a gate, copy, paste it on a wire. Tiles fit the circuit templates.",
           90, 19, 2.6, align="center", color="gray")

    p.text("Single-qubit gates", 12, 28, 3.4, width=0.4)
    for r, row in enumerate(SINGLE):
        cy = 41 + r * 16
        for c, g in enumerate(row):
            cx = 17 + c * 16
            if g is None:      # barrier: dashed box
                for a, b in (((cx - 5.5, cy - 5.5), (cx + 5.5, cy - 5.5)),
                             ((cx + 5.5, cy - 5.5), (cx + 5.5, cy + 5.5)),
                             ((cx + 5.5, cy + 5.5), (cx - 5.5, cy + 5.5)),
                             ((cx - 5.5, cy + 5.5), (cx - 5.5, cy - 5.5))):
                    p.dashed(a, b, 0.4)
                p.dashed((cx, cy - 3.5), (cx, cy + 3.5), 0.4, on=0.8, off=0.8)
            elif isinstance(g, list) and g and isinstance(g[0], tuple) and g[0][0] == "ket":
                p.gate(cx, cy, g, size=3.4)
            else:
                p.gate(cx, cy, g, size=4.6 if len(_plain(g)) <= 1 else 3.8 if len(_plain(g)) == 2
                       else 3.0)
    for c, name in enumerate(["Hadamard", "Pauli X", "Pauli Y", "Pauli Z", "phase", "pi/8",
                              "sqrt X", "", "identity", "phase"]):
        if name:
            p.text(name, 17 + c * 16, 48.5, 1.7, align="center", color="gray")
    for c, name in enumerate(["", "", "", "rot X", "rot Y", "rot Z", "", "measure",
                              "reset", "barrier"]):
        if name:
            p.text(name, 17 + c * 16, 64.5, 1.7, align="center", color="gray")

    p.text("Multi-qubit gates", 12, 74, 3.4, width=0.4)
    top = 86
    cols = [("CX", "cnot"), ("CZ", "cz"), ("CCX", "toffoli"), ("CXC", "cxc"),
            ("SWAP", "swap"), ("CSWAP", "fredkin"), ("iSWAP", "iswap"),
            ("sqrt SWAP", "sqswap"), ("XC", "xc")]
    for i, (name, kind) in enumerate(cols):
        cx = 18 + i * 18
        ys = [top + ROW * k for k in range(3)]
        for y in ys:   # faint guide wires so the spacing is visible
            p.line([(cx - 7, y), (cx + 7, y)], 0.25, "gray")
        if kind == "cnot":
            p.line([(cx, ys[0]), (cx, ys[1] + TGT)], 0.5)
            p.control(cx, ys[0]); p.target(cx, ys[1])
        elif kind == "xc":
            p.line([(cx, ys[0] - TGT), (cx, ys[1])], 0.5)
            p.target(cx, ys[0]); p.control(cx, ys[1])
        elif kind == "cz":
            p.line([(cx, ys[0]), (cx, ys[1])], 0.5)
            p.control(cx, ys[0]); p.control(cx, ys[1])
        elif kind == "toffoli":
            p.line([(cx, ys[0]), (cx, ys[2] + TGT)], 0.5)
            p.control(cx, ys[0]); p.control(cx, ys[1]); p.target(cx, ys[2])
        elif kind == "cxc":
            p.line([(cx, ys[0]), (cx, ys[2])], 0.5)
            p.control(cx, ys[0]); p.target(cx, ys[1]); p.control(cx, ys[2])
        elif kind == "swap":
            p.line([(cx, ys[0]), (cx, ys[1])], 0.5)
            p.cross(cx, ys[0]); p.cross(cx, ys[1])
        elif kind == "fredkin":
            p.line([(cx, ys[0]), (cx, ys[2])], 0.5)
            p.control(cx, ys[0]); p.cross(cx, ys[1]); p.cross(cx, ys[2])
        elif kind in ("iswap", "sqswap"):
            p.rect(cx - 6.5, ys[0] - GATE / 2, 13, ROW + GATE)
            lab = "iSWAP" if kind == "iswap" else [("sqrt", ["SWAP"])]
            p.label(lab, cx, (ys[0] + ys[1]) / 2, 2.3)
        p.text(name if kind != "sqswap" else [("sqrt", ["SWAP"])], cx, top + 2 * ROW + 7, 2.0,
               align="center", color="gray")
    p.text("toffoli", 18 + 2 * 18, top + 2 * ROW + 10.5, 1.7, align="center", color="gray")
    p.text("fredkin", 18 + 5 * 18, top + 2 * ROW + 10.5, 1.7, align="center", color="gray")

    p.text("Building blocks", 12, 148, 3.4, width=0.4)
    p.text("Mix dots and targets on a connector: CX, CCX, CXC, C-C-SWAP ...",
           12, 154, 2.2, color="gray")
    y = 168
    blocks = [("control", lambda x: p.control(x, y)),
              ("open ctrl", lambda x: p.control(x, y, open_=True)),
              ("target", lambda x: p.target(x, y)),
              ("swap", lambda x: p.cross(x, y)),
              ("measure", lambda x: p.meter(x, y)),
              ("in box", lambda x: p.rect(x - 6, y - 5, 12, 10, fill=None, edge="black",
                                          rx=0.8, width=0.45)),
              ("out box", lambda x: p.rect(x - 5, y - 5, 10, 10, fill=None, edge="black",
                                           rx=0.8, width=0.45)),
              ]
    for i, (name, draw) in enumerate(blocks):
        x = 18 + i * 18
        p.line([(x - 7, y), (x + 7, y)], 0.25, "gray") if name in (
            "control", "open ctrl", "target", "swap") else None
        draw(x)
        p.text(name, x, y + 9, 1.9, align="center", color="gray")
    # connectors: 1, 2 and 3 rows long
    for i, n in enumerate((1, 2, 3)):
        x = 142 + i * 10
        p.line([(x, 160), (x, 160 + n * ROW)], 0.5)
        p.text(str(n), x, 156.5, 1.9, align="center", color="gray")
    p.text("connectors (rows)", 152, 152, 1.9, align="center", color="gray")
    # wire pieces
    p.text("wire", 18, 184, 1.9, align="center", color="gray")
    p.line([(12, 190), (60, 190)], 0.45)
    p.text("classical", 18, 196, 1.9, align="center", color="gray")
    p.line([(12, 201.5), (60, 201.5)], 0.35)
    p.line([(12, 203), (60, 203)], 0.35)

    p.text("Drawn with rmdraw + Claude - every line is editable ink", 90, 226, 2.2,
           align="center", color="gray")
    return p.page()


# ---- page 2: states -------------------------------------------------------------------------
STATES = ["0", "1", "+", "-", "i+", "i-"]
BELL = [("00", "F", "+", ["00"], "+", ["11"]), ("01", "Y", "+", ["01"], "+", ["10"]),
        ("10", "F", "-", ["00"], "-", ["11"]), ("11", "Y", "-", ["01"], "-", ["10"])]


def page_states():
    p = Ink()
    p.text("Qubit states", 90, 10, 6.5, align="center", width=0.6)
    p.text("Dirac notation: kets, bras and the four Bell states", 90, 19, 2.6, align="center",
           color="gray")

    p.text("Kets", 12, 28, 3.4, width=0.4)
    for i, s in enumerate(STATES):
        p.text([ket(s)], 22 + i * 27, 37, 6.0, align="center", width=0.55)
    p.text("Bras", 12, 52, 3.4, width=0.4)
    for i, s in enumerate(STATES):
        p.text([bra(s)], 22 + i * 27, 61, 6.0, align="center", width=0.55)

    p.text("Definitions", 12, 76, 3.4, width=0.4)
    h = 3.4
    defs = [
        [ket("+"), " = (", ket("0"), " + ", ket("1"), ") / ", ("sqrt", ["2"])],
        [ket("-"), " = (", ket("0"), " - ", ket("1"), ") / ", ("sqrt", ["2"])],
        [ket("i+"), " = (", ket("0"), " + i", ket("1"), ") / ", ("sqrt", ["2"])],
        [ket("i-"), " = (", ket("0"), " - i", ket("1"), ") / ", ("sqrt", ["2"])],
    ]
    for i, d in enumerate(defs):
        p.text(d, 14 + (i % 2) * 82, 85 + (i // 2) * 10, h, width=0.35)

    p.text("Bell states", 12, 108, 3.4, width=0.4)
    for i, (n, g, sg, a, op, b) in enumerate(BELL):
        y = 119 + i * 13
        p.text([ket(("greek", "b"), ("sub", n))], 14, y, 5.0, width=0.5)
        p.text([" = ", ket(("greek", g), ("sup", sg)), " = (", ket(*a), f" {op} ", ket(*b),
                ") / ", ("sqrt", ["2"])], 31, y + 0.8, 3.6, width=0.35)

    p.text("Input and output boxes", 12, 172, 3.4, width=0.4)
    p.text("for the In / Out columns of the circuit templates", 12, 178, 2.2, color="gray")
    for i, s in enumerate(STATES):
        cx = 18 + i * 17
        p.rect(cx - 6, 186, 12, 10, fill=None, edge="black", rx=0.8, width=0.45)
        p.label([ket(s)], cx, 191, 3.0, width=0.35)
    for i, s in enumerate(("0", "1")):
        cx = 128 + i * 14
        p.rect(cx - 5, 186, 10, 10, fill=None, edge="black", rx=0.8, width=0.45)
        p.label(s, cx, 191, 4.4, width=0.5)
    p.meter(160, 191)
    p.text("Drawn with rmdraw + Claude - every line is editable ink", 90, 226, 2.2,
           align="center", color="gray")
    return p.page()


# ---- page 3: Bloch spheres ------------------------------------------------------------------
SPHERE = "#c9d3e3"
VIEWS = [(-62, 18), (-75, 12), (-45, 24), (-30, 15), (-66, -14), (-58, 34)]   # (azimuth, elevation)


def _view(az, el):
    a, e = math.radians(az), math.radians(el)
    d = (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))
    r = (-math.sin(a), math.cos(a), 0.0)
    u = (-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e))
    dot = lambda p, q: sum(i * j for i, j in zip(p, q))
    return lambda p: (dot(p, r), dot(p, u), dot(p, d))


def bloch(p, cx, cy, R, az, el):
    proj = _view(az, el)
    P = lambda q: (cx + R * proj(q)[0], cy - R * proj(q)[1])
    p.circle(cx, cy, R, fill=SPHERE, width=0.45)

    def ring(f, width, color):
        pts = [f(2 * math.pi * i / 96) for i in range(97)]
        for a, b in zip(pts, pts[1:]):
            front = proj(a)[2] + proj(b)[2] >= 0
            if front:
                p.line([P(a), P(b)], width, color)
            else:
                p.dashed(P(a), P(b), width * 0.8, "gray", on=0.9, off=1.3)
    c, s_ = math.cos, math.sin
    ring(lambda t: (c(t), s_(t), 0), 0.4, "black")    # equator
    ring(lambda t: (c(t), 0, s_(t)), 0.3, "gray")     # x-z meridian
    ring(lambda t: (0, c(t), s_(t)), 0.3, "gray")     # y-z meridian
    for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        neg = tuple(-v for v in axis)
        for end in (axis, neg):
            if proj(end)[2] >= 0:
                p.line([(cx, cy), P(end)], 0.35)
            else:
                p.dashed((cx, cy), P(end), 0.3, "gray", on=0.9, off=1.1)
    labels = [((0, 0, 1), "0", "z"), ((0, 0, -1), "1", None), ((1, 0, 0), "+", "x"),
              ((-1, 0, 0), "-", None), ((0, 1, 0), "i", "y"), ((0, -1, 0), "-i", None)]
    for v, k, axis_name in labels:
        x, y = P(v)
        dx, dy = x - cx, y - cy
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        lx, ly = x + ux * 6.0, y + uy * 4.6
        _, w = run([ket(k)], 0, 0, 2.7)
        p.rect(lx - w / 2 - 0.4, ly - 2.3, w + 0.8, 4.6, fill="white", outline=False, rx=0.8)
        p.label([ket(k)], lx, ly, 2.7, width=0.32)
        if axis_name:
            p.label(axis_name, x + ux * 12.5, y + uy * 9.5, 2.8, color="gray", width=0.3)
    p.circle(cx, cy, 1.1, fill="red")


def page_bloch():
    p = Ink()
    p.text("Bloch spheres", 90, 10, 6.5, align="center", width=0.6)
    p.text("Six viewing angles. Copy one and draw the state vector by hand.", 90, 19, 2.6,
           align="center", color="gray")
    for i, (az, el) in enumerate(VIEWS):
        bloch(p, 50 + (i % 2) * 80, 62 + (i // 2) * 68, 23, az, el)
    return p.page()


# ---- pages 4..9: circuit templates --------------------------------------------------------
X0, XIN, XOUT, X1 = 10.0, 40.0, 142.0, 170.0
STEPS = 6


def page_circuit(n):
    p = Ink()
    p.text(f"Circuit - {n} qubit{'s' if n > 1 else ''}", 90, 10, 5.5, align="center", width=0.55)
    p.text("In: input states.   Measured: classical bits (0 or 1) from the meters.", 90, 19.5,
           2.2, align="center", color="gray")
    p.text("Output state: the quantum state before measurement, written as an equation below.",
           90, 23.5, 2.2, align="center", color="gray")
    top, head = 29.5, 12.0
    bottom = top + head + n * ROW
    p.rect(X0, top, X1 - X0, bottom - top, fill=None, edge="gray", rx=0.0, width=0.4)
    for x in (XIN, XOUT):
        p.line([(x, top), (x, bottom)], 0.4, "gray")
    p.line([(X0, top + head), (X1, top + head)], 0.4, "gray")
    # header: "In / Step" and "Step / Out" with diagonals like a composer's grid
    p.line([(X0, top), (XIN, top + head)], 0.25, "gray")
    p.line([(XOUT, top + head), (X1, top)], 0.25, "gray")
    p.text("Step", XIN - 1.5, top + 1.8, 2.6, align="right", width=0.33)
    p.text("In", X0 + 1.5, top + head - 4.2, 2.6, width=0.33)
    p.text("Step", XOUT + 1.5, top + 1.8, 2.6, width=0.33)
    p.text("Measured", X1 - 1.2, top + head - 3.6, 2.2, align="right", width=0.3)
    step_w = (XOUT - XIN) / STEPS
    for s in range(STEPS):
        p.text(str(s + 1), XIN + step_w * (s + 0.5), top + 4.5, 3.0, align="center",
               color="gray")
    for q in range(n):
        y = top + head + ROW * (q + 0.5)
        p.text(f"q[{q}]", X0 + 2, y - 1.4, 2.8, width=0.3)
        p.rect(X0 + 15, y - 5, 12, 10, fill=None, edge="black", rx=0.8, width=0.45)  # In box
        p.line([(X0 + 27, y), (XOUT + 4, y)], 0.45)                                   # wire
        p.meter(XOUT + 10, y, w=10, h=8)
        p.rect(X1 - 12.5, y - 5, 10, 10, fill=None, edge="black", rx=0.8, width=0.45)  # Out box
    # output state: the quantum state before measurement, written as an equation (hand-lettered)
    y = bottom + 9
    HAND[0] = True
    p.text(["Output state (before measurement)"], X0, y, 3.4, width=0.38)
    p.text([ket(("greek", "y"), ("sub", "out")), " ="], X0 + 2, y + 10, 4.6, width=0.45)
    HAND[0] = False
    for k in range(3):
        ly = y + 15 + k * 12
        p.line([(X0 + 22 if k == 0 else X0 + 2, ly), (X1, ly)], 0.25, "gray")
    return p.page()


def build() -> Document:
    import quantum_matrices as qm
    pages = [page_gates()] + qm.gate_pages() + [page_states()] + qm.state_pages() + [page_bloch()] + [page_circuit(n) for n in range(1, 7)]
    doc = from_dict({"name": NAME, "pages": [items for items, _ in pages]})
    for page, (_, strokes) in zip(doc.pages, pages):
        page.strokes.extend(strokes)
    return doc


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    from build_gallery import OUT, publish
    publish(build(), OUT / "symbols" / "quantum-gates", "quantum-gates")
