"""Render the square social-media videos of the import animation.

    python tools/import_guide/make_video.py            # -> out/import-guide-en.mp4, out/import-guide-fi.mp4

Each frame is square.html?t=<seconds>&lang=<en|fi>, screenshotted by headless Chrome and
joined with ffmpeg (H.264, yuv420p, 1080x1080, which LinkedIn and Facebook accept).
Needs Google Chrome and ffmpeg. The videos land loose in out/, which git ignores.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FPS, DURATION, LOOPS = 25, 10.0, 2  # play the loop twice so the clip isn't over too fast


def shot(url: str, path: Path) -> None:
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--allow-file-access-from-files", "--virtual-time-budget=2000",
                    "--window-size=1080,1080", f"--screenshot={path}", url],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render(lang: str) -> Path:
    n = int(FPS * DURATION)
    out = ROOT / "out" / f"import-guide-{lang}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        jobs = [(f"file://{HERE / 'square.html'}?t={i / FPS:.3f}&lang={lang}",
                 Path(tmp) / f"f{i:04d}.png") for i in range(n)]
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda j: shot(*j), jobs))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", str(LOOPS - 1),
                        "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                        "-movflags", "+faststart", str(out)], check=True)
    print(f"{out.relative_to(ROOT)}: {out.stat().st_size // 1024} KB", file=sys.stderr)
    return out


if __name__ == "__main__":
    for lang in sys.argv[1:] or ["en", "fi"]:
        render(lang)
