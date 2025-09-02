from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Iterable


ALLOWED_MIME_PREFIXES = (
    "text/",
    "image/",
    "application/pdf",
    "application/zip",
)


def is_allowed_mime(path: Path) -> bool:
    m, _ = mimetypes.guess_type(str(path))
    if not m:
        return False
    return m.startswith(ALLOWED_MIME_PREFIXES) or m in ALLOWED_MIME_PREFIXES


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

