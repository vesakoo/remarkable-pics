"""Package a Document as a reMarkable .rmdoc (zip) notebook."""

import io
import json
import time
import uuid
import zipfile
from pathlib import Path

from rmdraw.model import Document
from rmdraw.rmwriter import write_page

_LETTERS = "abcdefghijklmnopqrstuvwxyz"
MAX_PAGES = 25 * 26  # first letter b..z, second a..z


def _idx(i: int) -> str:
    return _LETTERS[1 + i // 26] + _LETTERS[i % 26]


def write_rmdoc(doc: Document, path: Path) -> str:
    if not doc.pages:
        raise ValueError("document has no pages")
    if len(doc.pages) > MAX_PAGES:
        raise ValueError(f"too many pages (max {MAX_PAGES})")

    doc_id = str(uuid.uuid4())
    page_ids = [str(uuid.uuid4()) for _ in doc.pages]
    rms = []
    for page in doc.pages:
        buf = io.BytesIO()
        write_page(page, buf)
        rms.append(buf.getvalue())

    content = {
        "cPages": {
            "lastOpened": {"timestamp": "1:1", "value": page_ids[0]},
            "original": {"timestamp": "0:0", "value": -1},
            "pages": [
                {
                    "id": pid,
                    "idx": {"timestamp": "1:2", "value": _idx(i)},
                    "template": {"timestamp": "1:1", "value": "Blank"},
                }
                for i, pid in enumerate(page_ids)
            ],
            "uuids": [{"first": str(uuid.uuid4()), "second": 1}],
        },
        "coverPageNumber": -1,
        "customZoomCenterX": 0,
        "customZoomCenterY": 936,
        "customZoomOrientation": "portrait",
        "customZoomPageHeight": 1872,
        "customZoomPageWidth": 1404,
        "customZoomScale": 1,
        "documentMetadata": {},
        "extraMetadata": {},
        "fileType": "notebook",
        "fontName": "",
        "formatVersion": 2,
        "lineHeight": 100,
        "orientation": "portrait",
        "pageCount": len(page_ids),
        "pageTags": [],
        "sizeInBytes": str(sum(len(r) for r in rms)),
        "tags": [],
        "textAlignment": "justify",
        "textScale": 1,
        "zoomMode": "bestFit",
    }
    now = str(int(time.time() * 1000))
    metadata = {
        "createdTime": now,
        "lastModified": now,
        "lastOpened": "0",
        "lastOpenedPage": 0,
        "new": False,
        "parent": "",
        "pinned": False,
        "source": "",
        "type": "DocumentType",
        "visibleName": doc.name,
    }

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{doc_id}.content", json.dumps(content, indent=4))
        z.writestr(f"{doc_id}.metadata", json.dumps(metadata, indent=4))
        for pid, data in zip(page_ids, rms):
            z.writestr(f"{doc_id}/{pid}.rm", data)
    return doc_id
