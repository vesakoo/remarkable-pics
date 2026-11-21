import io
from pathlib import Path

import pytest
import rmdraw  # noqa: F401
from rmscene import read_blocks
from rmscene.scene_items import Pen, PenColor
from rmscene.scene_stream import SceneLineItemBlock, UnreadableBlock

from rmdraw.geometry import mm_to_units
from rmdraw.model import Page, Stroke
from rmdraw.rmwriter import page_blocks, write_page

REF = Path(__file__).parent / "fixtures/reference/8854cd39-dba3-48f7-8c5f-e6b9f0cea45f/f4017db6-bda2-43bb-a742-cf6640428bd6.rm"


def _write(page):
    buf = io.BytesIO()
    write_page(page, buf)
    buf.seek(0)
    return buf


def _lines(page):
    return [
        b.item.value
        for b in read_blocks(_write(page))
        if isinstance(b, SceneLineItemBlock) and b.item.value is not None
    ]


def test_round_trip_preserves_strokes():
    rgba = (250, 231, 25, 115)
    page = Page(
        [
            Stroke([(10, 10), (20, 20)], "fineliner", "black"),
            Stroke([(30, 30), (40, 50), (50, 60)], "marker", "blue"),
            Stroke([(60, 60), (80, 60)], "shader", "yellow", rgba=rgba),
        ]
    )
    blocks = list(read_blocks(_write(page)))
    assert not any(isinstance(b, UnreadableBlock) for b in blocks)
    lines = _lines(page)
    assert len(lines) == 3
    assert [l.tool for l in lines] == [Pen.FINELINER_2, Pen.MARKER_2, Pen.SHADER]
    assert [l.color for l in lines] == [PenColor.BLACK, PenColor.BLUE, PenColor.HIGHLIGHT]
    assert lines[2].color_rgba == rgba
    ex, ey = mm_to_units(10, 10)
    assert abs(lines[0].points[0].x - ex) < 0.01
    assert abs(lines[0].points[0].y - ey) < 0.01


def test_long_stroke_is_chunked():
    pts = [(10 + i * 0.1, 10 + (i % 7)) for i in range(1200)]
    lines = _lines(Page([Stroke(pts)]))
    assert len(lines) == 3
    assert all(len(l.points) <= 500 for l in lines)
    # chunks overlap by one point so the stroke stays continuous
    assert lines[0].points[-1].x == lines[1].points[0].x
    assert lines[1].points[-1].x == lines[2].points[0].x


def test_out_of_bounds_raises():
    with pytest.raises(ValueError):
        page_blocks(Page([Stroke([(-1, 10), (5, 5)])]))
    with pytest.raises(ValueError):
        page_blocks(Page([Stroke([])]))


def test_header_matches_reference_structure():
    skip = {"SceneLineItemBlock", "UnreadableBlock", "SceneTombstoneItemBlock"}

    def names(blocks):
        return [type(b).__name__ for b in blocks if type(b).__name__ not in skip]

    ref = names(read_blocks(REF.open("rb")))
    ours = names(page_blocks(Page([Stroke([(10, 10), (20, 20)])])))
    assert ours == ref
