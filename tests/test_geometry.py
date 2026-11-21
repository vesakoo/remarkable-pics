import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from rmdraw.geometry import (
    COLOR_NAMES,
    PAGE_H_MM,
    PAGE_W_MM,
    mm_to_units,
    units_to_mm,
    width_to_device,
)
from dump_rm import dump  # noqa: E402

REF = Path(__file__).parent / "fixtures/reference/8854cd39-dba3-48f7-8c5f-e6b9f0cea45f/f4017db6-bda2-43bb-a742-cf6640428bd6.rm"


def _corner_dots():
    dots = []
    for s in dump(REF):
        if s["tool"] != "FINELINER_2" or s["bbox"] is None:
            continue
        x0, y0, x1, y1 = s["bbox"]
        if x1 - x0 < 15 and y1 - y0 < 15:
            dots.append(((x0 + x1) / 2, (y0 + y1) / 2))
    return dots


def test_exact_corners():
    x, y = mm_to_units(0, 0)
    assert abs(x + 810) < 1e-6 and abs(y) < 1e-6
    x, y = mm_to_units(PAGE_W_MM, PAGE_H_MM)
    assert abs(x - 810) < 1e-6 and abs(y - 2160) < 1e-6


def test_centre():
    x, y = mm_to_units(PAGE_W_MM / 2, PAGE_H_MM / 2)
    assert abs(x) < 1e-6 and abs(y - 1080) < 1e-6


def test_round_trip():
    x, y = units_to_mm(*mm_to_units(12.5, 80.25))
    assert abs(x - 12.5) < 1e-9 and abs(y - 80.25) < 1e-9


def test_reference_corner_dots_within_15mm():
    dots = [units_to_mm(x, y) for x, y in _corner_dots()]
    assert len(dots) >= 4
    for cx, cy in [(0, 0), (PAGE_W_MM, 0), (0, PAGE_H_MM), (PAGE_W_MM, PAGE_H_MM)]:
        d = min(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in dots)
        assert d < 15, (cx, cy, d)


def test_width_round_trip():
    scale, w = width_to_device("fineliner", 0.44)
    assert scale == 2.0
    assert abs(w - 16) <= 4


def test_width_clamped():
    assert width_to_device("fineliner", 0)[1] == 1
    assert width_to_device("fineliner", 1e6)[1] == 65535


def test_colour_names():
    assert COLOR_NAMES["hl_orange"] == 15
    assert COLOR_NAMES["green"] == 10
