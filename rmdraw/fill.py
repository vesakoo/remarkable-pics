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
SPUR_MAX_ANGLE_DEG = 100.0
MIN_BAND_MM = 0.5
MIN_RING_AREA_MM2 = 1.0
SIMPLIFY_MM = 0.2
DEFAULT_SPACING = {"shader": 1.2, "marker": 2.0, "hatch": 1.2}
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


def filled_area(shapes: list[FilledShape]) -> BaseGeometry:
    """Union of the areas of all filled shapes (white ones included): what they hide."""
    areas = [_shape_area(s, False) for s in shapes if s.fill_rgb is not None]
    areas = [a for a in areas if not a.is_empty]
    return shapely.union_all(areas) if areas else EMPTY


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


def _sharp_corners(poly: Polygon, max_angle_deg: float):
    """(vertex, unit inward bisector, interior angle rad) for convex corners sharper than max."""
    out = []
    for ring in [poly.exterior, *poly.interiors]:
        pts = list(ring.coords)[:-1]
        n = len(pts)
        if n < 3:
            continue
        for i in range(n):
            v, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
            ax, ay = a[0] - v[0], a[1] - v[1]
            bx, by = b[0] - v[0], b[1] - v[1]
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            if la < 1e-9 or lb < 1e-9:
                continue
            cosang = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
            alpha = math.acos(cosang)
            if alpha < 1e-3 or math.degrees(alpha) >= max_angle_deg:
                continue
            ux, uy = ax / la + bx / lb, ay / la + by / lb
            lu = math.hypot(ux, uy)
            if lu < 1e-9:
                continue
            ux, uy = ux / lu, uy / lu
            probe = (v[0] + ux * 1e-4, v[1] + uy * 1e-4)
            if not poly.contains(shapely.geometry.Point(probe)):
                continue  # reflex corner of the filled region
            out.append((v, (ux, uy), alpha))
    return out


def _contour_fill(area: BaseGeometry, spacing: float, width: float,
                  angle: float) -> list[tuple[LineString, float]]:
    """Fill that never paints outside `area`, round caps included.

    A closed contour stroke runs width/2 inside every boundary ring (covering the edge strip),
    parallel bands fill the rest and end where their caps just overlap the contour, and short
    thinner spur strokes reach into acute corners. Returns (line, stroke width) pairs.
    """
    out: list[tuple[LineString, float]] = []
    overlap = max(0.0, width - spacing)
    for poly in getattr(area, "geoms", [area]):
        if poly.geom_type != "Polygon" or poly.is_empty:
            continue
        # thin parts: shrink the stroke until it fits
        w = width
        inner = poly.buffer(-w / 2)
        while inner.is_empty and w > 0.2:
            w /= 2
            inner = poly.buffer(-w / 2)
        if inner.is_empty:
            continue
        for ring in _lines(inner.boundary):
            if ring.length >= MIN_BAND_MM / 2:
                out.append((ring, w))
        core = poly.buffer(-w)
        if not core.is_empty:
            reach = max(width / 2, w + width / 2 - overlap - spacing / 2)
            for seg in _band(poly, spacing, reach, angle):
                out.append((seg, width))
        safe = poly.buffer(1e-6)
        shapely.prepare(safe)
        for v, (ux, uy), alpha in _sharp_corners(poly, SPUR_MAX_ANGLE_DEG):
            s2 = math.sin(alpha / 2)
            start = (w / 2) / s2
            t = w
            for _ in range(2):
                t /= 2
                end = (t / 2) / s2
                if start - end < 0.1:
                    break
                seg = LineString([(v[0] + ux * start, v[1] + uy * start),
                                  (v[0] + ux * end, v[1] + uy * end)])
                if safe.contains(seg.buffer(t / 2, quad_segs=4)):
                    out.append((seg, t))
                start = end
    return out


def _render(shapes, method, spacing, category, drop_small, simplify, cache, inset="half",
            outlines=True, overlap=BAND_OVERLAP) -> list[Stroke]:
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
        width, angle = spacing * overlap, 0.0

    factor = {"half": 0.5, "quarter": 0.25, "outer": 0.5, "contour": 0.25}[inset]
    use_contour = inset == "contour" and method != "hatch"
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
                if use_contour:
                    parts = _contour_fill(visible, spacing, width, angle)
                else:
                    parts = [(seg, width) for seg in
                             _band(visible, spacing, width * factor, angle, inset == "outer")]
                for seg, w in parts:
                    pts = [tuple(p) for p in seg.coords]
                    if method == "shader":
                        fill_strokes.append(Stroke(pts, pen="shader", width_mm=w, rgba=rgba))
                    elif method == "marker":
                        fill_strokes.append(Stroke(pts, pen="marker", color=name, width_mm=w))
                    else:
                        fill_strokes.append(Stroke(pts, pen="fineliner", color=name, width_mm=w))
            if not outlines:
                continue
            edge = areas[i].boundary
            o_width = OUTLINE_WIDTH_MM
        else:
            if not outlines:
                continue
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
    inset: str = "contour",
    outlines: bool = True,
    overlap: float = BAND_OVERLAP,
) -> list[Stroke]:
    """Convert shapes (in paint order) to fill strokes followed by outline strokes.

    Over budget: widen spacing in 25% steps up to 2x, then drop rings < 1 mm^2,
    then simplify outlines at 0.2 mm; raise ValueError if still over.
    inset: "contour" (default; no ink outside the shape: an edge contour stroke, bands inside it and
    thin spurs into acute corners), "quarter" (band edge inset by width/4; round caps overshoot),
    "half" (width/2), or "outer" (only the exterior boundary is inset by width/2). "contour" falls
    back to "quarter" for the hatch method. overlap: band width as a multiple of the spacing.
    outlines=False returns only the fill strokes (the caller draws its own outlines).
    """
    if inset not in ("contour", "half", "quarter", "outer"):
        raise ValueError(f"unknown inset {inset!r}")
    if method not in DEFAULT_SPACING:
        raise ValueError(f"unknown fill method {method!r}")
    base = spacing_mm if spacing_mm is not None else DEFAULT_SPACING[method]
    if base <= 0:
        raise ValueError("spacing_mm must be positive")
    if overlap < 1.0:
        raise ValueError("overlap must be >= 1.0 (bands would leave gaps)")
    cache: dict = {}
    attempts = [(base * f, False, False) for f in (1.0, 1.25, 1.5, 1.75, 2.0)]
    attempts += [(base * 2.0, True, False), (base * 2.0, True, True)]
    strokes: list[Stroke] = []
    for spacing, drop_small, simplify in attempts:
        strokes = _render(shapes, method, spacing, category, drop_small, simplify, cache, inset,
                          outlines, overlap)
        if len(strokes) <= budget:
            return strokes
    raise ValueError(f"{len(strokes)} strokes exceed the budget of {budget} after simplification")
