"""Build out/calibration.rmdoc: a two-page calibration notebook for the Paper Pro."""
from pathlib import Path

from rmdraw.fill import shapes_to_strokes
from rmdraw.model import Document, Page, Stroke
from rmdraw.preview import render_rmdoc_svg
from rmdraw.rmdoc import write_rmdoc
from rmdraw.svgimport import FilledShape
from rmdraw.text import text_strokes

OUT = Path(__file__).resolve().parent.parent / "out"
LABEL_H = 2.5
AWS = {"orange": (255, 153, 0), "purple": (140, 79, 255), "pink": (231, 21, 123),
       "green": (122, 161, 22), "blue": (1, 168, 224)}


def label(s, x, y, align="left"):
    return text_strokes(s, x, y, LABEL_H, align=align)


def cross(x, y, r=2.5):
    return [Stroke([(x - r, y), (x + r, y)]), Stroke([(x, y - r), (x, y + r)])]


def rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def rounded(x, y, w, h, r, n=6):
    import math
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts + [pts[0]]


def page1(w=179.0, h=239.0):
    st = []
    for i, (x, y) in enumerate([(5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5), (w / 2, h / 2)], 1):
        st += cross(x, y)
        st += label(str(i), x + 4 if x < w - 20 else x - 8, y + 3)
    # grid 100x100 at (10,10), gray fineliner 0.2
    for k in range(11):
        v = 10 + 10 * k
        st.append(Stroke([(v, 10), (v, 110)], color="gray", width_mm=0.2))
        st.append(Stroke([(10, v), (110, v)], color="gray", width_mm=0.2))
    st += label("GRID 10MM", 112, 12)
    # pens
    y = 125
    for pen in ("fineliner", "ballpoint", "marker", "pencil", "mechanical_pencil",
                "calligraphy", "paintbrush"):
        st += label(pen, 10, y - 1.5)
        st.append(Stroke([(55, y), (100, y), (110, y - 2), (120, y + 1)], pen=pen, width_mm=0.6))
        y += 7
    # AWS shader bands
    y = 180
    st += label("SHADER AWS A170", 10, y - 6)
    for i, (n, rgb) in enumerate(AWS.items()):
        x = 10 + i * 33
        for k in range(4):
            st.append(Stroke([(x, y + k * 2.4), (x + 28, y + k * 2.4)], pen="shader",
                             width_mm=2.5, rgba=(*rgb, 170)))
        st += label(n, x, y + 11)
    y = 210
    st += label("ALPHA 120 170 230", 10, y - 6)
    for i, (n, rgb) in enumerate(list(AWS.items())[:3]):
        for j, a in enumerate((120, 170, 230)):
            x = 10 + i * 55 + j * 17
            for k in range(3):
                st.append(Stroke([(x, y + k * 2.4), (x + 15, y + k * 2.4)], pen="shader",
                                 width_mm=2.5, rgba=(*rgb, a)))
            st += label(str(a), x, y + 9)
    return Page(st)


def icon_shapes(x, y, s=20.0):
    glyph = [rounded(x + 4, y + 4, s - 8, s - 8, 2.0)]
    for i in range(3):
        for j in range(2):
            gx, gy = x + 6.5 + i * 3.1, y + 6.5 + j * 3.4
            glyph.append(rect(gx, gy, 2.0, 2.4))
    return [FilledShape([rect(x, y, s, s)], AWS["orange"], None),
            FilledShape(glyph[:1], (255, 255, 255), (255, 255, 255), stroke_width_mm=0.5),
            *[FilledShape([g], (255, 255, 255), None) for g in glyph[1:]]]


def page2():
    st, counts = [], {}
    for idx, (spacing, inset) in enumerate((sp, ins) for sp in (2.0, 1.2)
                                           for ins in ("half", "quarter", "outer")):
        col, row = idx % 3, idx // 3
        x, y = 15 + col * 55, 30 + row * 55
        strokes = shapes_to_strokes(icon_shapes(x, y), method="shader",
                                    spacing_mm=spacing, inset=inset, budget=400)
        name = f"S{spacing} {inset}"
        counts[name] = len(strokes)
        st += strokes
        st += label(name.upper(), x, y + 23)
    st += label("ICON FILL VARIANTS", 15, 15)
    return Page(st), counts


def main():
    OUT.mkdir(exist_ok=True)
    p2, counts = page2()
    doc = Document("RM-CALIBRATION", [page1(), p2])
    path = OUT / "calibration.rmdoc"
    uuid = write_rmdoc(doc, path)
    for i in (0, 1):
        (OUT / f"calibration-p{i + 1}.svg").write_text(render_rmdoc_svg(path, i))
    for k, v in counts.items():
        print(f"{k}: {v} strokes")
    print(uuid)
    return uuid


if __name__ == "__main__":
    main()
