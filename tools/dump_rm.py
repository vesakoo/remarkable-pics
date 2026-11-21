"""Dump the strokes of a reMarkable v6 .rm file, one line per stroke."""

import sys
from pathlib import Path

import rmdraw  # noqa: F401  (installs the rmscene colour compat)
from rmscene import read_tree
from rmscene.scene_items import Line


def _walk(item):
    if isinstance(item, Line):
        yield item
    children = getattr(item, "children", None)
    if children is not None:
        for child in children.values():
            if child is not None:
                yield from _walk(child)


def dump(path: Path) -> list[dict]:
    with open(path, "rb") as f:
        tree = read_tree(f)
    out = []
    for line in _walk(tree.root):
        xs = [p.x for p in line.points]
        ys = [p.y for p in line.points]
        out.append(
            {
                "tool": line.tool.name,
                "color": line.color.name,
                "rgba": line.color_rgba,
                "thickness_scale": line.thickness_scale,
                "n_points": len(line.points),
                "bbox": (min(xs), min(ys), max(xs), max(ys)) if xs else None,
            }
        )
    return out


def main(argv: list[str]) -> int:
    for s in dump(Path(argv[1])):
        print(
            f"tool={s['tool']} color={s['color']} rgba={s['rgba']} "
            f"thick={s['thickness_scale']} n={s['n_points']} bbox={s['bbox']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
