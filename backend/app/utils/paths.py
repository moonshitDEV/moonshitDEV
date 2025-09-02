from __future__ import annotations

import os
from pathlib import Path


def secure_join(root: Path, user_path: str) -> Path:
    up = user_path or "/"
    up = os.path.normpath("/" + up).lstrip("/")  # prevent traversal
    p = (root / up).resolve()
    root_res = root.resolve()
    if not str(p).startswith(str(root_res)):
        raise PermissionError("Path traversal detected")
    return p

