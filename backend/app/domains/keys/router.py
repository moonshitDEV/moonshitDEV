from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Body

from ...security.auth import require_session, Session
from ...security.hmac import new_key
from ...db import list_api_keys, revoke_api_key


router = APIRouter(prefix="/keys", tags=["keys"])  # under /api/v1


@router.get("")
def list_keys(sess: Session = Depends(require_session)):
    return list_api_keys()


@router.post("/new")
def issue_key(scopes: List[str] = Body(...), sess: Session = Depends(require_session)):
    kid, secret = new_key(scopes)
    return {"key_id": kid, "secret": secret, "scopes": scopes}


@router.post("/revoke")
def revoke(key_id: str = Body(...), sess: Session = Depends(require_session)):
    ok = revoke_api_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return {"ok": True}
