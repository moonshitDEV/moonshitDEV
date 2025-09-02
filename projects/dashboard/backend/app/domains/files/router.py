from __future__ import annotations

# pip install aiofiles python-multipart
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi import status as http
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import tempfile
import zipfile

from ...security.auth import Session
from ...security.deps import require_user_or_hmac
from ...settings import get_settings
from ...utils.paths import secure_join
from .utils import file_sha256, is_allowed_mime


router = APIRouter(prefix="/files", tags=["files"])  # under /api/v1


def user_root(sess: Session) -> Path:
    s = get_settings()
    root = s.data_root / sess.user / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


@router.get("/list", dependencies=[Depends(require_user_or_hmac(["files:read"]))])
def list_dir(path: str = Query("/"), sess: Session = Depends(lambda: None)):
    # For HMAC callers there is no session; derive user folder as 'api'
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    root = user_root(sess)
    d = secure_join(root, path)
    if not d.exists() or not d.is_dir():
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Not found")
    items = []
    for p in sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        stat = p.stat()
        items.append(
            {
                "name": p.name,
                "type": "dir" if p.is_dir() else "file",
                "bytes": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    return items


@router.post("/mkdir", dependencies=[Depends(require_user_or_hmac(["files:write"]))])
def mkdir(path: str = Form(...), sess: Session = Depends(lambda: None)):
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    root = user_root(sess)
    p = secure_join(root, path)
    p.mkdir(parents=True, exist_ok=True)
    return {"ok": True}


@router.post("/rename", dependencies=[Depends(require_user_or_hmac(["files:write"]))])
def rename(frm: str = Form(...), to: str = Form(...), sess: Session = Depends(lambda: None)):
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    root = user_root(sess)
    p_from = secure_join(root, frm)
    p_to = secure_join(root, to)
    if not p_from.exists():
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Source not found")
    p_to.parent.mkdir(parents=True, exist_ok=True)
    p_from.rename(p_to)
    return {"ok": True}


@router.delete("", dependencies=[Depends(require_user_or_hmac(["files:write"]))])
def delete(path: str = Query(...), sess: Session = Depends(lambda: None)):
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    root = user_root(sess)
    p = secure_join(root, path)
    if p.is_dir():
        try:
            p.rmdir()
        except OSError:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="Directory not empty")
    elif p.is_file():
        p.unlink()
    else:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Not found")
    return {"ok": True}


@router.post("/upload", dependencies=[Depends(require_user_or_hmac(["files:write"]))])
async def upload(
    path: str = Query("/"),
    zip: bool = Form(False),
    zip_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    sess: Session = Depends(lambda: None),
):
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    s = get_settings()
    root = user_root(sess)
    d = secure_join(root, path)
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)

    # No restrictions per user request: accept any file type/size (bounded by disk)
    if zip:
        zname = zip_name or "upload.zip"
        dest = d / zname
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if files:
                for f in files:
                    zinfo_name = f.filename or "file"
                    tmp = tempfile.NamedTemporaryFile(delete=False)
                    try:
                        while True:
                            chunk = await f.read(1024 * 1024)
                            if not chunk:
                                break
                            tmp.write(chunk)
                        tmp.flush(); tmp.close()
                        zf.write(tmp.name, arcname=zinfo_name)
                    finally:
                        try: os.unlink(tmp.name)
                        except Exception: pass
            elif file:
                zinfo_name = file.filename or "file"
                tmp = tempfile.NamedTemporaryFile(delete=False)
                try:
                    while True:
                        chunk = await file.read(1024 * 1024)
                        if not chunk:
                            break
                        tmp.write(chunk)
                    tmp.flush(); tmp.close()
                    zf.write(tmp.name, arcname=zinfo_name)
                finally:
                    try: os.unlink(tmp.name)
                    except Exception: pass
            else:
                raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="No files provided for zip upload")
        # Optional size enforcement when unrestricted is false
        if not s.upload_unrestricted:
            if dest.stat().st_size > s.upload_max_mb * 1024 * 1024:
                try: dest.unlink()
                except Exception: pass
                raise HTTPException(http.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Zip too large")
        return {"stored": str(dest.name), "sha256": file_sha256(dest), "zipped": True}
    else:
        stored = []
        if files:
            for f in files:
                dest = d / (f.filename or "file")
                async with aiofiles.open(dest, "wb") as out:
                    size = 0
                    while True:
                        chunk = await f.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if not s.upload_unrestricted and size > s.upload_max_mb * 1024 * 1024:
                            await out.close()
                            try: dest.unlink()
                            except Exception: pass
                            raise HTTPException(http.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
                        await out.write(chunk)
                if not s.upload_unrestricted and not is_allowed_mime(dest):
                    try: dest.unlink()
                    except Exception: pass
                    raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="MIME not allowed")
                stored.append({"name": dest.name, "sha256": file_sha256(dest)})
        elif file:
            dest = d / (file.filename or "file")
            async with aiofiles.open(dest, "wb") as out:
                size = 0
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if not s.upload_unrestricted and size > s.upload_max_mb * 1024 * 1024:
                        await out.close()
                        try: dest.unlink()
                        except Exception: pass
                        raise HTTPException(http.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
                    await out.write(chunk)
            if not s.upload_unrestricted and not is_allowed_mime(dest):
                try: dest.unlink()
                except Exception: pass
                raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="MIME not allowed")
            stored.append({"name": dest.name, "sha256": file_sha256(dest)})
        else:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="No file(s) provided")
        return {"stored": stored}


@router.get("/download", dependencies=[Depends(require_user_or_hmac(["files:read"]))])
def download(path: str = Query("/"), zip: bool = Query(False), paths: Optional[List[str]] = Query(None), zip_name: Optional[str] = Query(None), sess: Session = Depends(lambda: None)):
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    root = user_root(sess)
    if zip:
        # Build a temporary zip for multiple paths or a directory/single file
        zname = zip_name or "download.zip"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp_path = tmp.name
        tmp.close()
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            def add_path(rel_str: str):
                rel = Path(rel_str.lstrip('/'))
                full = secure_join(root, str(rel))
                if full.is_dir():
                    for sub in full.rglob('*'):
                        if sub.is_file():
                            zf.write(sub, arcname=str((rel / sub.relative_to(full)).as_posix()))
                elif full.is_file():
                    zf.write(full, arcname=str(rel))
            if paths:
                for r in paths:
                    add_path(r)
            else:
                add_path(path)
        return FileResponse(tmp_path, filename=zname, media_type="application/zip", background=BackgroundTask(lambda: os.unlink(tmp_path)))
    else:
        p = secure_join(root, path)
        if not p.exists() or not p.is_file():
            raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Not found")
        return FileResponse(path=str(p), filename=p.name)

@router.post("/zip", dependencies=[Depends(require_user_or_hmac(["files:read"]))])
def zip_paths(paths: List[str], name: Optional[str] = None, sess: Session = Depends(lambda: None)):
    if sess is None:
        class Dummy: user = 'api'
        sess = Dummy()
    root = user_root(sess)
    zname = name or "bundle.zip"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()
    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in paths:
            rel_path = Path(rel.lstrip('/'))
            full = secure_join(root, str(rel_path))
            if full.is_dir():
                for sub in full.rglob('*'):
                    if sub.is_file():
                        zf.write(sub, arcname=str((rel_path / sub.relative_to(full)).as_posix()))
            elif full.is_file():
                zf.write(full, arcname=str(rel_path))
    return FileResponse(tmp_path, filename=zname, media_type="application/zip", background=BackgroundTask(lambda: os.unlink(tmp_path)))
