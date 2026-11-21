import math
import warnings
from pathlib import Path

import pytest

from rmdraw.svgimport import svg_to_shapes

FX = Path(__file__).parent / "fixtures" / "svg"
BOX = (10.0, 20.0, 48.0, 48.0)


def bounds(shape):
    pts = [p for r in shape.outline for p in r]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def test_rect_maps_into_box():
    (s,) = svg_to_shapes(FX / "rect.svg", BOX)
    assert bounds(s) == pytest.approx((10, 20, 58, 68))
    assert s.fill_rgb == (255, 128, 0)
    assert s.stroke_rgb is None
    assert s.outline[0][0] == s.outline[0][-1]


def test_group_transform_applied():
    (s,) = svg_to_shapes(FX / "group_translate.svg", BOX)
    assert bounds(s) == pytest.approx((20, 20, 30, 30))


def test_circle_flattened_smoothly():
    tol = 0.15
    (s,) = svg_to_shapes(FX / "circle.svg", (0, 0, 96, 96), tolerance_mm=tol)
    assert s.stroke_rgb == (255, 0, 0)
    assert s.stroke_width_mm == pytest.approx(4.0)
    ring = s.outline[0]
    assert len(ring) > 12
    for x, y in ring:
        assert abs(math.hypot(x - 48, y - 48) - 40) <= tol
    # chord midpoints must also be near the circle
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        m = math.hypot((x0 + x1) / 2 - 48, (y0 + y1) / 2 - 48)
        assert 40 - m <= tol


def test_gradient_uses_first_stop():
    (s,) = svg_to_shapes(FX / "gradient.svg", BOX)
    assert s.fill_rgb == (255, 0, 0)


def test_clip_path_ignored_with_warning():
    with pytest.warns(UserWarning, match="clip-path") as rec:
        (s,) = svg_to_shapes(FX / "clip.svg", BOX)
    assert len([w for w in rec if "clip-path" in str(w.message)]) == 1
    assert bounds(s) == pytest.approx((10, 20, 20, 30))


def test_use_element_resolved():
    (s,) = svg_to_shapes(FX / "use.svg", BOX)
    assert bounds(s) == pytest.approx((30, 25, 40, 35))


def test_evenodd_ring_count():
    (s,) = svg_to_shapes(FX / "evenodd.svg", BOX)
    assert len(s.outline) == 2
    assert s.fill_rule == "evenodd"


def test_aspect_fit_and_hidden_skipped():
    shapes = svg_to_shapes(FX / "wide.svg", (0, 0, 20, 20))
    assert len(shapes) == 1
    assert bounds(shapes[0]) == pytest.approx((0, 5, 20, 15))
