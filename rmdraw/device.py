"""Install generated notebooks on a reMarkable over SSH (additive only, never deletes)."""
from __future__ import annotations

import re
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

XOCHITL = "/home/root/.local/share/remarkable/xochitl"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
SCP = ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-r"]
UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


HOST_RE = r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+"


def check_host(host: str) -> str:
    """Reject anything ssh/scp could read as an option (e.g. -oProxyCommand=...)."""
    if not isinstance(host, str) or host.startswith("-") or not re.fullmatch(HOST_RE, host):
        raise ValueError(f"invalid host {host!r} (expected user@host, e.g. root@10.11.99.1)")
    return host


def _check_uuid(uuid: str) -> str:
    if not isinstance(uuid, str) or not re.fullmatch(UUID_RE, uuid):
        raise ValueError(f"invalid document uuid {uuid!r}")
    return uuid


def _doc_uuid(names: list[str]) -> str:
    """Validate the zip layout and return the doc uuid."""
    contents = [n for n in names if n.endswith(".content")]
    if len(contents) != 1:
        raise ValueError("rmdoc must contain exactly one .content file")
    uuid = _check_uuid(contents[0][: -len(".content")])
    allowed = {f"{uuid}.content", f"{uuid}.metadata", f"{uuid}/"}
    page_re = re.compile(rf"{re.escape(uuid)}/{UUID_RE}\.rm")
    for n in names:
        if n not in allowed and not page_re.fullmatch(n):
            raise ValueError(f"unexpected entry in rmdoc: {n!r}")
    if f"{uuid}.metadata" not in names:
        raise ValueError("rmdoc has no .metadata file")
    if not any(page_re.fullmatch(n) for n in names):
        raise ValueError("rmdoc has no page files")
    return uuid


def install_rmdoc(path: Path, host: str = "root@10.11.99.1", runner=subprocess.run) -> str:
    check_host(host)
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path) as z:
            uuid = _doc_uuid(z.namelist())
            z.extractall(tmp)
        r = runner(SSH + [host, f"ls -d {XOCHITL}/{uuid}*"], capture_output=True, text=True)
        out, err = (r.stdout or "").strip(), (r.stderr or "")
        if r.returncode == 0 and out:
            raise FileExistsError(f"{uuid} already exists on the device")
        if not (r.returncode in (1, 2) and not out and "No such file" in err):
            raise RuntimeError(
                f"existence check failed (rc={r.returncode}): {err.strip() or out}")
        for name in (f"{uuid}.content", f"{uuid}.metadata", uuid):
            runner(SCP + [str(Path(tmp) / name), f"{host}:{XOCHITL}/"],
                   check=True, capture_output=True, text=True)
        runner(SSH + [host, "systemctl restart xochitl"], check=True,
               capture_output=True, text=True)
    return uuid


def fetch_thumbnails(doc_uuid: str, out_dir: Path, host: str = "root@10.11.99.1",
                     runner=subprocess.run, wait_s: float = 10, sleep=time.sleep) -> list[Path]:
    check_host(host)
    _check_uuid(doc_uuid)
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
