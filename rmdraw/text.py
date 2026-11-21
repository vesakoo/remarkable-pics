"""Single-stroke (Hershey futural) text as pen strokes."""

import warnings

from HersheyFonts import HersheyFonts

from rmdraw.model import Stroke

_font = HersheyFonts()
_font.load_default_font("futural")
_MAP = {"–": "-", "—": "-", "’": "'"}
_CAP_TOP, _BASE = -12.0, 9.0  # futural cap line / baseline (y down)
_CAP = _BASE - _CAP_TOP
_EPS = 1e-6
_cache: dict[str, tuple[float, list[list[tuple[float, float]]]] | None] = {}


def _glyph(ch):
    """(advance, polylines) in font units, or None if the font lacks ch."""
    if ch not in _cache:
        gs = list(_font.glyphs_for_text(ch)) if len(ch) == 1 else []
        if not gs:
            _cache[ch] = None
        else:
            polys: list[list[tuple[float, float]]] = []
            for (a, b) in _font.lines_for_text(ch):
                a, b = (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
                if polys and abs(polys[-1][-1][0] - a[0]) < _EPS and abs(polys[-1][-1][1] - a[1]) < _EPS:
                    polys[-1].append(b)
                else:
                    polys.append([a, b])
            _cache[ch] = (float(gs[0].char_width), polys)
    return _cache[ch]


def _layout(line):
    """Polylines (font units, y down from cap top) and advance width."""
    x, out = 0.0, []
    for ch in line:
        adv, polys = _glyph(ch)
        for p in polys:
            out.append([(x + px, py - _CAP_TOP) for px, py in p])
        x += adv
    return out, x


def _normalize(s):
    warned: set[str] = set()
    chars = []
    for ch in s:
        ch = _MAP.get(ch, ch)
        if _glyph(ch) is None:
            if ch not in warned:
                warned.add(ch)
                warnings.warn(f"character {ch!r} missing from stroke font; using space", stacklevel=3)
            ch = " "
        chars.append(ch)
    return "".join(chars)


def _width(line):
    return sum(_glyph(c)[0] for c in line)


def _split(s, limit_units):
    words = s.split()
    if len(words) < 2 or _width(s) <= limit_units:
        return [s]
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        w = max(_width(a), _width(b))
        if best is None or w < best[0]:
            best = (w, [a, b])
    return best[1]


def text_strokes(s, x_mm, y_mm, height_mm, max_width_mm=None, align="center", color="black"):
    s = _normalize(s).strip()
    if not s:
        return []
    k = height_mm / _CAP
    lines = [s]
    if max_width_mm is not None:
        lines = _split(s, max_width_mm / k)
        widest = max(_width(l) for l in lines)
        if widest * k > max_width_mm:
            k = max_width_mm / widest
    h = _CAP * k
    width_pen = max(0.2, height_mm * 0.1)
    out = []
    for i, line in enumerate(lines):
        polys, w = _layout(line)
        left = x_mm - w * k / 2 if align == "center" else x_mm
        top = y_mm + i * 1.5 * height_mm
        for p in polys:
            out.append(Stroke([(left + px * k, top + py * k) for px, py in p],
                              pen="fineliner", color=color, width_mm=width_pen))
    return out
