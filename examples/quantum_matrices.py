"""Matrix pages for the quantum symbols notebook: gate matrices and state vectors.

Lettered in a casual hand style (rounded, slanted, slightly uneven) with roomy matrix cells, so
the numbers never crowd each other. Used by quantum_gates.build().
"""
import math

import quantum_gates as qg
from quantum_gates import Ink, bra, ket, run, shift
from rmdraw.model import Stroke

EH = 4.4          # entry height, mm
ROWP = 8.6        # matrix row pitch, mm
GAP = 7.5         # minimum free space between matrix columns, mm
GREEK = {"th": "q", "ph": "f", "la": "l", "pi": "p", "al": "a", "be": "b", "y": "y"}


def g(name):
    return ("greek", GREEK[name])


def pen(h):
    return max(0.3, h * 0.11)


class Box:
    """Strokes laid out around a vertical centre line y=0, starting at x=0."""

    def __init__(self, strokes, w, half):
        self.strokes, self.w, self.half = strokes, w, half

    def at(self, x, cy):
        return shift(self.strokes, x, cy)


def atom(segs, h=EH, color="black"):
    st, w = run(segs, 0, -h / 2, h, color, pen(h))
    return Box(st, w, h * 0.75)


def frac(num, den, h=EH):
    n, d = atom(num, h * 0.85), atom(den, h * 0.85)
    w = max(n.w, d.w) + 1.6
    bar = Stroke([(0.2, 0.0), (w - 0.2, 0.0)], width_mm=pen(h) * 0.9)
    st = n.at((w - n.w) / 2, -h * 0.62) + d.at((w - d.w) / 2, h * 0.72) + [bar]
    return Box(st, w, h * 1.15)


def hcat(boxes, gap=1.6):
    st, x, half = [], 0.0, 0.0
    for b in boxes:
        st += b.at(x, 0)
        x += b.w + gap
        half = max(half, b.half)
    return Box(st, x - gap, half)


def as_box(e, h=EH):
    if isinstance(e, Box):
        return e
    return atom(e if isinstance(e, list) else [e], h)


def paren(x, top, bot, left, width):
    H = bot - top
    pts = []
    for i in range(25):
        t = i / 24
        bulge = 1.6 * math.sin(math.pi * t)
        pts.append((x - bulge if left else x + bulge, top + H * t))
    return Stroke(pts, width_mm=width)


def matrix(rows, h=EH, rowp=ROWP, gap=GAP):
    cells = [[as_box(e, h) for e in r] for r in rows]
    ncol = max(len(r) for r in cells)
    colw = [max(r[j].w for r in cells if j < len(r)) for j in range(ncol)]
    inner = sum(colw) + gap * (ncol - 1)
    pad = 3.2
    H = rowp * len(rows)
    st = []
    x = pad
    for j in range(ncol):
        for i, r in enumerate(cells):
            b = r[j]
            cy = -H / 2 + rowp * (i + 0.5)
            st += b.at(x + (colw[j] - b.w) / 2, cy)
        x += colw[j] + gap
    W = inner + 2 * pad
    st.append(paren(1.6, -H / 2 - 0.6, H / 2 + 0.6, True, pen(h) * 1.1))
    st.append(paren(W - 1.6, -H / 2 - 0.6, H / 2 + 0.6, False, pen(h) * 1.1))
    return Box(st, W, H / 2 + 1)


def equation(p, x, cy, tile, parts, h=EH):
    """Optional gate tile, then '=' and the given boxes, centred on cy. Returns the end x."""
    if tile:
        label, extra = tile if isinstance(tile, tuple) else (tile, None)
        n = len(qg._plain(label))
        size = 4.4 if n <= 1 else 3.6 if n == 2 else 3.0
        tw = max(10.0, run(label, 0, 0, size)[1] + 3.5)
        p.gate(x + tw / 2, cy, label, w=tw, h=10.0, size=size)
        x += tw + 1.2
        if extra:
            b = atom(extra, h)
            p.strokes += b.at(x, cy)
            x += b.w + 0.8
        parts = ["="] + parts
    eq = hcat([as_box(q, h) for q in parts], 2.2)
    p.strokes += eq.at(x + 1.0, cy)
    return x + 1.0 + eq.w


def heading(p, title, sub=None):
    qg.HAND[0] = True
    p.text(title, 90, 10, 7.0, align="center", width=0.7)
    if sub:
        p.text(sub, 90, 21.5, 3.0, align="center", color="gray", width=0.32)


def note(p, s, x, y, h=2.9):
    p.text(s, x, y, h, color="gray", width=0.3)


SQ2 = frac(["1"], [("sqrt", ["2"])])
HALF = frac(["1"], ["2"])


def e_i(*exp, neg=False):
    return ["e", ("sup", ["-i" if neg else "i"] + list(exp))]


# ---- gate pages --------------------------------------------------------------------------------
def page_single():
    p = Ink()
    heading(p, "Gate matrices", ["single-qubit gates, basis ", ket("0"), ", ", ket("1")])
    eqs = [
        ("I", [matrix([["1", "0"], ["0", "1"]])]),
        ("X", [matrix([["0", "1"], ["1", "0"]])]),
        ("Y", [matrix([["0", "-i"], ["i", "0"]])]),
        ("Z", [matrix([["1", "0"], ["0", "-1"]])]),
        ("H", [SQ2, matrix([["1", "1"], ["1", "-1"]])]),
        ("S", [matrix([["1", "0"], ["0", "i"]])]),
        (["S", ("dag",)], [matrix([["1", "0"], ["0", "-i"]])]),
        ("T", [matrix([["1", "0"], ["0", e_i(g("pi"), "/4")]])]),
        (["T", ("dag",)], [matrix([["1", "0"], ["0", e_i(g("pi"), "/4", neg=True)]])]),
        ("SX", [HALF, matrix([["1+i", "1-i"], ["1-i", "1+i"]])]),
        (["SX", ("dag",)], [HALF, matrix([["1-i", "1+i"], ["1+i", "1-i"]])]),
    ]
    for i, (tile, parts) in enumerate(eqs):
        col, row = i % 2, i // 2
        equation(p, 12 + col * 84, 40 + row * 32, tile, parts)
    note(p, ["S = ", ("sqrt", ["Z"]), ",   T = ", ("sqrt", ["S"]), ",   SX = ", ("sqrt", ["X"]), ",   HXH = Z"], 14, 222)
    return p.page()


def page_param():
    p = Ink()
    heading(p, "Rotation and phase gates", "angles in radians")
    th2 = [g("th"), "/2"]
    cos, sin = ["cos ", *th2], ["sin ", *th2]
    eqs = [
        (("P", ["(", g("ph"), ")"]), [matrix([["1", "0"], ["0", e_i(g("ph"))]])]),
        (("RX", ["(", g("th"), ")"]), [matrix([[cos, ["-i ", *sin]], [["-i ", *sin], cos]])]),
        (("RY", ["(", g("th"), ")"]), [matrix([[cos, ["-", *sin]], [sin, cos]])]),
        (("RZ", ["(", g("th"), ")"]), [matrix([[e_i(g("th"), "/2", neg=True), "0"],
                                                ["0", e_i(g("th"), "/2")]])]),
        (("U", ["(", g("th"), ", ", g("ph"), ", ", g("la"), ")"]),
         [matrix([[cos, ["-", *e_i(g("la")), " ", *sin]],
                  [[*e_i(g("ph")), " ", *sin], [*e_i("(", g("ph"), "+", g("la"), ")"), " ", *cos]]])]),
    ]
    for i, (tile, parts) in enumerate(eqs):
        equation(p, 14, 42 + i * 36, tile, parts)
    note(p, ["RX(", g("pi"), ") = -iX,    U(", g("pi"), "/2, 0, ", g("pi"), ") = H"], 14, 214)
    note(p, ["RZ(", g("ph"), ") = P(", g("ph"), ") up to a global phase"], 14, 220)
    return p.page()


def page_two():
    p = Ink()
    heading(p, "Two-qubit gates", ["basis order ", ket("00"), ", ", ket("01"), ", ", ket("10"), ", ", ket("11"), "   (q0 is the left bit)"])
    one, zero = "1", "0"
    I4 = lambda r: matrix(r, rowp=8.4, gap=7.2)
    eqs = [
        ("CX", [I4([[one, zero, zero, zero], [zero, one, zero, zero],
                    [zero, zero, zero, one], [zero, zero, one, zero]])]),
        ("CZ", [I4([[one, zero, zero, zero], [zero, one, zero, zero],
                    [zero, zero, one, zero], [zero, zero, zero, "-1"]])]),
        ("SWAP", [I4([[one, zero, zero, zero], [zero, zero, one, zero],
                      [zero, one, zero, zero], [zero, zero, zero, one]])]),
        ("iSWAP", [I4([[one, zero, zero, zero], [zero, zero, "i", zero],
                       [zero, "i", zero, zero], [zero, zero, zero, one]])]),
    ]
    for i, (tile, parts) in enumerate(eqs):
        col, row = i % 2, i // 2
        equation(p, 10 + col * 86, 56 + row * 50, tile, parts)
    a = frac(["1+i"], ["2"])
    b = frac(["1-i"], ["2"])
    equation(p, 14, 174, [("sqrt", ["SWAP"])],
             [matrix([[one, zero, zero, zero], [zero, a, b, zero], [zero, b, a, zero],
                      [zero, zero, zero, one]], rowp=13.0, gap=8.0)])
    note(p, "CX: control q0, target q1.", 14, 216)
    return p.page()


def page_three():
    p = Ink()
    heading(p, "Three-qubit gates", ["basis ", ket("000"), ", ", ket("001"), " ... ", ket("111")])
    def big(swap_rows):
        z = atom("0", 3.0, "gray")
        rows = [[z] * 8 for _ in range(8)]
        for i in range(8):
            rows[i][swap_rows.get(i, i)] = "1"
        return matrix(rows, h=4.0, rowp=7.2, gap=4.4)
    lab = lambda s: atom(s, 3.4, "gray")
    for j in range(8):  # basis labels above the columns would crowd; list them in a note instead
        pass
    equation(p, 20, 70, "CCX", [big({6: 7, 7: 6})])
    note(p, "Toffoli: flips the last qubit when both controls are 1", 20, 110)
    equation(p, 20, 160, "CSWAP", [big({5: 6, 6: 5})])
    note(p, "Fredkin: swaps the last two qubits when the control is 1", 20, 200)
    return p.page()


def gate_pages():
    pages = [page_single(), page_param(), page_two(), page_three()]
    qg.HAND[0] = False
    return pages


# ---- state pages -------------------------------------------------------------------------------
def col(*xs, rowp=ROWP):
    return matrix([[x] for x in xs], rowp=rowp)


def ket_box(s, h=EH + 0.6):
    return atom([ket(*s)] if isinstance(s, list) else [ket(s)], h)


def page_states1():
    p = Ink()
    heading(p, "State vectors", ["one qubit, column vectors in the basis ", ket("0"), ", ", ket("1")])
    eqs = [
        ("0", [col("1", "0")]), ("1", [col("0", "1")]),
        ("+", [SQ2, col("1", "1")]), ("-", [SQ2, col("1", "-1")]),
        ("i+", [SQ2, col("1", "i")]), ("i-", [SQ2, col("1", "-i")]),
    ]
    for i, (k, parts) in enumerate(eqs):
        c, r = i % 2, i // 2
        x, cy = 16 + c * 84, 44 + r * 30
        b = hcat([ket_box(k), atom("="), *parts], 2.4)
        p.strokes += b.at(x, cy)
    y = 146
    b = hcat([atom([ket(g("y"))], EH + 0.6), atom("="), atom([g("al"), " ", ket("0"), " + ", g("be"), " ", ket("1")]),
              atom("="), col([g("al")], [g("be")])], 2.4)
    p.strokes += b.at(16, y)
    note(p, ["where  |", g("al"), "|", ("sup", "2"), " + |", g("be"), "|", ("sup", "2"), " = 1"], 22, y + 12, 3.0)
    b = hcat([atom([bra(g("y"))], EH + 0.6), atom("="),
              matrix([[[g("al"), ("sup", "*")], [g("be"), ("sup", "*")]]]), atom(" (row vector)", 3.2)], 2.4)
    p.strokes += b.at(16, 176)
    th2 = [g("th"), "/2"]
    b = hcat([atom([ket(g("y"))], EH + 0.6), atom("="),
              atom(["cos ", *th2, " ", ket("0"), " + ", *e_i(g("ph")), " sin ", *th2, " ", ket("1")])], 2.4)
    p.strokes += b.at(16, 202)
    note(p, ["Bloch sphere: ", g("th"), " measured from the z axis, ", g("ph"), " around it"], 16, 214, 2.8)
    return p.page()


def page_states2():
    p = Ink()
    heading(p, "Two-qubit states", ["basis ", ket("00"), ", ", ket("01"), ", ", ket("10"), ", ", ket("11")])
    basis = ["00", "01", "10", "11"]
    for i, k in enumerate(basis):
        v = ["0"] * 4
        v[i] = "1"
        b = hcat([ket_box(k), atom("="), col(*v, rowp=7.6)], 2.4)
        p.strokes += b.at(20 + (i % 2) * 86, 50 + (i // 2) * 40)
    note(p, [ket("ab"), " = ", ket("a"), " (x) ", ket("b"), "   (tensor product)"], 20, 114)
    bell = [("00", "F", "+", ["1", "0", "0", "1"]), ("01", "Y", "+", ["0", "1", "1", "0"]),
            ("10", "F", "-", ["1", "0", "0", "-1"]), ("11", "Y", "-", ["0", "1", "-1", "0"])]
    for i, (n, gk, sg, v) in enumerate(bell):
        c, r = i % 2, i // 2
        b = hcat([atom([ket(("greek", "b"), ("sub", n))], EH + 0.6), atom("="),
                  atom([ket(("greek", gk), ("sup", sg))], EH), atom("="), SQ2,
                  col(*v, rowp=7.6)], 2.2)
        p.strokes += b.at(12 + c * 86, 148 + r * 42)
    note(p, ["Bell circuit: H on q0, then CX turns ", ket("ab"), " into ", ket(("greek", "b"), ("sub", "ab"))], 12, 220)
    return p.page()


def state_pages():
    qg.HAND[0] = True
    pages = [page_states1(), page_states2()]
    qg.HAND[0] = False
    return pages
