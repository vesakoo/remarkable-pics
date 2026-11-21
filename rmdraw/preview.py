"""SVG preview of rmdoc pages, rendered from what the .rm file contains."""

import io
import json
import statistics
import zipfile
from pathlib import Path

import rmdraw  # noqa: F401  (installs the extended PenColor)
from rmscene import read_tree
from rmscene.scene_items import Line, Pen, PenColor

from .geometry import PAGE_H_MM, PAGE_W_MM, UNITS_PER_MM, units_to_mm

_HEX = {
    PenColor.BLACK: "#000000",
    PenColor.GRAY: "#8c8c8c",
    PenColor.WHITE: "#ffffff",
    PenColor.BLUE: "#2f5fd0",
    PenColor.RED: "#d23a2c",
    PenColor.GREEN: "#2f9447",
    PenColor.GREEN_2: "#2f9447",
    PenColor.YELLOW: "#e9b915",
    PenColor.YELLOW_2: "#e9b915",
    PenColor.CYAN: "#19aac2",
    PenColor.MAGENTA: "#c0399f",
    PenColor.PINK: "#f59ac8",
    PenColor.HIGHLIGHT_BLUE: "#9fd8f5",
    PenColor.HIGHLIGHT_ORANGE: "#ffb066",
    PenColor.HIGHLIGHT_GRAY: "#bdbdbd",
    PenColor.GRAY_OVERLAP: "#8c8c8c",
}
_TRANSLUCENT = {Pen.HIGHLIGHTER_1, Pen.HIGHLIGHTER_2, Pen.SHADER}


def _walk(item):
    if isinstance(item, Line):
        yield item
    children = getattr(item, "children", None)
    if children is not None:
        for child in children.values():
            if child is not None:
                yield from _walk(child)


def _style(line: Line) -> tuple[str, float | None]:
    rgba = line.color_rgba
    if rgba:
        r, g, b, a = rgba
        return f"rgb({r},{g},{b})", a / 255
    colour = _HEX.get(line.color, "#ff00ff")
    return colour, (0.35 if line.tool in _TRANSLUCENT else None)


def render_rm_svg(rm_bytes: bytes) -> str:
    tree = read_tree(io.BytesIO(rm_bytes))
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{PAGE_W_MM:.3f}mm" height="{PAGE_H_MM:.3f}mm" '
        f'viewBox="0 0 {PAGE_W_MM:.3f} {PAGE_H_MM:.3f}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    for line in _walk(tree.root):
        if not line.points:
            continue
        pts = " ".join(
            "%.3f,%.3f" % units_to_mm(p.x, p.y) for p in line.points
        )
        width = statistics.median(p.width for p in line.points) / 4 / UNITS_PER_MM
        width = max(0.1, width * (line.thickness_scale / 2.0))
        colour, opacity = _style(line)
        op = f' stroke-opacity="{opacity:.3f}"' if opacity is not None else ""
        out.append(
            f'<polyline points="{pts}" fill="none" stroke="{colour}"{op} '
            f'stroke-width="{width:.3f}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
        )
    out.append("</svg>")
    return "\n".join(out)


def render_rmdoc_svg(path: Path, page_index: int = 0) -> str:
    with zipfile.ZipFile(path) as z:
        content = next(n for n in z.namelist() if n.endswith(".content"))
        uid = content[: -len(".content")]
        pages = json.loads(z.read(content))["cPages"]["pages"]
        if not 0 <= page_index < len(pages):
            raise IndexError(f"page_index {page_index} out of range ({len(pages)} pages)")
        return render_rm_svg(z.read(f"{uid}/{pages[page_index]['id']}.rm"))
