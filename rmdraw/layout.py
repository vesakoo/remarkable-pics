"""Grid layout for icon sheets: icon square with a title box under it, category headings."""
from __future__ import annotations

from dataclasses import dataclass

from .geometry import PAGE_H_MM, PAGE_W_MM

Box = tuple[float, float, float, float]  # x, y, w, h in mm

TITLE_LINES = 2
LINE_PITCH = 1.5  # text_strokes puts lines 1.5 x height apart
TITLE_PAD_MM = 1.5  # icon bottom to title top
HEADING_H_MM = 3.5
HEADING_PAD_MM = 3.0  # heading bottom to first icon row


@dataclass
class Cell:
    category: str
    title: str
    icon_box: Box | None
    title_box: Box
    heading: bool = False


def category_label(category: str) -> str:
    if category == "ai_ml":
        return "AI / ML"
    return category.replace("_", " ").title()


def title_box_height(title_h_mm: float) -> float:
    return title_h_mm * (1 + LINE_PITCH * (TITLE_LINES - 1)) + title_h_mm * 0.5


def grid_layout(items: list[tuple[str, str]], cell_mm: float = 20, title_h_mm: float = 2.5,
                cols: int = 4, gap_mm: float = 8, margin_mm: float = 12) -> list[list[Cell]]:
    """Lay out (category, title) items in rows of `cols`, grouped per page.

    The title box is cell + gap - 1 mm wide, centred under the icon, so adjacent titles
    stay 1 mm apart. A heading row starts each new category; a heading is never left
    alone at the bottom of a page. A category that fits on an empty page is never split
    across pages; a longer one breaks row by row.
    """
    title_w = cell_mm + gap_mm - 1
    title_bh = title_box_height(title_h_mm)
    row_h = cell_mm + TITLE_PAD_MM + title_bh
    side = (title_w - cell_mm) / 2
    grid_w = cols * cell_mm + (cols - 1) * gap_mm + 2 * side
    avail_w = PAGE_W_MM - 2 * margin_mm
    if grid_w > avail_w:
        raise ValueError(f"grid {grid_w:.1f} mm wider than page {avail_w:.1f} mm")
    left = margin_mm + (avail_w - grid_w) / 2 + side
    bottom = PAGE_H_MM - margin_mm
    heading_h = HEADING_H_MM + HEADING_PAD_MM

    # group into rows: each row is one category
    rows: list[tuple[str, list[str], bool]] = []
    for cat, title in items:
        if not rows or rows[-1][0] != cat:
            rows.append((cat, [title], True))
        elif len(rows[-1][1]) == cols:
            rows.append((cat, [title], False))
        else:
            rows[-1][1].append(title)

    # height of each category's whole block (heading + its rows), indexed by start row
    block: dict[int, float] = {}
    for i, (_, _, starts) in enumerate(rows):
        if starts:
            n = 1
            while i + n < len(rows) and not rows[i + n][2]:
                n += 1
            block[i] = heading_h + n * row_h + (n - 1) * gap_mm
    fresh = bottom - margin_mm

    pages: list[list[Cell]] = [[]]
    y = margin_mm
    for i, (cat, titles, starts) in enumerate(rows):
        need = row_h + (heading_h if starts else 0)
        if starts and block[i] <= fresh + 1e-9:
            need = block[i]  # keep a category on one page when a fresh page can hold it
        if pages[-1] and y + need > bottom + 1e-9:
            pages.append([])
            y = margin_mm
        if y + need > bottom + 1e-9:
            raise ValueError("a row does not fit on an empty page")
        if starts:
            pages[-1].append(Cell(cat, category_label(cat), None,
                                  (left - side, y, grid_w, HEADING_H_MM), heading=True))
            y += heading_h
        for i, title in enumerate(titles):
            x = left + i * (cell_mm + gap_mm)
            pages[-1].append(Cell(cat, title, (x, y, cell_mm, cell_mm),
                                  (x - side, y + cell_mm + TITLE_PAD_MM, title_w, title_bh)))
        y += row_h + gap_mm
    return pages
