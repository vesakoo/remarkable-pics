"""Build out/fox-v2.rmdoc: page 1 the fox (contour fill), page 2 fill swatches to pick
the stripe-free spacing/overlap and the strongest orange on the device."""
from pathlib import Path

from rmdraw.fill import shapes_to_strokes
from rmdraw.model import Page
from rmdraw.preview import render_rmdoc_svg
from rmdraw.rmdoc import write_rmdoc
from rmdraw.shapes_json import load
from rmdraw.svgimport import FilledShape
from rmdraw.text import text_strokes

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
ORANGE = (232, 116, 12)


def rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def swatch(x, y, rgb, label, **kw):
    st = shapes_to_strokes([FilledShape([rect(x, y, 48, 26)], rgb, None)], outlines=False,
                           budget=1000, **kw)
    return st + text_strokes(label, x, y + 31, 3.0, align="left")


def swatch_page() -> Page:
    st = text_strokes("FILL SWATCHES - WHICH IS SMOOTHEST?", 10, 14, 4.0, align="left")
    ys = (24, 64, 104)
    for r, spacing in enumerate((1.2, 2.0, 3.0)):
        for c, overlap in enumerate((1.0, 1.25, 1.6)):
            n = r * 3 + c + 1
            st += swatch(10 + c * 56, ys[r], ORANGE, f"{n}: S{spacing} O{overlap}",
                         spacing_mm=spacing, overlap=overlap)
    st += text_strokes("ORANGES (DEFAULT FILL)", 10, 152, 4.0, align="left")
    for c, (name, rgb) in enumerate((("A E8740C", (232, 116, 12)), ("B FF5A00", (255, 90, 0)),
                                     ("C FF3C00", (255, 60, 0)))):
        st += swatch(10 + c * 56, 160, rgb, name)
    return Page(st)


def main():
    OUT.mkdir(exist_ok=True)
    doc = load(ROOT / "examples" / "fox.json")
    doc.pages.append(swatch_page())
    path = OUT / "fox-v2.rmdoc"
    uuid = write_rmdoc(doc, path)
    for i in range(len(doc.pages)):
        (OUT / f"fox-v2-p{i + 1}.svg").write_text(render_rmdoc_svg(path, i))
    print(uuid)


if __name__ == "__main__":
    main()
