"""Map arbitrary RGB to the device's pen palette (pens ignore rgba) and to shader rgba."""
from __future__ import annotations

# Alpha used for shader fills (the shader honours arbitrary RGBA on the device).
FILL_ALPHA = 170

# Reference RGBs for the palette colours that pens can render. White is never chosen.
PALETTE_RGB: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "gray": (140, 140, 140),
    "blue": (47, 95, 208),
    "red": (210, 58, 44),
    "green": (47, 148, 71),
    "yellow": (233, 185, 21),
    "cyan": (25, 170, 194),
    "magenta": (192, 57, 159),
}

AWS_CATEGORY_COLORS: dict[str, str] = {
    "compute": "yellow",
    "storage": "green",
    "database": "blue",
    "networking": "magenta",
    "integration": "red",
    "security": "red",
    "analytics": "cyan",
    "management": "gray",
    "ai_ml": "cyan",
}


def nearest_palette(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return min(
        PALETTE_RGB,
        key=lambda n: (PALETTE_RGB[n][0] - r) ** 2
        + (PALETTE_RGB[n][1] - g) ** 2
        + (PALETTE_RGB[n][2] - b) ** 2,
    )


def to_pen_color(
    rgb: tuple[int, int, int], category: str | None = None
) -> tuple[str, tuple[int, int, int, int]]:
    """Return (palette name for pens, exact rgba for the shader)."""
    name = AWS_CATEGORY_COLORS[category] if category is not None else nearest_palette(rgb)
    r, g, b = (int(c) for c in rgb[:3])
    return name, (r, g, b, FILL_ALPHA)
