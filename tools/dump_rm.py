"""Dump the strokes of a reMarkable v6 .rm file (thin wrapper around rmdraw.dump)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rmdraw.dump import dump, format_stroke  # noqa: E402,F401


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/dump_rm.py <file.rm>   (same as: rmdraw dump <file.rm>)",
              file=sys.stderr)
        return 2
    for s in dump(Path(argv[1])):
        print(format_stroke(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
