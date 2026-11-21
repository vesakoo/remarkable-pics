import json
from itertools import combinations
from pathlib import Path

from rmdraw.geometry import PAGE_H_MM, PAGE_W_MM
from rmdraw.layout import category_label, grid_layout
from rmdraw.palette import AWS_CATEGORY_COLORS

DATA = Path(__file__).resolve().parent.parent / "data" / "aws_top50.json"
MARGIN = 12.0
GAP = 8.0


def items50():
    return [(e["category"], e["title"]) for e in json.loads(DATA.read_text())]


def boxes(cell):
    return [b for b in (cell.icon_box, cell.title_box) if b is not None]


def test_layout_never_leaves_page():
    pages = grid_layout(items50())
    for page in pages:
        for cell in page:
            for x, y, w, h in boxes(cell):
                assert w > 0 and h > 0
                assert x >= MARGIN - 1e-9 and y >= MARGIN - 1e-9
                assert x + w <= PAGE_W_MM - MARGIN + 1e-9
                assert y + h <= PAGE_H_MM - MARGIN + 1e-9


def _bbox(cell):
    bs = boxes(cell)
    x0 = min(b[0] for b in bs)
    y0 = min(b[1] for b in bs)
    x1 = max(b[0] + b[2] for b in bs)
    y1 = max(b[1] + b[3] for b in bs)
    return x0, y0, x1, y1


def _sep(a, b):
    """Largest axis separation between two boxes (negative means overlap)."""
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def test_cells_do_not_overlap_and_keep_gap():
    for page in grid_layout(items50()):
        icons = [c for c in page if not c.heading]
        for a, b in combinations(icons, 2):
            # icon squares keep the full gap; title boxes may come within 1 mm
            ia = (a.icon_box[0], a.icon_box[1], a.icon_box[0] + a.icon_box[2],
                  a.icon_box[1] + a.icon_box[3])
            ib = (b.icon_box[0], b.icon_box[1], b.icon_box[0] + b.icon_box[2],
                  b.icon_box[1] + b.icon_box[3])
            assert _sep(ia, ib) >= GAP - 1e-9
            assert _sep(_bbox(a), _bbox(b)) >= 1.0 - 1e-9
        for a, b in combinations(page, 2):
            assert _sep(_bbox(a), _bbox(b)) > 0
        for c in icons:
            # title sits under its icon
            assert c.title_box[1] >= c.icon_box[1] + c.icon_box[3]
            assert abs((c.title_box[0] + c.title_box[2] / 2)
                       - (c.icon_box[0] + c.icon_box[2] / 2)) < 1e-9
            assert abs(c.title_box[2] - (20 + GAP - 1)) < 1e-9


def test_heading_on_category_change():
    items = [("compute", "A"), ("compute", "B"), ("storage", "C"), ("ai_ml", "D")]
    flat = [c for page in grid_layout(items) for c in page]
    kinds = [(c.heading, c.title) for c in flat]
    assert kinds == [(True, "Compute"), (False, "A"), (False, "B"),
                     (True, "Storage"), (False, "C"), (True, "AI / ML"), (False, "D")]
    # the heading row lies above its category's icons
    assert flat[3].title_box[1] + flat[3].title_box[3] <= flat[4].icon_box[1]
    assert flat[0].icon_box is None


def test_heading_never_orphaned_at_page_bottom():
    for page in grid_layout(items50()):
        assert not page[-1].heading


def test_50_items_fit_in_at_most_4_pages():
    pages = grid_layout(items50())
    assert len(pages) <= 4
    titles = [c.title for p in pages for c in p if not c.heading]
    assert titles == [t for _, t in items50()]


def test_category_label():
    assert category_label("ai_ml") == "AI / ML"
    assert category_label("networking") == "Networking"


def test_aws_top50_json_valid():
    entries = json.loads(DATA.read_text())
    assert len(entries) == 50
    assert all(set(e) == {"title", "category", "match"} for e in entries)
    assert all(e["category"] in AWS_CATEGORY_COLORS for e in entries)
    assert all(e["title"].strip() and e["match"].strip() for e in entries)
    assert len({e["title"] for e in entries}) == 50
    assert len({e["match"].lower() for e in entries}) == 50
    # grouped: each category forms one contiguous run
    cats = [e["category"] for e in entries]
    runs = [c for i, c in enumerate(cats) if i == 0 or cats[i - 1] != c]
    assert len(runs) == len(set(runs))


def test_category_kept_on_one_page_when_it_fits():
    pages = grid_layout(items50())
    seen = {}
    for n, page in enumerate(pages):
        for c in page:
            seen.setdefault(c.category, set()).add(n)
    assert all(len(v) == 1 for v in seen.values()), seen
    # every non-first page starts with a heading
    assert all(p[0].heading for p in pages)
