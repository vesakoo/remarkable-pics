"""Plain data model: points are in mm from the page's top-left."""

from dataclasses import dataclass, field


@dataclass
class Stroke:
    points: list[tuple[float, float]]
    pen: str = "fineliner"
    color: str = "black"
    width_mm: float = 0.3
    rgba: tuple[int, int, int, int] | None = None


@dataclass
class Page:
    strokes: list[Stroke] = field(default_factory=list)


@dataclass
class Document:
    name: str
    pages: list[Page] = field(default_factory=list)
