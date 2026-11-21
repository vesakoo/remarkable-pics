import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from rmdraw import device
from rmdraw.model import Document, Page, Stroke
from rmdraw.rmdoc import write_rmdoc


class Fake:
    def __init__(self, exists=False, thumbs_after=0):
        self.cmds = []
        self.exists = exists
        self.thumbs_after = thumbs_after
        self.ls_calls = 0

    def __call__(self, cmd, **kw):
        self.cmds.append(list(cmd))
        out = ""
        rc = 0
        joined = " ".join(cmd)
        if cmd[0] == "ssh" and "thumbnails" in joined and "ls" in joined:
            self.ls_calls += 1
            if self.ls_calls > self.thumbs_after:
                out = "/home/root/x/abc.thumbnails/0.png\n"
        elif cmd[0] == "ssh" and "ls" in joined:
            out = "somefile\n" if self.exists else ""
            rc = 0 if self.exists else 2
        return SimpleNamespace(returncode=rc, stdout=out, stderr="")


def make(tmp_path):
    doc = Document("T", [Page([Stroke([(1, 1), (5, 5)])])])
    p = tmp_path / "t.rmdoc"
    return p, write_rmdoc(doc, p)


def test_install_commands(tmp_path):
    p, uuid = make(tmp_path)
    f = Fake()
    assert device.install_rmdoc(p, runner=f) == uuid
    assert all("BatchMode=yes" in c for c in f.cmds)
    assert f.cmds[0][0] == "ssh" and uuid in " ".join(f.cmds[0])
    scps = [c for c in f.cmds if c[0] == "scp"]
    assert len(scps) >= 3
    assert any(c[-1].startswith("root@10.11.99.1:") for c in scps)
    assert any(f"{uuid}.content" in c[-2] for c in scps)
    assert f.cmds[-1][0] == "ssh" and "systemctl restart xochitl" in " ".join(f.cmds[-1])
    for c in f.cmds:
        assert "rm " not in " ".join(c) and "delete" not in " ".join(c)


def test_install_refuses_existing(tmp_path):
    p, uuid = make(tmp_path)
    f = Fake(exists=True)
    with pytest.raises(FileExistsError):
        device.install_rmdoc(p, runner=f)
    assert not any(c[0] == "scp" for c in f.cmds)
    assert not any("restart" in " ".join(c) for c in f.cmds)


def test_fetch_thumbnails(tmp_path):
    f = Fake(thumbs_after=1)
    out = device.fetch_thumbnails("abc", tmp_path / "o", runner=f, wait_s=5, sleep=lambda s: None)
    assert all("BatchMode=yes" in c for c in f.cmds)
    assert f.ls_calls == 2
    assert any(c[0] == "scp" and "abc.thumbnails" in c[-2] for c in f.cmds)
    assert (tmp_path / "o").is_dir()
    assert all("rm " not in " ".join(c) for c in f.cmds)
