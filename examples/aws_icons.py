"""Build out/aws-top50.rmdoc: the 50 most-used AWS service icons, each with its title.

Needs the AWS Architecture Icons package unzipped under vendor/aws-icons/ (git-ignored):
https://aws.amazon.com/architecture/icons/ -> Icon package zip. The SVGs are parsed as
data only.
"""
import json
import sys
from pathlib import Path

from rmdraw.fill import shapes_to_strokes
from rmdraw.layout import HEADING_H_MM, grid_layout
from rmdraw.model import Document, Page
from rmdraw.preview import render_rmdoc_svg
from rmdraw.rmdoc import write_rmdoc
from rmdraw.svgimport import svg_to_shapes
from rmdraw.text import text_strokes

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
DATA = ROOT / "data" / "aws_top50.json"
VENDOR = ROOT / "vendor" / "aws-icons"
NAME = "AWS Icons – Top 50 (v2)"
TITLE_H = 2.5
BUDGET = 150
TOLERANCES = (0.15, 0.25, 0.4, 0.6)


def find_icon(match: str) -> Path:
    hits = [p for p in VENDOR.glob("Architecture-Service-Icons*/*/48/*.svg")
            if match.lower() in p.name.lower()]
    if len(hits) != 1:
        raise LookupError(f"match {match!r} hit {len(hits)} 48 px icons: {hits}")
    return hits[0]


def icon_strokes(path: Path, box):
    """Strokes for one icon; raise the curve tolerance if it is over budget."""
    for tol in TOLERANCES:
        shapes = svg_to_shapes(path, box, tolerance_mm=tol)
        try:
            # category=None on purpose: the 2026 AWS icon colours differ from the guessed
            # AWS_CATEGORY_COLORS (Database fills are magenta-purple, Networking purple), so
            # forcing the category pen gave outlines that clash with the fill. Without a
            # category each outline uses the palette colour nearest to its actual fill.
            return shapes_to_strokes(shapes, category=None, budget=BUDGET), tol
        except ValueError:
            continue
    raise ValueError(f"{path.name} exceeds {BUDGET} strokes at every tolerance")


def _inside(strokes, box, slack=0.3):
    x, y, w, h = box
    return all(x - slack <= px <= x + w + slack and y - slack <= py <= y + h + slack
               for s in strokes for px, py in s.points)


def build():
    entries = json.loads(DATA.read_text())
    pages = grid_layout([(e["category"], e["title"]) for e in entries], title_h_mm=TITLE_H)
    by_title = {e["title"]: e for e in entries}
    doc_pages, rows = [], []
    for n, cells in enumerate(pages, 1):
        st = []
        for c in cells:
            if c.heading:
                x, y, _, _ = c.title_box
                st += text_strokes(c.title, x, y, HEADING_H_MM, align="left")
                continue
            e = by_title[c.title]
            icon, tol = icon_strokes(find_icon(e["match"]), c.icon_box)
            tx, ty, tw, _ = c.title_box
            title = text_strokes(c.title, tx + tw / 2, ty, TITLE_H, max_width_mm=tw)
            if not _inside(title, c.title_box):
                raise ValueError(f"title {c.title!r} overflows its box")
            if not _inside(icon, c.icon_box):
                raise ValueError(f"icon {c.title!r} overflows its box")
            rows.append((n, c.title, len(icon), len(title), tol))
            st += icon + title
        doc_pages.append(Page(st))
    return Document(NAME, doc_pages), rows


def main():
    if not VENDOR.exists():
        sys.exit(f"missing {VENDOR}; download the AWS Architecture Icons package first")
    OUT.mkdir(exist_ok=True)
    doc, rows = build()
    path = OUT / "aws-top50.rmdoc"
    uuid = write_rmdoc(doc, path)
    for i in range(len(doc.pages)):
        (OUT / f"aws-top50-p{i + 1}.svg").write_text(render_rmdoc_svg(path, i))
    print(f"{'page':>4}  {'service':<28} {'icon':>4} {'title':>5} {'total':>5}  tol")
    for n, title, ni, nt, tol in rows:
        print(f"{n:>4}  {title:<28} {ni:>4} {nt:>5} {ni + nt:>5}  {tol}")
    icons = [r[2] for r in rows]
    print(f"icons {len(rows)}, pages {len(doc.pages)}, icon strokes max {max(icons)} "
          f"mean {sum(icons) / len(icons):.1f}, total strokes "
          f"{sum(len(p.strokes) for p in doc.pages)}")
    print(uuid)
    return uuid


if __name__ == "__main__":
    main()
