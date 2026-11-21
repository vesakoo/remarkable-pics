from pathlib import Path

from rmdraw.dump import dump

ROOT = Path(__file__).resolve().parent.parent

REF = ROOT / "tests/fixtures/reference/8854cd39-dba3-48f7-8c5f-e6b9f0cea45f"
PAGE1 = REF / "f4017db6-bda2-43bb-a742-cf6640428bd6.rm"
PAGE2 = REF / "ca78643d-4662-48ef-a930-7e6a87dc6b71.rm"


def test_reference_page1_has_expected_strokes():
    strokes = dump(PAGE1)
    assert len(strokes) >= 47
    tools = {s["tool"] for s in strokes}
    assert {"FINELINER_2", "MARKER_2", "SHADER", "HIGHLIGHTER_2"} <= tools
    assert any(s["color"] == "CYAN" for s in strokes)
    assert any(s["rgba"] is not None for s in strokes)
    colors = {s["color"] for s in strokes}
    assert {"HIGHLIGHT_BLUE", "HIGHLIGHT_ORANGE", "HIGHLIGHT_GRAY"} <= colors
    for s in strokes:
        assert set(s) == {"tool", "color", "rgba", "thickness_scale", "n_points", "bbox"}


def test_reference_page2_scaled_copy():
    strokes = dump(PAGE2)
    assert len(strokes) == 2
    assert strokes[1]["thickness_scale"] > 3.0
