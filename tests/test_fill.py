import math

import pytest
from shapely.geometry import Point, Polygon

from rmdraw.fill import shapes_to_strokes
from rmdraw.svgimport import FilledShape

ORANGE = (255, 153, 0)


def square(x, y, s, ccw=True):
    r = [(x, y), (x + s, y), (x + s, y + s), (x, y + s), (x, y)]
    return r if ccw else r[::-1]


def circle(cx, cy, r, n=64):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
           for i in range(n)]
    return pts + [pts[0]]


def fills(strokes):
    return [s for s in strokes if s.pen != "fineliner"]


def test_hatch_covers_square():
    sq = Polygon(square(0, 0, 20))
    out = shapes_to_strokes([FilledShape([square(0, 0, 20)], ORANGE, None)],
                            method="hatch", spacing_mm=1.5)
    hatch = out[:-1]
    assert out[-1].pen == "fineliner" and out[-1].width_mm == 0.35  # outline
    # 45 deg lines at 1.5 mm perpendicular spacing across a 20 mm square
    expected = 20 * math.sqrt(2) / 1.5
    assert abs(len(hatch) - expected) <= 2
    for s in hatch:
        assert s.pen == "fineliner" and s.width_mm == 0.3
        assert s.color == "yellow"
        (x0, y0), (x1, y1) = s.points[0], s.points[-1]
        assert abs(abs(x1 - x0) - abs(y1 - y0)) < 1e-6  # 45 degrees
        for p in s.points:
            assert sq.buffer(1e-6).contains(Point(p))


def test_shader_fill_default():
    sq = Polygon(square(10, 10, 20))
    out = shapes_to_strokes([FilledShape([square(10, 10, 20)], ORANGE, None)])
    f = fills(out)
    assert len(f) >= 14
    for s in f:
        assert s.pen == "shader"
        assert s.rgba == (255, 153, 0, 230)
        assert s.width_mm == pytest.approx(1.5)  # default spacing 1.2 x overlap 1.25
        for p in s.points:
            assert sq.contains(Point(p))
        # default inset is a quarter of the band width
        for p in s.points:
            assert sq.exterior.distance(Point(p)) >= 0.375 - 1e-6


def test_marker_fill_uses_palette():
    out = shapes_to_strokes([FilledShape([square(0, 0, 20)], ORANGE, None)], method="marker")
    f = fills(out)
    assert f and all(s.pen == "marker" and s.color == "yellow" and s.rgba is None for s in f)


def test_outline_on_top():
    out = shapes_to_strokes([FilledShape([square(0, 0, 20)], (47, 95, 208), None)])
    assert out[-1].pen == "fineliner"
    assert out[-1].color == "blue"
    assert out[-1].width_mm == 0.35
    first_outline = next(i for i, s in enumerate(out) if s.pen == "fineliner")
    assert all(s.pen == "fineliner" for s in out[first_outline:])
    assert all(s.pen == "shader" for s in out[:first_outline])


def test_white_glyph_becomes_gap():
    circ = Polygon(circle(20, 20, 6))
    shapes = [FilledShape([square(0, 0, 40)], ORANGE, None),
              FilledShape([circle(20, 20, 6)], (255, 255, 255), None)]
    out = shapes_to_strokes(shapes)
    inner = circ.buffer(-0.05)
    for s in fills(out):
        for a, b in zip(s.points, s.points[1:]):
            from shapely.geometry import LineString
            assert not LineString([a, b]).intersects(inner)
    outlines = [s for s in out if s.pen == "fineliner"]
    # circle edge is outlined in the parent's palette colour
    circle_outlines = [s for s in outlines
                       if all(abs(Point(p).distance(Point(20, 20)) - 6) < 0.1 for p in s.points)]
    assert circle_outlines and all(s.color == "yellow" for s in circle_outlines)
    for s in out:
        assert s.color != "white"
        if s.rgba is not None:
            assert not all(c >= 230 for c in s.rgba[:3])


def test_white_on_nothing_outlined_black():
    out = shapes_to_strokes([FilledShape([circle(20, 20, 6)], (255, 255, 255), None)])
    assert out and all(s.pen == "fineliner" and s.color == "black" for s in out)


def test_painter_order():
    blue = FilledShape([square(0, 0, 20)], (47, 95, 208), None)
    red = FilledShape([square(10, 10, 20)], (210, 58, 44), None)
    out = shapes_to_strokes([blue, red])
    red_area = Polygon(square(10, 10, 20)).buffer(-0.05)
    blue_fills = [s for s in fills(out) if s.rgba[:3] == (47, 95, 208)]
    red_fills = [s for s in fills(out) if s.rgba[:3] == (210, 58, 44)]
    assert blue_fills and red_fills
    from shapely.geometry import LineString
    for s in blue_fills:
        assert not LineString(s.points).intersects(red_area)
    # the blue outline is clipped where the red square covers it
    for s in out:
        if s.pen == "fineliner" and s.color == "blue":
            assert not LineString(s.points).intersects(red_area)


def test_nonzero_hole_by_orientation():
    shp = FilledShape([square(0, 0, 30), square(10, 10, 10, ccw=False)], ORANGE, None)
    hole = Polygon(square(10, 10, 10)).buffer(-0.05)
    from shapely.geometry import LineString
    f = fills(shapes_to_strokes([shp]))
    assert f
    for s in f:
        assert not LineString(s.points).intersects(hole)


def test_evenodd_hole():
    shp = FilledShape([square(0, 0, 30), square(10, 10, 10)], ORANGE, None, fill_rule="evenodd")
    hole = Polygon(square(10, 10, 10)).buffer(-0.05)
    from shapely.geometry import LineString
    for s in fills(shapes_to_strokes([shp])):
        assert not LineString(s.points).intersects(hole)


def test_stroke_only_shape():
    shp = FilledShape([[(0, 0), (30, 5)]], None, (210, 58, 44), stroke_width_mm=0.8)
    out = shapes_to_strokes([shp])
    assert len(out) == 1
    assert out[0].pen == "fineliner" and out[0].color == "red" and out[0].width_mm == 0.8


def test_category_overrides_colours():
    out = shapes_to_strokes([FilledShape([square(0, 0, 20)], ORANGE, None)],
                            method="marker", category="networking")
    assert all(s.color == "magenta" for s in out)


def test_budget_enforced():
    rings = [square(0, 0, 60)]
    for i in range(20):
        for j in range(20):
            rings.append(square(5 + i * 2.5, 5 + j * 2.5, 0.6))
    shp = FilledShape(rings, ORANGE, None, fill_rule="evenodd")
    out = shapes_to_strokes([shp], budget=150)
    assert 0 < len(out) <= 150


def test_budget_impossible_raises():
    shapes = [FilledShape([square(i * 3, 0, 2)], (0, 0, 0), None) for i in range(50)]
    with pytest.raises(ValueError, match="exceed the budget of 10"):
        shapes_to_strokes(shapes, budget=10)


def _band_len(strokes):
    return sum(math.dist(a, b) for s in strokes if s.pen == "shader"
               for a, b in zip(s.points, s.points[1:]))


def test_inset_outer_has_more_band_than_half():
    glyph = [square(x, y, 2.0, ccw=False) for x in (6, 12) for y in (6, 12)]
    shapes = [FilledShape([square(0, 0, 20)] + glyph, ORANGE, None, fill_rule="evenodd")]
    half = shapes_to_strokes(shapes, spacing_mm=1.2, inset="half", budget=1000)
    quarter = shapes_to_strokes(shapes, spacing_mm=1.2, inset="quarter", budget=1000)
    outer = shapes_to_strokes(shapes, spacing_mm=1.2, inset="outer", budget=1000)
    assert _band_len(outer) > _band_len(half)
    assert _band_len(quarter) > _band_len(half)


def test_inset_invalid():
    with pytest.raises(ValueError):
        shapes_to_strokes([FilledShape([square(0, 0, 5)], ORANGE, None)], inset="bogus")
