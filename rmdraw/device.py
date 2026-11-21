"""Install generated notebooks on a reMarkable over SSH (additive only, never deletes)."""
from __future__ import annotations

import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

XOCHITL = "/home/root/.local/share/remarkable/xochitl"
SSH = ["ssh", "-o", "BatchMode=yes"]
SCP = ["scp", "-o", "BatchMode=yes", "-r"]


def _doc_uuid(names: list[str]) -> str:
    for n in names:
        if n.endswith(".content"):
            return n[: -len(".content")]
    raise ValueError("no .content file in rmdoc")


def install_rmdoc(path: Path, host: str = "root@10.11.99.1", runner=subprocess.run) -> str:
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path) as z:
            uuid = _doc_uuid(z.namelist())
            z.extractall(tmp)
        r = runner(SSH + [host, f"ls -d {XOCHITL}/{uuid}* 2>/dev/null"],
                   capture_output=True, text=True)
        if r.returncode == 0 and (r.stdout or "").strip():
            raise FileExistsError(f"{uuid} already exists on the device")
        for name in (f"{uuid}.content", f"{uuid}.metadata", uuid):
            runner(SCP + [str(Path(tmp) / name), f"{host}:{XOCHITL}/"],
                   check=True, capture_output=True, text=True)
        runner(SSH + [host, "systemctl restart xochitl"], check=True,
               capture_output=True, text=True)
    return uuid


def fetch_thumbnails(doc_uuid: str, out_dir: Path, host: str = "root@10.11.99.1",
                     runner=subprocess.run, wait_s: float = 10, sleep=time.sleep) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    remote = f"{XOCHITL}/{doc_uuid}.thumbnails"
    waited = 0.0
    while True:
        r = runner(SSH + [host, f"ls {remote}/*.png 2>/dev/null"], capture_output=True, text=True)
        if (r.stdout or "").strip():
            break
        if waited >= wait_s:
            return []
        sleep(1.0)
        waited += 1.0
    runner(SCP + [f"{host}:{remote}", str(out_dir)], check=True, capture_output=True, text=True)
    sub = out_dir / f"{doc_uuid}.thumbnails"
    result = []
    for png in sorted(sub.glob("*.png")):
        dest = out_dir / png.name
        png.replace(dest)
        result.append(dest)
    return result
