from __future__ import annotations

import io
import json
import os
import re
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, RootModel, field_validator

from ...security.deps import require_user_or_hmac


router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_user_or_hmac(["tasks:write"]))])


class LessonFile(BaseModel):
    path: str
    contents: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, v: str):
        if v.startswith("/"):
            raise ValueError("Absolute paths not allowed")
        norm = os.path.normpath("/" + v).lstrip("/")
        if ".." in Path(norm).parts:
            raise ValueError("Path traversal not allowed")
        if norm == "" or norm.endswith("/"):
            raise ValueError("Invalid file path")
        return norm


class LessonPackageInput(BaseModel):
    title: str
    lessonMarkdown: str
    files: List[LessonFile] = Field(default_factory=list)
    readme: Optional[str] = None
    metadata: Optional[dict] = None


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\-_. ]+", "", text)
    s = s.strip().lower().replace(" ", "-")
    return re.sub(r"-+", "-", s) or f"pkg-{int(time.time())}"


def _lint_basic(path: str, contents: str) -> list[str]:
    errs: list[str] = []
    if path.endswith(('.html', '.htm')):
        if '<html' in contents and '</html>' not in contents:
            errs.append(f"{path}: missing </html>")
        # Very naive tag balance for <script> and <style>
        if contents.count('<script') != contents.count('</script>'):
            errs.append(f"{path}: unbalanced <script> tags")
        if contents.count('<style') != contents.count('</style>'):
            errs.append(f"{path}: unbalanced <style> tags")
    if path.endswith(('.js', '.ts', '.jsx', '.tsx')):
        # Balance braces/parens/brackets
        pairs = {'{': '}', '(': ')', '[': ']'}
        stack = []
        for ch in contents:
            if ch in pairs:
                stack.append(pairs[ch])
            elif ch in pairs.values():
                if not stack or stack.pop() != ch:
                    errs.append(f"{path}: unbalanced braces/parens/brackets")
                    break
    if path.endswith('.css'):
        if contents.count('{') != contents.count('}'):
            errs.append(f"{path}: unbalanced CSS braces")
    return errs


def _ensure_citations(md: str, files: list[LessonFile]) -> list[str]:
    # Assumption: any file under knowledge/ must be cited by name in lessonMarkdown
    errs: list[str] = []
    lower = md.lower()
    for f in files:
        if f.path.startswith('knowledge/'):
            name = Path(f.path).name.lower()
            if name not in lower and f.path.lower() not in lower:
                errs.append(f"lesson.md should cite knowledge file: {f.path}")
    return errs


@router.post("/create_lesson_package")
def create_lesson_package(payload: LessonPackageInput):
    # Validate duplicate names
    seen = set()
    dups = [f.path for f in payload.files if (f.path in seen or seen.add(f.path))]
    if dups:
        raise HTTPException(status_code=400, detail={"error": "Duplicate file paths", "paths": dups})

    # Lint basic syntax
    lint_errs: list[str] = []
    for f in payload.files:
        lint_errs.extend(_lint_basic(f.path, f.contents))
    if lint_errs:
        raise HTTPException(status_code=400, detail={"error": "Lint errors", "issues": lint_errs})

    # Ensure citations
    cite_errs = _ensure_citations(payload.lessonMarkdown, payload.files)
    if cite_errs:
        raise HTTPException(status_code=400, detail={"error": "Citation errors", "issues": cite_errs})

    # Prepare temp dir structure
    tmpdir = Path(tempfile.mkdtemp(prefix="lesson_pkg_"))
    try:
        # lesson.md
        lesson_path = tmpdir / "lesson.md"
        title = payload.title.strip()
        md = payload.lessonMarkdown
        if not md.lstrip().startswith('#'):
            md = f"# {title}\n\n" + md
        lesson_path.write_text(md, encoding='utf-8')

        # README.md
        if payload.readme:
            (tmpdir / "README.md").write_text(payload.readme, encoding='utf-8')

        # Files
        for f in payload.files:
            p = tmpdir / f.path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f.contents, encoding='utf-8')

        # Metadata
        if payload.metadata:
            (tmpdir / "metadata.json").write_text(json.dumps(payload.metadata, indent=2), encoding='utf-8')

        # Zip the bundle
        slug = _slugify(title)
        ts = time.strftime('%Y%m%d%H%M%S')
        zip_name = f"{slug}-{ts}.zip"

        # Save zip under nginx-served downloads directory
        downloads_root = Path('/var/www/moonshit/current/downloads')
        downloads_root.mkdir(parents=True, exist_ok=True)
        zip_path = downloads_root / zip_name

        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for child in tmpdir.rglob('*'):
                if child.is_file():
                    zf.write(child, arcname=str(child.relative_to(tmpdir)))

        # Build URL
        url = f"https://moonshit.dev/downloads/{zip_name}"
        return {"url": url}
    finally:
        # Cleanup temp dir
        try:
            for child in reversed(list(tmpdir.rglob('*'))):
                if child.is_file():
                    child.unlink()
                else:
                    child.rmdir()
            tmpdir.rmdir()
        except Exception:
            pass

