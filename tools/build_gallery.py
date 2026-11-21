"""Rebuild the published gallery under out/ from the examples.

    .venv/bin/python tools/build_gallery.py [--skip-aws]

Layout (committed to git; loose files directly in out/ stay git-ignored scratch):

    out/drawings/<name>/<name>.rmdoc   + <name>.png (preview)
    out/aws-icons/aws-icons-top50.rmdoc + aws-icons-top50-pN.png
    out/calibration/*.rmdoc            + page PNGs
    out/*/tablet/*.png                 device thumbnails (copied in by hand, not rebuilt)

The AWS sheet needs the AWS Architecture Icons package under vendor/aws-icons/.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

from rmdraw.model import Document  # noqa: E402
from rmdraw.preview import render_rmdoc_svg  # noqa: E402
from rmdraw.rmdoc import write_rmdoc  # noqa: E402
from rmdraw.shapes_json import load  # noqa: E402

OUT = ROOT / "out"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DRAWINGS = ("owl", "fox", "smiley", "tree")


def png(rmdoc: Path, page: int, dest: Path, scale: float = 1.5) -> None:
    """Render one page of the written .rmdoc to PNG via headless Chrome."""
    with tempfile.TemporaryDirectory() as tmp:
        svg = Path(tmp) / "page.svg"
        svg.write_text(render_rmdoc_svg(rmdoc, page))
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=680,906", f"--force-device-scale-factor={scale}",
                        f"--screenshot={dest}", svg.as_uri()],
                       check=False, capture_output=True)
    if not dest.exists():
        raise RuntimeError(f"Chrome did not write {dest}")


def publish(doc: Document, folder: Path, stem: str) -> Path:
    """Write <stem>.rmdoc plus <stem>.png (one page) or <stem>-pN.png (several)."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stem}.rmdoc"
    write_rmdoc(doc, path)
    n = len(doc.pages)
    for i in range(n):
        png(path, i, folder / (f"{stem}.png" if n == 1 else f"{stem}-p{i + 1}.png"))
    print(f"{path.relative_to(ROOT)}: {len(doc.pages)} page(s), "
          f"{sum(len(p.strokes) for p in doc.pages)} strokes")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-aws", action="store_true")
    a = ap.parse_args()

    for name in DRAWINGS:
        publish(load(ROOT / "examples" / f"{name}.json"), OUT / "drawings" / name, name)

    if not a.skip_aws:
        import aws_icons
        if not aws_icons.VENDOR.exists():
            sys.exit(f"missing {aws_icons.VENDOR}; download the AWS icon package or use --skip-aws")
        doc, _ = aws_icons.build()
        publish(doc, OUT / "aws-icons", "aws-icons-top50")
        import aws_architecture
        publish(aws_architecture.build(), OUT / "drawings" / "aws-architecture",
                "aws-architecture")

    import calibration
    import fox_v2
    p2, _ = calibration.page2()
    publish(Document("RM-CALIBRATION", [calibration.page1(), p2]),
            OUT / "calibration", "pens-and-fills")
    publish(Document("Fill swatches", [fox_v2.swatch_page()]),
            OUT / "calibration", "fill-swatches")


if __name__ == "__main__":
    main()
