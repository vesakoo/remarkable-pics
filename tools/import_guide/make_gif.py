"""Render the "import without developer mode" animation to docs/media/import-desktop-app.gif.

Each frame is anim.html?t=<seconds>, screenshotted by headless Chrome; Pillow joins them.
Needs Google Chrome and Pillow (not a project dependency):

    python -m venv /tmp/gifenv && /tmp/gifenv/bin/pip install pillow
    /tmp/gifenv/bin/python tools/import_guide/make_gif.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs" / "media" / "import-desktop-app.gif"
FPS, DURATION, SCALE = 10, 10.0, 0.75  # output 720x405


def shot(t: float, path: Path) -> Path:
    url = f"file://{HERE / 'anim.html'}?t={t:.2f}"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--allow-file-access-from-files", "--window-size=960,540",
                    f"--screenshot={path}", url],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def main() -> None:
    n = int(FPS * DURATION)
    with tempfile.TemporaryDirectory() as tmp:
        paths = [Path(tmp) / f"f{i:03d}.png" for i in range(n)]
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(lambda i: shot(i / FPS, paths[i]), range(n)))
        size = (int(960 * SCALE), int(540 * SCALE))
        frames = [Image.open(p).convert("RGB").resize(size, Image.LANCZOS) for p in paths]
    # a palette per frame: one shared palette drops small colour areas (the green AWS
    # icons, the blue selection) because the large flat backgrounds dominate it
    q = [f.quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
         for f in frames]
    durations = [1000 // FPS] * n
    durations[int(4.6 * FPS)] = 900   # linger on the dropped notebook
    durations[int(8.8 * FPS)] = 1200  # and on the tablet
    OUT.parent.mkdir(parents=True, exist_ok=True)
    q[0].save(OUT, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=True)
    print(f"{OUT.relative_to(ROOT)}: {n} frames, {OUT.stat().st_size // 1024} KB", file=sys.stderr)


if __name__ == "__main__":
    main()
