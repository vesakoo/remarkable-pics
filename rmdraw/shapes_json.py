"""Shapes JSON: compose a drawing from simple shapes in mm and turn it into a Document.

Format (coordinates in mm on the page, origin top-left, y down; page ~179.7 x 239.6 mm):

    {"name": "Smiley", "pages": [[item, item, ...], ...]}

Item types (geometry fields):
    polyline {points: [[x, y], ...], closed?}
    circle   {cx, cy, r}
    ellipse  {cx, cy, rx, ry, rotation_deg?}
    rect     {x, y, w, h, rx?}
    arc      {cx, cy, r, start_deg, end_deg}   clockwise from 3 o'clock (y points down)
    bezier   {points: [p0, c1, c2, p3, (c, c, p)...], closed?}   cubic chain
    text     {text, x, y, height, align?: "center"|"left", max_width?}
    svg      {path, box: [x, y, w, h]}         path is relative to the JSON file
Common optional fields: pen (default fineliner), color (default black), width_mm,
fill {color: palette name or "#rrggbb", method?: shader|marker|hatch, spacing_mm?}.
For svg items, fill is {method?: shader|marker|hatch|none, spacing_mm?}.

Paint order is list order. A filled item hides everything listed before it where they
overlap (fills and lines are clipped), so draw background first and details last.
A white fill draws nothing but still hides what is below: that's how to make a gap.
"""
from __future__ import annotations

import json
import math
import re
import warnings
from pathlib import Path

import shapely
from shapely.geometry import LineString, Point, Polygon

from .fill import DEFAULT_SPACING, shapes_to_strokes
from .geometry import COLOR_NAMES, PAGE_H_MM, PAGE_W_MM, PEN_NAMES
from .model import Document, Page, Stroke
from .palette import FILL_ALPHA, PALETTE_RGB
from .svgimport import FilledShape, svg_to_shapes
from .text import text_strokes

TOLERANCE_MM = 0.15
DEFAULT_WIDTH_MM = 0.4
ITEM_BUDGET = 150
PAGE_WARN = 3000
FILL_RGB = {**PALETTE_RGB, "white": (255, 255, 255)}
FILL_METHODS = tuple(DEFAULT_SPACING)
_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_COMMON = {"type", "pen", "color", "width_mm", "fill"}
_FIELDS = {
    "polyline": ({"points"}, {"closed"}),
    "circle": ({"cx", "cy", "r"}, set()),
    "ellipse": ({"cx", "cy", "rx", "ry"}, {"rotation_deg"}),
    "rect": ({"x", "y", "w", "h"}, {"rx"}),
    "arc": ({"cx", "cy", "r", "start_deg", "end_deg"}, set()),
    "bezier": ({"points"}, {"closed"}),
    "text": ({"text", "x", "y", "height"}, {"align", "max_width"}),
    "svg": ({"path", "box"}, set()),
}
Pt = tuple[float, float]


# ---------- flattening ----------

def _segments(r: float, sweep_rad: float) -> int:
    if r <= TOLERANCE_MM:
        return max(1, math.ceil(abs(sweep_rad) / (math.pi / 2)))
    step = 2 * math.acos(1 - TOLERANCE_MM / r)
    return max(1, math.ceil(abs(sweep_rad) / step))


def flatten_arc(cx: float, cy: float, rx: float, ry: float, start_deg: float, end_deg: float,
                rotation_deg: float = 0.0) -> list[Pt]:
    """Points on an elliptical arc, clockwise on screen (y down) from start to end."""
    a0, a1 = math.radians(start_deg), math.radians(end_deg)
    n = _segments(max(rx, ry), a1 - a0)
    rot = math.radians(rotation_deg)
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def flatten_bezier(points) -> list[Pt]:
    """Flatten a cubic Bezier chain [p0, c1, c2, p3, c, c, p, ...] within TOLERANCE_MM."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) < 4 or (len(pts) - 1) % 3:
        raise ValueError("bezier needs 1 + 3k points (p0, c1, c2, p3, then c, c, p ...)")
    out = [pts[0]]
    for k in range(0, len(pts) - 1, 3):
        p0, p1, p2, p3 = pts[k:k + 4]
        # Wang's formula for a cubic: n = sqrt(3/4 * M / tol)
        m = max(math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1]),
                math.hypot(p1[0] - 2 * p2[0] + p3[0], p1[1] - 2 * p2[1] + p3[1]))
        n = max(1, math.ceil(math.sqrt(0.75 * m / TOLERANCE_MM)))
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            out.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


# ---------- validation helpers ----------

class _Item:
    def __init__(self, where: str, d: dict):
        self.where, self.d = where, d

    def fail(self, msg: str):
        raise ValueError(f"{self.where}: {msg}")

    def num(self, key: str, positive=False, nonneg=False, default=None) -> float:
        if key not in self.d:
            if default is not None:
                return default
            self.fail(f"missing field '{key}'")
        v = self.d[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            self.fail(f"field '{key}' must be a number, got {v!r}")
        if positive and v <= 0:
            self.fail(f"field '{key}' must be > 0, got {v!r}")
        if nonneg and v < 0:
            self.fail(f"field '{key}' must be >= 0, got {v!r}")
        return float(v)

    def points(self, key: str, min_n: int) -> list[Pt]:
        v = self.d.get(key)
        if not isinstance(v, list) or len(v) < min_n:
            self.fail(f"field '{key}' must be a list of at least {min_n} [x, y] points")
        out = []
        for j, p in enumerate(v):
            if (not isinstance(p, (list, tuple)) or len(p) != 2
                    or not all(isinstance(c, (int, float)) and not isinstance(c, bool)
                               for c in p)):
                self.fail(f"field '{key}[{j}]' must be [x, y] numbers, got {p!r}")
            out.append((float(p[0]), float(p[1])))
        return out


def _hex_rgb(s: str) -> tuple[int, int, int]:
    return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)


def _fill_rgb(it: _Item, v, key: str) -> tuple[int, int, int]:
    if isinstance(v, str) and v in FILL_RGB:
        return FILL_RGB[v]
    if isinstance(v, str) and _HEX.fullmatch(v):
        return _hex_rgb(v)
    it.fail(f"field '{key}' must be a palette name ({', '.join(FILL_RGB)}) or '#rrggbb', "
            f"got {v!r}")


def _check_on_page(it: _Item, pts):
    for x, y in pts:
        if not (0 <= x <= PAGE_W_MM and 0 <= y <= PAGE_H_MM):
            it.fail(f"point ({x:.2f}, {y:.2f}) mm is off the page "
                    f"(0..{PAGE_W_MM:.1f} x 0..{PAGE_H_MM:.1f} mm)")


# ---------- items ----------

def _style(it: _Item) -> dict:
    d = it.d
    pen = d.get("pen", "fineliner")
    if pen not in PEN_NAMES:
        it.fail(f"unknown pen {pen!r} in field 'pen' (one of {', '.join(PEN_NAMES)})")
    width = it.num("width_mm", positive=True, default=DEFAULT_WIDTH_MM)
    color = d.get("color", "black")
    if pen == "shader":
        rgb = _fill_rgb(it, color, "color")
        return {"pen": pen, "color": "black", "width_mm": width, "rgba": (*rgb, FILL_ALPHA)}
    if color not in COLOR_NAMES:
        it.fail(f"unknown color {color!r} in field 'color' (one of {', '.join(COLOR_NAMES)})")
    return {"pen": pen, "color": color, "width_mm": width, "rgba": None}


def _fill_spec(it: _Item, allow_none=False):
    f = it.d.get("fill")
    if f is None:
        return None
    if not isinstance(f, dict):
        it.fail("field 'fill' must be an object like {\"color\": \"yellow\"}")
    extra = set(f) - {"color", "method", "spacing_mm"}
    if extra:
        it.fail(f"unknown field 'fill.{sorted(extra)[0]}'")
    methods = FILL_METHODS + (("none",) if allow_none else ())
    method = f.get("method", "shader")
    if method not in methods:
        it.fail(f"unknown fill method {method!r} in field 'fill.method' "
                f"(one of {', '.join(methods)})")
    spacing = None
    if "spacing_mm" in f:
        spacing = f["spacing_mm"]
        if isinstance(spacing, bool) or not isinstance(spacing, (int, float)) or spacing <= 0:
            it.fail(f"field 'fill.spacing_mm' must be a number > 0, got {spacing!r}")
    if allow_none:
        if "color" in f:
            it.fail("field 'fill.color' is not used for svg items (the SVG's colours are)")
        return {"method": method, "spacing": spacing}
    if "color" not in f:
        it.fail("missing field 'fill.color'")
    return {"rgb": _fill_rgb(it, f["color"], "fill.color"), "method": method,
            "spacing": spacing}


def _geometry(it: _Item, t: str) -> tuple[list[Pt], bool]:
    """Flattened outline and whether it is closed."""
    if t == "polyline":
        pts = it.points("points", 2)
        closed = bool(it.d.get("closed", False))
        if closed and pts[0] != pts[-1]:
            pts.append(pts[0])
        return pts, closed
    if t == "bezier":
        pts = it.points("points", 4)
        if (len(pts) - 1) % 3:
            it.fail("field 'points' must hold 1 + 3k points (p0, c1, c2, p3, then c, c, p ...)")
        pts = flatten_bezier(pts)
        closed = bool(it.d.get("closed", False))
        if closed and pts[0] != pts[-1]:
            pts.append(pts[0])
        return pts, closed
    if t == "circle":
        r = it.num("r", positive=True)
        return flatten_arc(it.num("cx"), it.num("cy"), r, r, 0, 360), True
    if t == "ellipse":
        return flatten_arc(it.num("cx"), it.num("cy"), it.num("rx", positive=True),
                           it.num("ry", positive=True), 0, 360,
                           it.num("rotation_deg", default=0.0)), True
    if t == "arc":
        a0, a1 = it.num("start_deg"), it.num("end_deg")
        if not a0 < a1 <= a0 + 360:
            it.fail("field 'end_deg' must be greater than 'start_deg' and at most 360 more "
                    "(arcs go clockwise from start to end)")
        r = it.num("r", positive=True)
        return flatten_arc(it.num("cx"), it.num("cy"), r, r, a0, a1), False
    if t == "rect":
        x, y = it.num("x"), it.num("y")
        w, h = it.num("w", positive=True), it.num("h", positive=True)
        rx = it.num("rx", nonneg=True, default=0.0)
        if rx > min(w, h) / 2:
            it.fail(f"field 'rx' must be at most half the shorter side ({min(w, h) / 2:g})")
        if rx == 0:
            return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], True
        pts: list[Pt] = []
        for cx, cy, a in ((x + w - rx, y + rx, -90), (x + w - rx, y + h - rx, 0),
                          (x + rx, y + h - rx, 90), (x + rx, y + rx, 180)):
            pts += flatten_arc(cx, cy, rx, rx, a, a + 90)
        return pts + [pts[0]], True
    raise AssertionError(t)


def _text(it: _Item, style: dict) -> list[Stroke]:
    s = it.d.get("text")
    if not isinstance(s, str) or not s.strip():
        it.fail("field 'text' must be a non-empty string")
    align = it.d.get("align", "center")
    if align not in ("center", "left"):
        it.fail(f"field 'align' must be 'center' or 'left', got {align!r}")
    mw = it.num("max_width", positive=True) if "max_width" in it.d else None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        strokes = text_strokes(s, it.num("x"), it.num("y"), it.num("height", positive=True),
                               max_width_mm=mw, align=align, color=style["color"])
    for st in strokes:
        st.pen = style["pen"]
        st.rgba = style["rgba"]
        if "width_mm" in it.d:
            st.width_mm = style["width_mm"]
    return strokes


def svg_strokes(path: Path, box: tuple[float, float, float, float], method: str = "shader",
                spacing_mm: float | None = None) -> list[Stroke]:
    """SVG file -> strokes fitted into box (mm). method 'none' draws outlines only."""
    shapes = svg_to_shapes(Path(path), box, tolerance_mm=TOLERANCE_MM)
    if method == "none":
        shapes = [FilledShape(s.outline, None, s.stroke_rgb or s.fill_rgb, s.fill_rule,
                              s.stroke_width_mm) for s in shapes
                  if (s.stroke_rgb or s.fill_rgb) is not None]
        method = "shader"
    budget = max(ITEM_BUDGET, 4 * len(shapes))
    return shapes_to_strokes(shapes, method=method, spacing_mm=spacing_mm, budget=budget)


def _svg(it: _Item, base: Path) -> list[Stroke]:
    p = it.d.get("path")
    if not isinstance(p, str) or not p:
        it.fail("field 'path' must be a file path string")
    path = (base / p) if not Path(p).is_absolute() else Path(p)
    if not path.is_file():
        it.fail(f"field 'path': no such file {str(path)!r}")
    box = it.d.get("box")
    if (not isinstance(box, list) or len(box) != 4
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in box)
            or box[2] <= 0 or box[3] <= 0):
        it.fail("field 'box' must be [x, y, w, h] with w, h > 0")
    x, y, w, h = (float(v) for v in box)
    _check_on_page(it, [(x, y), (x + w, y + h)])
    spec = _fill_spec(it, allow_none=True) or {"method": "shader", "spacing": None}
    try:
        return svg_strokes(path, (x, y, w, h), spec["method"], spec["spacing"])
    except ValueError as e:
        it.fail(str(e))


def _polygon(ring: list[Pt]):
    if len(ring) < 4:
        return None
    g = shapely.make_valid(Polygon(ring))
    parts = [g] if g.geom_type == "Polygon" else [
        p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    g = shapely.union_all(parts) if parts else None
    return g if g is not None and not g.is_empty and g.area > 0 else None


def _rings(area) -> list[list[Pt]]:
    out = []
    for poly in getattr(area, "geoms", [area]):
        if poly.geom_type != "Polygon" or poly.is_empty:
            continue
        out.append([tuple(p) for p in poly.exterior.coords])
        out += [[tuple(p) for p in r.coords] for r in poly.interiors]
    return out


def _clip(stroke: Stroke, cover) -> list[Stroke]:
    """The parts of a stroke not hidden under `cover`."""
    if cover is None or cover.is_empty:
        return [stroke]
    pts = stroke.points
    if len(pts) < 2 or len(set(pts)) < 2:
        return [] if cover.covers(Point(pts[0])) else [stroke]
    line = LineString(pts)
    if not line.intersects(cover):
        return [stroke]
    rest = line.difference(cover)
    out = []
    for part in getattr(rest, "geoms", [rest]):
        if part.geom_type == "LineString" and not part.is_empty and part.length > 0:
            out.append(Stroke([tuple(p) for p in part.coords], stroke.pen, stroke.color,
                              stroke.width_mm, stroke.rgba))
    return out


def _page(items, p: int, base: Path) -> Page:
    if not isinstance(items, list):
        raise ValueError(f"pages[{p}]: a page must be a list of items")
    built = []  # (strokes, (area, fill) or None) per item
    for i, d in enumerate(items):
        where = f"pages[{p}][{i}]"
        if not isinstance(d, dict):
            raise ValueError(f"{where}: an item must be an object with a 'type'")
        t = d.get("type")
        if t not in _FIELDS:
            raise ValueError(f"{where}: unknown type {t!r} (one of {', '.join(_FIELDS)})")
        it = _Item(f"{where} ({t})", d)
        required, optional = _FIELDS[t]
        for k in d:
            if k not in _COMMON | required | optional:
                it.fail(f"unknown field '{k}' (allowed: "
                        f"{', '.join(sorted(_COMMON | required | optional))})")
        if t == "svg":
            strokes = _svg(it, base)
            built.append((strokes, None))
            continue
        style = _style(it)
        if t == "text":
            if "fill" in d:
                it.fail("field 'fill' is not allowed on text")
            strokes = _text(it, style)
            for st in strokes:
                _check_on_page(it, st.points)
            built.append((strokes, None))
            continue
        pts, closed = _geometry(it, t)
        _check_on_page(it, pts)
        fill = _fill_spec(it)
        area = None
        if fill is not None:
            if not closed:
                it.fail(f"field 'fill' needs a closed shape ({t} is open; "
                        "use closed: true or a circle/ellipse/rect)")
            area = _polygon(pts)
            if area is None:
                it.fail("field 'fill': the shape encloses no area")
        outline = Stroke(pts, style["pen"], style["color"], style["width_mm"], style["rgba"])
        built.append(([outline], (area, fill) if fill else None))

    # paint order: each filled item hides what was drawn before it
    strokes: list[Stroke] = []
    cover = None
    for i in range(len(built) - 1, -1, -1):
        strokes_i, filled = built[i]
        mine: list[Stroke] = []
        if filled is not None:
            area, fill = filled
            visible = area.difference(cover) if cover is not None else area
            if fill["rgb"] != FILL_RGB["white"] and not visible.is_empty:
                shape = FilledShape(_rings(visible), fill["rgb"], None, "evenodd")
                try:
                    mine += shapes_to_strokes([shape], method=fill["method"],
                                              spacing_mm=fill["spacing"], outlines=False,
                                              budget=ITEM_BUDGET)
                except ValueError as e:
                    raise ValueError(f"pages[{p}][{i}]: {e}") from None
        for st in strokes_i:
            mine += _clip(st, cover)
        strokes[:0] = mine
        if filled is not None:
            cover = filled[0] if cover is None else cover.union(filled[0])
    if len(strokes) > PAGE_WARN:
        warnings.warn(f"pages[{p}] has {len(strokes)} strokes; above ~{PAGE_WARN} the "
                      "tablet gets sluggish", UserWarning, stacklevel=3)
    return Page(strokes)


def from_dict(data, base: Path = Path(".")) -> Document:
    if not isinstance(data, dict):
        raise ValueError("shapes JSON must be an object with 'name' and 'pages'")
    extra = set(data) - {"name", "pages"}
    if extra:
        raise ValueError(f"unknown top-level field '{sorted(extra)[0]}' (allowed: name, pages)")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("field 'name' must be a non-empty string (the notebook title)")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("field 'pages' must be a non-empty list of pages (lists of items)")
    return Document(name, [_page(items, p, base) for p, items in enumerate(pages)])


def load(path) -> Document:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON at line {e.lineno} column {e.colno}: {e.msg}") \
            from None
    return from_dict(data, path.parent)
