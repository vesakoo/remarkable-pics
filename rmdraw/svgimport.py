"""SVG import: turn vector art into flattened geometric shapes in mm."""
from __future__ import annotations

import math
import re
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from svgelements import SVG, Close, Color, Move, Path as SvgPath, Shape

Point = tuple[float, float]


@dataclass
class FilledShape:
    outline: list[list[Point]]
    fill_rgb: tuple[int, int, int] | None
    stroke_rgb: tuple[int, int, int] | None
    fill_rule: str = "nonzero"
    stroke_width_mm: float = 0.0


def _rgb(c) -> tuple[int, int, int] | None:
    if c is None or c.value is None:
        return None
    return (int(c.red), int(c.green), int(c.blue))


def _gradient_stops(root) -> dict:
    """Map gradient id -> (first stop colour string or None, href id or None)."""
    out = {}
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("linearGradient", "radialGradient") or not el.get("id"):
            continue
        first = None
        for st in el:
            if st.tag.rsplit("}", 1)[-1] != "stop":
                continue
            first = st.get("stop-color")
            for decl in (st.get("style") or "").split(";"):
                if decl.strip().startswith("stop-color"):
                    first = decl.split(":", 1)[1].strip()
            if first is None:
                first = "black"
            break
        href = el.get("href") or el.get("{http://www.w3.org/1999/xlink}href")
        out[el.get("id")] = (first, href.lstrip("#") if href else None)
    return out


def _resolve_paint(grads, elem, attr: str):
    """Return RGB for fill/stroke, resolving url(#id) to the first gradient stop."""
    raw = elem.values.get(attr) if isinstance(elem.values, dict) else None
    if isinstance(raw, str) and raw.strip().startswith("url("):
        head, _, tail = raw.strip()[4:].partition(")")
        ref = head.strip("'\" ").lstrip("#")
        tail = tail.strip()
        for _ in range(8):
            first, href = grads.get(ref, (None, None))
            if first is not None:
                return _rgb(Color(first))
            if not href:
                break
            ref = href
        if tail and tail != "none":
            try:
                return _rgb(Color(tail))
            except Exception:
                return None
        return None
    return _rgb(getattr(elem, attr))


def _n_points(length_mm: float, tol: float) -> int:
    # conservative: treat the segment as an arc of radius ~ length/2
    step = 2.0 * math.sqrt(max(length_mm, tol) * tol)
    return max(2, math.ceil(length_mm / step))


def _flatten(path: SvgPath, scale: float, ox: float, oy: float, tol: float):
    rings: list[list[Point]] = []
    cur: list[Point] = []
    start: Point | None = None

    def add(p):
        q = (ox + p[0] * scale, oy + p[1] * scale)
        if not cur or q != cur[-1]:
            cur.append(q)

    for seg in path.segments():
        if isinstance(seg, Move):
            if len(cur) > 1:
                rings.append(cur)
            cur = []
            start = (seg.end.x, seg.end.y)
            add(start)
        elif isinstance(seg, Close):
            if start is not None and cur:
                add(start)
            if len(cur) > 1:
                rings.append(cur)
            cur = []
            if start is not None:
                # a following drawing command continues from the start point
                cur = []
                pending = start
                cur.append((ox + pending[0] * scale, oy + pending[1] * scale))
        else:
            if seg.start is not None and not cur:
                add((seg.start.x, seg.start.y))
            if type(seg).__name__ == "Line":
                add((seg.end.x, seg.end.y))
            else:
                length = seg.length(error=1e-4) * scale
                n = _n_points(length, tol)
                for i in range(1, n + 1):
                    p = seg.npoint([i / n])[0]
                    add((float(p[0]), float(p[1])))
    if len(cur) > 1:
        rings.append(cur)
    return rings


def _hidden(e) -> bool:
    v = e.values if isinstance(getattr(e, "values", None), dict) else {}
    if str(v.get("display", "")).strip() == "none":
        return True
    return str(v.get("visibility", "")).strip() in ("hidden", "collapse")


def svg_to_shapes(path: Path, box: tuple[float, float, float, float],
                  tolerance_mm: float = 0.15) -> list[FilledShape]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if "<!ENTITY" in text or re.search(r"<!DOCTYPE[^>\[]*\[", text, re.I):
        raise ValueError("SVG with entity declarations or DOCTYPE internal subset rejected")
    svg = SVG.parse(str(path), reify=True)
    grads = _gradient_stops(ET.parse(str(path)).getroot())
    # reify already maps the viewBox into the width/height space
    vx, vy, vw, vh = 0.0, 0.0, float(svg.width), float(svg.height)
    bx, by, bw, bh = box
    scale = min(bw / vw, bh / vh)
    ox = bx + (bw - vw * scale) / 2 - vx * scale
    oy = by + (bh - vh * scale) / 2 - vy * scale

    warned: set[str] = set()
    out: list[FilledShape] = []

    def check_ignored(e):
        v = e.values if isinstance(getattr(e, "values", None), dict) else {}
        for kind in ("clip-path", "mask", "filter"):
            if v.get(kind) not in (None, "", "none") and kind not in warned:
                warned.add(kind)
                warnings.warn(f"svg {kind} is not supported and was ignored",
                              UserWarning, stacklevel=3)

    for e in svg.elements():
        if not isinstance(e, Shape) or _hidden(e):
            continue
        check_ignored(e)
        fill = _resolve_paint(grads, e, "fill")
        stroke = _resolve_paint(grads, e, "stroke")
        if fill is None and stroke is None:
            continue
        p = SvgPath(e)
        p.reify()
        rings = _flatten(p, scale, ox, oy, tolerance_mm)
        if not rings:
            continue
        sw = e.stroke_width if (stroke is not None and e.stroke_width) else 0.0
        out.append(FilledShape(
            outline=rings, fill_rgb=fill, stroke_rgb=stroke,
            fill_rule="evenodd" if e.values.get("fill-rule") == "evenodd" else "nonzero",
            stroke_width_mm=float(sw) * scale))
    return out
