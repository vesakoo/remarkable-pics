import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from rmdraw import device
from rmdraw.model import Document, Page, Stroke
from rmdraw.rmdoc import write_rmdoc


class Fake:
    def __init__(self, exists=False, thumbs_after=0, rc=None):
        self.rc = rc
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
                out = "/home/root/x/b9e10bde-1351-43f5-a32b-1f945c933961.thumbnails/0.png\n"
        elif cmd[0] == "ssh" and "ls" in joined:
            out = "somefile\n" if self.exists else ""
            rc = 0 if self.exists else 2
        err = "ls: No such file or directory" if rc == 2 else ""
        if self.rc is not None and cmd[0] == "ssh" and "ls -d" in joined:
            rc, out, err = self.rc, "", "ssh: connect to host: No route to host"
        return SimpleNamespace(returncode=rc, stdout=out, stderr=err)


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
    out = device.fetch_thumbnails("b9e10bde-1351-43f5-a32b-1f945c933961", tmp_path / "o", runner=f, wait_s=5, sleep=lambda s: None)
    assert all("BatchMode=yes" in c for c in f.cmds)
    assert f.ls_calls == 2
    assert any(c[0] == "scp" and "b9e10bde-1351-43f5-a32b-1f945c933961.thumbnails" in c[-2] for c in f.cmds)
    assert (tmp_path / "o").is_dir()
    assert all("rm " not in " ".join(c) for c in f.cmds)


def test_install_fails_closed_on_ssh_error(tmp_path):
    p, _ = make(tmp_path)
    f = Fake(rc=255)
    with pytest.raises(RuntimeError):
        device.install_rmdoc(p, runner=f)
    assert not any(c[0] == "scp" for c in f.cmds)
    assert not any("restart" in " ".join(c) for c in f.cmds)


def _zip(tmp_path, names):
    p = tmp_path / "h.rmdoc"
    with zipfile.ZipFile(p, "w") as z:
        for n in names:
            z.writestr(n, "x")
    return p


U = "b9e10bde-1351-43f5-a32b-1f945c933961"
P = "e69a9c4e-4635-48f2-8e3f-f7b5696d40e6"


def test_install_rejects_hostile_name(tmp_path):
    p = _zip(tmp_path, ["x; reboot #.content", "x; reboot #.metadata", f"x; reboot #/{P}.rm"])
    f = Fake()
    with pytest.raises(ValueError):
        device.install_rmdoc(p, runner=f)
    assert f.cmds == []


@pytest.mark.parametrize("extra", ["../evil", "/etc/passwd", f"{U}/../x.rm", f"{U}/notes.txt"])
def test_install_rejects_extra_entry(tmp_path, extra):
    p = _zip(tmp_path, [f"{U}.content", f"{U}.metadata", f"{U}/{P}.rm", extra])
    f = Fake()
    with pytest.raises(ValueError):
        device.install_rmdoc(p, runner=f)
    assert f.cmds == []


def test_install_rejects_missing_metadata(tmp_path):
    p = _zip(tmp_path, [f"{U}.content", f"{U}/{P}.rm"])
    with pytest.raises(ValueError):
        device.install_rmdoc(p, runner=Fake())


def test_fetch_rejects_bad_uuid(tmp_path):
    f = Fake()
    with pytest.raises(ValueError):
        device.fetch_thumbnails("x; reboot", tmp_path, runner=f)
    assert f.cmds == []


@pytest.mark.parametrize("host", ["-oProxyCommand=touch /tmp/x", "root@x;ls", "nohost", ""])
def test_device_rejects_bad_host(tmp_path, host):
    def runner(*a, **k):
        raise AssertionError("must not run ssh/scp")
    with pytest.raises(ValueError, match="invalid host"):
        device.install_rmdoc(tmp_path / "x.rmdoc", host=host, runner=runner)
    with pytest.raises(ValueError, match="invalid host"):
        device.fetch_thumbnails("0b1c2d3e-0000-4000-8000-000000000000", tmp_path, host=host,
                                runner=runner)
    assert device.check_host("root@10.11.99.1") == "root@10.11.99.1"
