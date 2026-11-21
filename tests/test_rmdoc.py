import json
import re
import zipfile
from pathlib import Path

import pytest
import rmdraw  # noqa: F401
from rmscene import read_blocks
from rmscene.scene_stream import UnreadableBlock

from rmdraw.model import Document, Page, Stroke
from rmdraw.rmdoc import write_rmdoc

REFDIR = Path(__file__).parent / "fixtures/reference"
REF_CONTENT = json.loads((REFDIR / "8854cd39-dba3-48f7-8c5f-e6b9f0cea45f.content").read_text())
REF_META = json.loads((REFDIR / "8854cd39-dba3-48f7-8c5f-e6b9f0cea45f.metadata").read_text())
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"


def _doc(n=2, name="My Doc"):
    return Document(name, [Page([Stroke([(10, 10), (20, 30)])]) for _ in range(n)])


def _build(tmp_path, n=2, name="My Doc"):
    p = tmp_path / "x.rmdoc"
    uid = write_rmdoc(_doc(n, name), p)
    return uid, zipfile.ZipFile(p)


def test_zip_layout(tmp_path):
    uid, z = _build(tmp_path, 3)
    assert re.fullmatch(UUID, uid)
    names = z.namelist()
    assert f"{uid}.content" in names and f"{uid}.metadata" in names
    rms = [n for n in names if n.endswith(".rm")]
    assert len(rms) == 3
    for n in rms:
        assert re.fullmatch(rf"{uid}/{UUID}\.rm", n)
    assert len(names) == 5
    assert all(i.compress_type == zipfile.ZIP_DEFLATED for i in z.infolist())


def test_content_keys_match_reference(tmp_path):
    uid, z = _build(tmp_path, 3)
    c = json.loads(z.read(f"{uid}.content"))
    assert set(c) == set(REF_CONTENT)
    ids = [p["id"] for p in c["cPages"]["pages"]]
    stems = [Path(n).stem for n in z.namelist() if n.endswith(".rm")]
    assert ids == stems
    assert c["pageCount"] == 3
    assert c["cPages"]["lastOpened"]["value"] == ids[0]
    total = sum(i.file_size for i in z.infolist() if i.filename.endswith(".rm"))
    assert c["sizeInBytes"] == str(total)
    for k in ("customZoomCenterY", "customZoomPageHeight", "customZoomPageWidth"):
        assert c[k] == REF_CONTENT[k]
    assert set(c["cPages"]) == set(REF_CONTENT["cPages"])


def test_page_idx_sort(tmp_path):
    uid, z = _build(tmp_path, 30)
    c = json.loads(z.read(f"{uid}.content"))
    idx = [p["idx"]["value"] for p in c["cPages"]["pages"]]
    assert idx[0] == "ba"
    assert all(a < b for a, b in zip(idx, idx[1:]))


def test_metadata_fields(tmp_path):
    uid, z = _build(tmp_path, 1, "Hello")
    m = json.loads(z.read(f"{uid}.metadata"))
    assert set(m) == set(REF_META)
    assert m["visibleName"] == "Hello"
    assert m["type"] == "DocumentType"
    assert m["parent"] == "" and m["lastOpened"] == "0" and m["lastOpenedPage"] == 0
    assert m["new"] is False and m["pinned"] is False
    assert m["createdTime"].isdigit() and m["lastModified"].isdigit()


def test_pages_readable(tmp_path):
    uid, z = _build(tmp_path, 2)
    import io
    for n in z.namelist():
        if n.endswith(".rm"):
            blocks = list(read_blocks(io.BytesIO(z.read(n))))
            assert blocks and not any(isinstance(b, UnreadableBlock) for b in blocks)


def test_empty_and_too_many(tmp_path):
    with pytest.raises(ValueError):
        write_rmdoc(Document("e", []), tmp_path / "e.rmdoc")
    with pytest.raises(ValueError):
        write_rmdoc(_doc(651), tmp_path / "big.rmdoc")
