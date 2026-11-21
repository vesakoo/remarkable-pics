"""rmdraw command line: build, svg, preview, dump, push, thumbs."""
from __future__ import annotations

import argparse
import re
import sys
import warnings
from pathlib import Path

from . import device, shapes_json
from .dump import dump, format_stroke
from .geometry import PAGE_H_MM, PAGE_W_MM
from .model import Document, Page
from .preview import render_rmdoc_svg
from .rmdoc import write_rmdoc

MARGIN_MM = 10.0
DEFAULT_BOX = (MARGIN_MM, MARGIN_MM, PAGE_W_MM - 2 * MARGIN_MM, PAGE_H_MM - 2 * MARGIN_MM)


class CliError(Exception):
    pass


def _box(s: str) -> tuple[float, float, float, float]:
    try:
        x, y, w, h = (float(v) for v in s.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"--box must be x,y,w,h in mm, got {s!r}") from None
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("--box width and height must be > 0")
    if x < 0 or y < 0 or x + w > PAGE_W_MM or y + h > PAGE_H_MM:
        raise argparse.ArgumentTypeError(
            f"--box {s} leaves the page (0..{PAGE_W_MM:.1f} x 0..{PAGE_H_MM:.1f} mm)")
    return x, y, w, h


def _write(doc: Document, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    try:
        write_rmdoc(doc, tmp)
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)
    n = sum(len(p.strokes) for p in doc.pages)
    print(f"wrote {out} ({len(doc.pages)} page(s), {n} strokes)")


def _host(s: str) -> str:
    try:
        return device.check_host(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _uuid(s: str) -> str:
    if not re.fullmatch(device.UUID_RE, s):
        raise argparse.ArgumentTypeError(f"invalid document uuid {s!r}")
    return s


def _wait(s: str) -> float:
    try:
        v = float(s)
    except ValueError:
        v = -1.0
    if not 0 <= v <= 600:
        raise argparse.ArgumentTypeError(f"--wait must be 0..600 seconds, got {s!r}")
    return v


def _need_file(p: Path) -> Path:
    if not p.is_file():
        raise CliError(f"no such file: {p}")
    return p


def cmd_build(a) -> int:
    doc = shapes_json.load(_need_file(Path(a.shapes)))
    _write(doc, Path(a.output))
    return 0


def cmd_svg(a) -> int:
    src = _need_file(Path(a.svg))
    if a.budget < 1:
        raise CliError("--budget must be at least 1")
    if a.budget > shapes_json.ITEM_BUDGET:
        print(f"rmdraw: warning: --budget {a.budget} is above {shapes_json.ITEM_BUDGET} "
              "strokes per object; the tablet may get sluggish", file=sys.stderr)
    strokes = shapes_json.svg_strokes(src, a.box, a.fill, budget=a.budget)
    if not strokes:
        raise CliError(f"{src}: no visible shapes found")
    _write(Document(a.name or src.stem, [Page(strokes)]), Path(a.output))
    return 0


def cmd_preview(a) -> int:
    src = _need_file(Path(a.rmdoc))
    if a.page < 1:
        raise CliError("--page counts from 1")
    try:
        svg = render_rmdoc_svg(src, a.page - 1)
    except IndexError:
        raise CliError(f"--page {a.page}: {src} has fewer pages") from None
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def cmd_dump(a) -> int:
    for s in dump(_need_file(Path(a.rm))):
        print(format_stroke(s))
    return 0


def _no_thumbs(uuid: str) -> str:
    return (f"no thumbnail yet for {uuid}: ask the user to open the notebook on the tablet, "
            f"then retry: rmdraw thumbs {uuid} -o DIR --wait 60")


def cmd_push(a) -> int:
    uuid = device.install_rmdoc(_need_file(Path(a.rmdoc)), host=a.host)
    print(f"installed {uuid}", flush=True)
    if a.wait is not None and not a.thumbs:
        print("rmdraw: note: --wait has no effect without --thumbs DIR", file=sys.stderr)
    if a.thumbs:
        wait = a.wait if a.wait is not None else 10.0
        pngs = device.fetch_thumbnails(uuid, Path(a.thumbs), host=a.host, wait_s=wait)
        if not pngs:
            print(f"rmdraw: warning: {_no_thumbs(uuid)}", file=sys.stderr)
        for png in pngs:
            print(png)
    return 0


def cmd_thumbs(a) -> int:
    pngs = device.fetch_thumbnails(a.uuid, Path(a.output), host=a.host, wait_s=a.wait)
    if not pngs:
        raise CliError(_no_thumbs(a.uuid))
    for png in pngs:
        print(png)
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rmdraw", description="Native reMarkable notebooks "
                                "made of pen strokes.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="shapes JSON -> .rmdoc")
    b.add_argument("shapes")
    b.add_argument("-o", "--output", required=True)
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("svg", help="SVG file -> .rmdoc (one page)")
    s.add_argument("svg")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--box", type=_box, default=DEFAULT_BOX,
                   help="x,y,w,h in mm (default: the page minus 10 mm margins)")
    s.add_argument("--fill", choices=("shader", "marker", "hatch", "none"), default="shader")
    s.add_argument("--name", help="notebook title (default: the file name)")
    s.add_argument("--budget", type=int, default=shapes_json.ITEM_BUDGET,
                   help="max strokes for the whole SVG (default 150; above warns)")
    s.set_defaults(func=cmd_svg)

    v = sub.add_parser("preview", help=".rmdoc page -> SVG preview")
    v.add_argument("rmdoc")
    v.add_argument("-o", "--output", required=True)
    v.add_argument("--page", type=int, default=1, help="page number, from 1 (default 1)")
    v.set_defaults(func=cmd_preview)

    d = sub.add_parser("dump", help="list the strokes of a .rm page")
    d.add_argument("rm")
    d.set_defaults(func=cmd_dump)

    u = sub.add_parser("push", help="add an .rmdoc to the tablet over SSH (never deletes)")
    u.add_argument("rmdoc")
    u.add_argument("--thumbs", metavar="DIR", help="fetch the device thumbnails into DIR")
    u.add_argument("--wait", type=_wait, default=None, metavar="S",
                   help="with --thumbs: seconds to wait for thumbnails (default 10)")
    u.add_argument("--host", type=_host, default="root@10.11.99.1")
    u.set_defaults(func=cmd_push)

    t = sub.add_parser("thumbs", help="fetch the device thumbnails of a pushed notebook")
    t.add_argument("uuid", type=_uuid)
    t.add_argument("-o", "--output", required=True, metavar="DIR")
    t.add_argument("--wait", type=_wait, default=10.0, metavar="S",
                   help="seconds to wait for thumbnails (default 10)")
    t.add_argument("--host", type=_host, default="root@10.11.99.1")
    t.set_defaults(func=cmd_thumbs)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as e:  # argparse already printed usage and the error
        return int(e.code or 0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("always", UserWarning)
            warnings.showwarning = lambda m, *_a, **_k: print(f"rmdraw: warning: {m}",
                                                              file=sys.stderr)
            return args.func(args)
    except KeyboardInterrupt:
        print("rmdraw: interrupted", file=sys.stderr)
        return 130
    except Exception as e:  # one clean line, no traceback
        msg = " ".join(str(e).split()) or type(e).__name__
        print(f"rmdraw: error: {msg}", file=sys.stderr)
        return 1
