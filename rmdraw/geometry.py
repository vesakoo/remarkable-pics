"""Paper Pro page geometry and pen/colour tables (see docs/format-notes.md)."""

import rmdraw  # noqa: F401  (installs the extended PenColor)
from rmscene.scene_items import Pen, PenColor

# format-notes.md "Page geometry": units are screen pixels at 229 PPI.
UNITS_PER_MM = 229 / 25.4
# format-notes.md: SceneInfo.paper_size = (1620, 2160).
PAGE_W_UNITS = 1620
PAGE_H_UNITS = 2160
PAGE_W_MM = PAGE_W_UNITS / UNITS_PER_MM
PAGE_H_MM = PAGE_H_UNITS / UNITS_PER_MM


def units_per_mm() -> float:
    return UNITS_PER_MM


def mm_to_units(x_mm: float, y_mm: float) -> tuple[float, float]:
    # format-notes.md: x is centred (0 at the middle), y starts at the top.
    return (x_mm - PAGE_W_MM / 2) * UNITS_PER_MM, y_mm * UNITS_PER_MM


def units_to_mm(x: float, y: float) -> tuple[float, float]:
    return x / UNITS_PER_MM + PAGE_W_MM / 2, y / UNITS_PER_MM


def width_to_device(pen: str, width_mm: float) -> tuple[float, int]:
    # format-notes.md "Pens": size 2 -> thickness_scale 2.0; point.width ~ 4 x stroke px.
    width = round(width_mm * UNITS_PER_MM * 4)
    return 2.0, max(1, min(65535, width))


PEN_NAMES = {
    "fineliner": Pen.FINELINER_2,
    "ballpoint": Pen.BALLPOINT_2,
    "marker": Pen.MARKER_2,
    "pencil": Pen.PENCIL_2,
    "mechanical_pencil": Pen.MECHANICAL_PENCIL_2,
    "highlighter": Pen.HIGHLIGHTER_2,
    "shader": Pen.SHADER,
    "calligraphy": Pen.CALIGRAPHY,
    "paintbrush": Pen.PAINTBRUSH_2,
}

# format-notes.md "Colours": the device writes GREEN_2/YELLOW_2 for pens;
# highlighter colours are 3, 14, 5, 15, 4, 16.
COLOR_NAMES = {
    "black": PenColor.BLACK,
    "gray": PenColor.GRAY,
    "white": PenColor.WHITE,
    "blue": PenColor.BLUE,
    "red": PenColor.RED,
    "green": PenColor.GREEN_2,
    "yellow": PenColor.YELLOW_2,
    "cyan": PenColor.CYAN,
    "magenta": PenColor.MAGENTA,
    "pink": PenColor.PINK,
    "hl_yellow": PenColor.YELLOW,
    "hl_blue": PenColor.HIGHLIGHT_BLUE,
    "hl_pink": PenColor.PINK,
    "hl_orange": PenColor.HIGHLIGHT_ORANGE,
    "hl_green": PenColor.GREEN,
    "hl_gray": PenColor.HIGHLIGHT_GRAY,
}
