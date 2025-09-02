from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Optional

from .settings import get_settings


def db_path() -> Path:
    # Default to /var/lib/dash/dash.db for systemd service; override with DASH_DB_PATH
    p = Path(os.environ.get("DASH_DB_PATH", "/var/lib/dash/dash.db"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> sqlite3.Connection:
    path = db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id TEXT UNIQUE NOT NULL,
            secret_hash TEXT NOT NULL,
            secret_enc BLOB,
            scopes TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            revoked_at INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def create_api_key(key_id: str, secret_hash: str, scopes: Iterable[str], secret_enc: bytes | None = None) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO api_keys (key_id, secret_hash, secret_enc, scopes, created_at) VALUES (?, ?, ?, ?, ?)",
        (key_id, secret_hash, secret_enc, ",".join(sorted(set(scopes))), int(time.time())),
    )
    conn.commit()
    conn.close()


def list_api_keys(include_revoked: bool = False) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if include_revoked:
        rows = cur.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()
    else:
        rows = cur.execute("SELECT * FROM api_keys WHERE revoked_at IS NULL ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_api_key(key_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE api_keys SET revoked_at=? WHERE key_id=? AND revoked_at IS NULL", (int(time.time()), key_id))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def lookup_api_key(key_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM api_keys WHERE key_id=? AND revoked_at IS NULL", (key_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
