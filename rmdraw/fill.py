"""Turn filled vector shapes into pen strokes: banded fills plus outlines on top."""
from __future__ import annotations

import math

import shapely
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.geometry.base import BaseGeometry

from .model import Stroke
from .palette import to_pen_color
from .svgimport import FilledShape

OUTLINE_WIDTH_MM = 0.35
HATCH_WIDTH_MM = 0.3
HATCH_ANGLE_DEG = 45.0
BAND_OVERLAP = 1.25
MIN_BAND_MM = 0.5
MIN_RING_AREA_MM2 = 1.0
SIMPLIFY_MM = 0.2
DEFAULT_SPACING = {"shader": 2.0, "marker": 2.0, "hatch": 1.2}
EMPTY = Polygon()


def _is_white(rgb) -> bool:
    return rgb is not None and all(c >= 230 for c in rgb[:3])


def _signed_area(ring) -> float:
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))


def _ring_polygon(ring) -> BaseGeometry:
    if len(ring) < 3:
        return EMPTY
    return _polys_only(shapely.make_valid(Polygon(ring)))


def _polys_only(g: BaseGeometry) -> BaseGeometry:
    """Keep only the areal part of a geometry (make_valid may emit lines/points)."""
    if g.is_empty or g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [p for p in getattr(g, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")]
    return shapely.union_all(parts) if parts else EMPTY


def _shape_area(shape: FilledShape, drop_small: bool) -> BaseGeometry:
    rings = [r for r in shape.outline if len(r) >= 3]
    polys = [_ring_polygon(r) for r in rings]
    keep = [i for i, p in enumerate(polys)
            if not p.is_empty and (not drop_small or p.area >= MIN_RING_AREA_MM2)]
    if not keep:
        return EMPTY
    if shape.fill_rule == "evenodd":
        g = EMPTY
        for i in keep:
            g = g.symmetric_difference(polys[i])
        return _polys_only(shapely.make_valid(g))
    # nonzero: winding number per nesting level (exact for nested, non-crossing rings)
    signs = {i: 1 if _signed_area(rings[i]) >= 0 else -1 for i in keep}
    for i in keep:
        shapely.prepare(polys[i])
    grown = {i: polys[i].buffer(1e-6) for i in keep}

    def contains(j, i):
        return (polys[j].area > polys[i].area or (polys[j].area == polys[i].area and j < i)) \
            and grown[j].covers(polys[i])

    parents = {i: [j for j in keep if j != i and contains(j, i)] for i in keep}
    regions = []
    for i in keep:
        winding = signs[i] + sum(signs[j] for j in parents[i])
        if winding == 0:
            continue
        kids = [k for k in keep if i in parents[k]
                and not any(m in parents[k] and i in parents[m] for m in keep)]
        region = polys[i]
        if kids:
            region = region.difference(shapely.union_all([polys[k] for k in kids]))
        regions.append(region)
    if not regions:
        return EMPTY
    return _polys_only(shapely.make_valid(shapely.union_all(regions)))


def _lines(g: BaseGeometry) -> list[LineString]:
    if g.is_empty:
        return []
    if g.geom_type in ("LineString", "LinearRing"):
        return [LineString(g.coords)]
    out = []
    for part in getattr(g, "geoms", []):
        out.extend(_lines(part))
    return out


def _inset_area(area: BaseGeometry, inset: float, outer_only: bool) -> BaseGeometry:
    if inset <= 0:
        return area
    if not outer_only:
        return area.buffer(-inset)
    parts = []
    for poly in getattr(area, "geoms", [area]):
        if poly.geom_type != "Polygon":
            continue
        g = Polygon(poly.exterior).buffer(-inset)
        if poly.interiors and not g.is_empty:
            g = g.difference(shapely.union_all([Polygon(r) for r in poly.interiors]))
        parts.append(g)
    return shapely.union_all(parts) if parts else EMPTY


def _band(area: BaseGeometry, spacing: float, inset: float, angle: float,
          outer_only: bool = False) -> list[LineString]:
    """Parallel lines `spacing` apart at `angle` degrees, clipped to `area` inset by `inset`."""
    if area.is_empty:
        return []
    inner = _inset_area(area, inset, outer_only)
    if inner.is_empty:
        return []
    origin = inner.centroid
    rot = affinity.rotate(inner, -angle, origin=origin) if angle else inner
    minx, miny, maxx, maxy = rot.bounds
    n = int(math.floor((maxy - miny) / spacing))
    y0 = miny + ((maxy - miny) - n * spacing) / 2.0
    out = []
    for k in range(n + 1):
        y = y0 + k * spacing
        line = LineString([(minx - 1, y), (maxx + 1, y)])
        for seg in _lines(rot.intersection(line)):
            if seg.length < MIN_BAND_MM:
                continue
            if angle:
                seg = affinity.rotate(seg, angle, origin=origin)
            out.append(seg)
    return out


def _render(shapes, method, spacing, category, drop_small, simplify, cache, inset="half") -> list[Stroke]:
    key = drop_small
    if key not in cache:
        cache[key] = [_shape_area(s, drop_small) if s.fill_rgb is not None else EMPTY
                      for s in shapes]
    areas = cache[key]
    n = len(shapes)

    # union of everything painted above shape i
    above = [EMPTY] * n
    acc = EMPTY
    for i in range(n - 1, -1, -1):
        above[i] = acc
        if not areas[i].is_empty:
            acc = acc.union(areas[i])

    # outline colour for white fills: the fill they sit on (resolved for white-on-white)
    white_color: dict[int, str] = {}

    def outline_color(i: int) -> str:
        s = shapes[i]
        if s.fill_rgb is None:
            return to_pen_color(s.stroke_rgb, category)[0]
        if not _is_white(s.fill_rgb):
            return to_pen_color(s.fill_rgb, category)[0]
        if i not in white_color:
            color = "black"
            for j in range(i - 1, -1, -1):
                if areas[j].is_empty or areas[j].intersection(areas[i]).area <= 1e-9:
                    continue
                color = outline_color(j)
                break
            white_color[i] = color
        return white_color[i]

    if method == "hatch":
        width, angle = HATCH_WIDTH_MM, HATCH_ANGLE_DEG
    else:
        width, angle = spacing * BAND_OVERLAP, 0.0

    factor = {"half": 0.5, "quarter": 0.25, "outer": 0.5}[inset]
    fill_strokes: list[Stroke] = []
    outline_strokes: list[Stroke] = []
    for i, s in enumerate(shapes):
        if s.fill_rgb is None and s.stroke_rgb is None:
            continue
        cover = above[i]
        if s.fill_rgb is not None:
            if areas[i].is_empty:
                continue
            if not _is_white(s.fill_rgb):
                visible = areas[i].difference(cover) if not cover.is_empty else areas[i]
                name, rgba = to_pen_color(s.fill_rgb, category)
                for seg in _band(visible, spacing, width * factor, angle, inset == "outer"):
                    pts = [tuple(p) for p in seg.coords]
                    if method == "shader":
                        fill_strokes.append(Stroke(pts, pen="shader", width_mm=width, rgba=rgba))
                    elif method == "marker":
                        fill_strokes.append(Stroke(pts, pen="marker", color=name, width_mm=width))
                    else:
                        fill_strokes.append(Stroke(pts, pen="fineliner", color=name, width_mm=width))
            edge = areas[i].boundary
            o_width = OUTLINE_WIDTH_MM
        else:
            rings = [r for r in s.outline if len(r) >= 2]
            if drop_small:
                rings = [r for r in rings if not (r[0] == r[-1] and len(r) >= 4
                                                  and _ring_polygon(r).area < MIN_RING_AREA_MM2)]
            if not rings:
                continue
            edge = MultiLineString([r for r in rings])
            o_width = max(0.3, s.stroke_width_mm)
        if not cover.is_empty:
            edge = edge.difference(cover)
        edge = shapely.line_merge(edge) if not edge.is_empty and edge.geom_type == "MultiLineString" else edge
        color = outline_color(i)
        for line in _lines(edge):
            if simplify:
                line = line.simplify(SIMPLIFY_MM)
            if line.length <= 0:
                continue
            outline_strokes.append(Stroke([tuple(p) for p in line.coords], pen="fineliner",
                                          color=color, width_mm=o_width))
    return fill_strokes + outline_strokes


def shapes_to_strokes(
    shapes: list[FilledShape],
    method: str = "shader",
    spacing_mm: float | None = None,
    budget: int = 150,
    category: str | None = None,
    inset: str = "half",
) -> list[Stroke]:
    """Convert shapes (in paint order) to fill strokes followed by outline strokes.

    Over budget: widen spacing in 25% steps up to 2x, then drop rings < 1 mm^2,
    then simplify outlines at 0.2 mm; raise ValueError if still over.
    inset: "half" (band edge inset by width/2), "quarter" (width/4), or "outer" (only the
    exterior boundary is inset by width/2; holes keep their true edge).
    """
    if inset not in ("half", "quarter", "outer"):
        raise ValueError(f"unknown inset {inset!r}")
    if method not in DEFAULT_SPACING:
        raise ValueError(f"unknown fill method {method!r}")
    base = spacing_mm if spacing_mm is not None else DEFAULT_SPACING[method]
    if base <= 0:
        raise ValueError("spacing_mm must be positive")
    cache: dict = {}
    attempts = [(base * f, False, False) for f in (1.0, 1.25, 1.5, 1.75, 2.0)]
    attempts += [(base * 2.0, True, False), (base * 2.0, True, True)]
    strokes: list[Stroke] = []
    for spacing, drop_small, simplify in attempts:
        strokes = _render(shapes, method, spacing, category, drop_small, simplify, cache, inset)
        if len(strokes) <= budget:
            return strokes
    raise ValueError(f"{len(strokes)} strokes exceed the budget of {budget} after simplification")
