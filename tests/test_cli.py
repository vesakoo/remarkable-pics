import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from rmdraw import cli, device, shapes_json
from rmdraw.dump import dump
from rmdraw.geometry import PAGE_H_MM, PAGE_W_MM

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
RECT_SVG = ROOT / "tests/fixtures/svg/rect.svg"


def _pages(rmdoc: Path, tmp_path: Path) -> list[list[dict]]:
    with zipfile.ZipFile(rmdoc) as z:
        content = next(n for n in z.namelist() if n.endswith(".content"))
        uid = content[: -len(".content")]
        pages = json.loads(z.read(content))["cPages"]["pages"]
        out = []
        for p in pages:
            f = tmp_path / f"{p['id']}.rm"
            f.write_bytes(z.read(f"{uid}/{p['id']}.rm"))
            out.append(dump(f))
    return out


def _write_json(tmp_path: Path, items, name="t") -> Path:
    p = tmp_path / "shapes.json"
    p.write_text(json.dumps({"name": name, "pages": [items]}))
    return p


@pytest.mark.parametrize("example", ["smiley.json", "tree.json"])
def test_cli_build_smiley(tmp_path, example):
    out = tmp_path / "out.rmdoc"
    assert cli.main(["build", str(EXAMPLES / example), "-o", str(out)]) == 0
    pages = _pages(out, tmp_path)
    assert len(pages) == 1
    assert len(pages[0]) >= 4
    tools = {s["tool"] for s in pages[0]}
    assert "SHADER" in tools and "FINELINER_2" in tools
    svg = tmp_path / "page.svg"
    assert cli.main(["preview", str(out), "-o", str(svg)]) == 0
    assert svg.read_text().startswith("<svg")


def test_cli_svg(tmp_path):
    out = tmp_path / "rect.rmdoc"
    assert cli.main(["svg", str(RECT_SVG), "-o", str(out), "--box", "20,20,40,40",
                     "--name", "Rect"]) == 0
    pages = _pages(out, tmp_path)
    assert len(pages) == 1 and pages[0]
    assert any(s["tool"] == "SHADER" for s in pages[0])
    with zipfile.ZipFile(out) as z:
        meta = next(n for n in z.namelist() if n.endswith(".metadata"))
        assert json.loads(z.read(meta))["visibleName"] == "Rect"

    out2 = tmp_path / "rect-none.rmdoc"
    assert cli.main(["svg", str(RECT_SVG), "-o", str(out2), "--fill", "none"]) == 0
    strokes = _pages(out2, tmp_path)[0]
    assert strokes and all(s["tool"] == "FINELINER_2" for s in strokes)


def test_shapes_json_rejects_unknown_type(tmp_path):
    p = _write_json(tmp_path, [{"type": "circle", "cx": 50, "cy": 50, "r": 10},
                               {"type": "star", "cx": 1, "cy": 1}])
    with pytest.raises(ValueError, match=r"pages\[0\]\[1\].*unknown type 'star'"):
        shapes_json.load(p)


@pytest.mark.parametrize("item, field", [
    ({"type": "circle", "cx": 50, "cy": 50, "r": 10, "pen": "crayon"}, "pen"),
    ({"type": "circle", "cx": 50, "cy": 50, "r": 10, "color": "orange"}, "color"),
    ({"type": "circle", "cx": 50, "cy": 50, "r": 10, "fill": {"color": "#12345"}}, "fill.color"),
    ({"type": "circle", "cx": 50, "cy": 50, "r": -1}, "r"),
    ({"type": "circle", "cx": 50, "cy": 50, "r": 10, "radius": 3}, "radius"),
    ({"type": "polyline", "points": [[1, 2]]}, "points"),
    ({"type": "arc", "cx": 50, "cy": 50, "r": 10, "start_deg": 10, "end_deg": 20,
      "fill": {"color": "red"}}, "fill"),
])
def test_shapes_json_names_bad_field(tmp_path, item, field):
    p = _write_json(tmp_path, [item])
    with pytest.raises(ValueError) as e:
        shapes_json.load(p)
    assert "pages[0][0]" in str(e.value)
    assert field in str(e.value)


def test_shapes_json_offpage_point(tmp_path):
    p = _write_json(tmp_path, [{"type": "circle", "cx": PAGE_W_MM - 5, "cy": 50, "r": 10}])
    with pytest.raises(ValueError, match=r"pages\[0\]\[0\].*off the page"):
        shapes_json.load(p)
    p = _write_json(tmp_path, [{"type": "polyline", "points": [[10, 10], [20, PAGE_H_MM + 1]]}])
    with pytest.raises(ValueError, match=r"pages\[0\]\[0\].*off the page"):
        shapes_json.load(p)


def _cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d
                 for a, b, c, d in zip(p0, p1, p2, p3))


def _dist_to_polyline(q, pts):
    best = math.inf
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((q[0] - x0) * dx + (q[1] - y0) * dy) / L2))
        best = min(best, math.hypot(q[0] - (x0 + t * dx), q[1] - (y0 + t * dy)))
    return best


def test_bezier_and_arc_flatten():
    tol = shapes_json.TOLERANCE_MM
    assert tol == 0.15
    # arc: clockwise from 3 o'clock (y down), so 0..90 goes from right to bottom
    pts = shapes_json.flatten_arc(50, 50, 20, 20, 0, 90)
    assert pts[0] == pytest.approx((70, 50))
    assert pts[-1] == pytest.approx((50, 70))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        assert math.hypot(x0 - 50, y0 - 50) == pytest.approx(20)
        assert math.hypot((x0 + x1) / 2 - 50, (y0 + y1) / 2 - 50) >= 20 - tol - 1e-9
    assert 4 < len(pts) < 40

    ctrl = [(10, 10), (10, 60), (80, 60), (80, 10), (80, -20), (120, 30), (130, 10)]
    pts = shapes_json.flatten_bezier(ctrl)
    assert pts[0] == pytest.approx((10, 10)) and pts[-1] == pytest.approx((130, 10))
    for seg in (ctrl[0:4], ctrl[3:7]):
        for k in range(201):
            assert _dist_to_polyline(_cubic(*seg, k / 200), pts) <= tol + 1e-6
    assert len(pts) < 100
    with pytest.raises(ValueError):
        shapes_json.flatten_bezier(ctrl[:5])


def test_cli_push_uses_device(tmp_path, monkeypatch, capsys):
    out = tmp_path / "s.rmdoc"
    assert cli.main(["build", str(EXAMPLES / "smiley.json"), "-o", str(out)]) == 0
    calls = {}

    def fake_install(path, host="root@10.11.99.1"):
        calls["install"] = (Path(path), host)
        return "0b1c2d3e-0000-4000-8000-000000000000"

    def fake_thumbs(uuid, out_dir, host="root@10.11.99.1"):
        calls["thumbs"] = (uuid, Path(out_dir))
        return [Path(out_dir) / "p.png"]

    monkeypatch.setattr(device, "install_rmdoc", fake_install)
    monkeypatch.setattr(device, "fetch_thumbnails", fake_thumbs)
    capsys.readouterr()
    assert cli.main(["push", str(out), "--thumbs", str(tmp_path / "th")]) == 0
    assert calls["install"] == (out, "root@10.11.99.1")
    assert calls["thumbs"] == ("0b1c2d3e-0000-4000-8000-000000000000", tmp_path / "th")
    assert "0b1c2d3e-0000-4000-8000-000000000000" in capsys.readouterr().out


def test_cli_error_no_traceback(tmp_path, capsys):
    bad = _write_json(tmp_path, [{"type": "star"}])
    rc = cli.main(["build", str(bad), "-o", str(tmp_path / "x.rmdoc")])
    err = capsys.readouterr().err
    assert rc != 0
    assert "Traceback" not in err
    assert len(err.strip().splitlines()) == 1 and "unknown type" in err
    assert not (tmp_path / "x.rmdoc").exists()

    assert cli.main(["preview", str(tmp_path / "missing.rmdoc"), "-o", str(tmp_path / "p.svg")]) != 0
    assert len(capsys.readouterr().err.strip().splitlines()) == 1

    r = subprocess.run([sys.executable, "-m", "rmdraw", "build", str(bad), "-o",
                        str(tmp_path / "y.rmdoc")], capture_output=True, text=True)
    assert r.returncode != 0
    assert "Traceback" not in r.stderr and "unknown type" in r.stderr


def test_cli_dump(capsys):
    ref = ROOT / ("tests/fixtures/reference/8854cd39-dba3-48f7-8c5f-e6b9f0cea45f/"
                  "ca78643d-4662-48ef-a930-7e6a87dc6b71.rm")
    assert cli.main(["dump", str(ref)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2 and lines[0].startswith("tool=")


def test_paint_order_later_fill_hides_earlier(tmp_path):
    line = {"type": "polyline", "points": [[20, 50], [120, 50]]}
    gap = {"type": "rect", "x": 60, "y": 40, "w": 20, "h": 20, "fill": {"color": "white"}}
    doc = shapes_json.from_dict({"name": "t", "pages": [[line, gap]]})
    strokes = doc.pages[0].strokes
    # the line is cut in two around the white rect; the white fill draws nothing
    cut = [s for s in strokes if s.points[0][1] == 50 and s.points[-1][1] == 50]
    assert len(cut) == 2
    assert all(not (60 < x < 80) for s in cut for x, _ in s.points)
    assert not any(s.pen == "shader" for s in strokes)
    # listed the other way round, the line stays whole on top
    doc = shapes_json.from_dict({"name": "t", "pages": [[gap, line]]})
    assert any(s.points == [(20.0, 50.0), (120.0, 50.0)] for s in doc.pages[0].strokes)


def _many_lines_svg(tmp_path: Path, n: int = 200) -> Path:
    lines = "".join(f'<line x1="{i}" y1="0" x2="{i}" y2="50" stroke="#000"/>' for i in range(n))
    p = tmp_path / "many.svg"
    p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} 50" '
                 f'width="{n}" height="50">{lines}</svg>')
    return p


def test_svg_item_over_budget_names_index(tmp_path):
    svg = _many_lines_svg(tmp_path)
    p = _write_json(tmp_path, [{"type": "circle", "cx": 50, "cy": 50, "r": 10},
                               {"type": "svg", "path": svg.name, "box": [10, 10, 150, 60],
                                "fill": {"method": "none"}}])
    with pytest.raises(ValueError, match=r"pages\[0\]\[1\].*budget of 150"):
        shapes_json.load(p)


def test_cli_svg_budget(tmp_path, capsys):
    svg = _many_lines_svg(tmp_path)
    out = tmp_path / "m.rmdoc"
    assert cli.main(["svg", str(svg), "-o", str(out), "--fill", "none"]) != 0
    assert "budget of 150" in capsys.readouterr().err
    assert not out.exists()
    assert cli.main(["svg", str(svg), "-o", str(out), "--fill", "none", "--budget", "300"]) == 0
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and "warning" in err[0] and "300" in err[0]
    assert len(_pages(out, tmp_path)[0]) == 200


def test_filled_item_total_within_budget():
    item = {"type": "circle", "cx": 90, "cy": 120, "r": 75,
            "fill": {"color": "yellow", "spacing_mm": 0.5}}
    try:
        doc = shapes_json.from_dict({"name": "t", "pages": [[item]]})
    except ValueError as e:
        assert "pages[0][0]" in str(e)
    else:
        assert len(doc.pages[0].strokes) <= shapes_json.ITEM_BUDGET


@pytest.mark.parametrize("host", ["-oProxyCommand=touch /tmp/x", "root@10.11.99.1;ls",
                                  "10.11.99.1", "root@host -x", "-x@host"])
def test_cli_push_rejects_bad_host(tmp_path, monkeypatch, capsys, host):
    called = []
    monkeypatch.setattr(device, "install_rmdoc", lambda *a, **k: called.append(a))
    rmdoc = tmp_path / "s.rmdoc"
    rmdoc.write_bytes(b"")
    assert cli.main(["push", str(rmdoc), f"--host={host}"]) != 0
    assert "invalid host" in capsys.readouterr().err
    assert not called
