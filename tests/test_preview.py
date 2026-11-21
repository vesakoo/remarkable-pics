import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from rmdraw.geometry import PAGE_H_MM, PAGE_W_MM
from rmdraw.model import Document, Page, Stroke
from rmdraw.preview import render_rm_svg, render_rmdoc_svg
from rmdraw.rmdoc import write_rmdoc

from rmdraw.dump import dump

REF = Path(__file__).parent / (
    "fixtures/reference/8854cd39-dba3-48f7-8c5f-e6b9f0cea45f/"
    "f4017db6-bda2-43bb-a742-cf6640428bd6.rm"
)
NS = "{http://www.w3.org/2000/svg}"


def test_preview_contains_one_path_per_line(tmp_path):
    doc = Document("d", [Page([Stroke([(10, 10), (20, 30)]) for _ in range(3)])])
    p = tmp_path / "x.rmdoc"
    write_rmdoc(doc, p)
    svg = render_rmdoc_svg(p)
    root = ET.fromstring(svg)
    assert len(root.findall(f".//{NS}polyline")) == 3
    assert root.get("viewBox") == f"0 0 {PAGE_W_MM:.3f} {PAGE_H_MM:.3f}"


def test_reference_page_renders():
    root = ET.fromstring(render_rm_svg(REF.read_bytes()))
    assert len(root.findall(f".//{NS}polyline")) == len(dump(REF))


def test_page_index_out_of_range(tmp_path):
    p = tmp_path / "x.rmdoc"
    write_rmdoc(Document("d", [Page([Stroke([(1, 1), (2, 2)])])]), p)
    with pytest.raises(IndexError):
        render_rmdoc_svg(p, 1)
