from __future__ import annotations

from typing import List

from fastapi import Depends, HTTPException
from fastapi import status as http

from fastapi import Request
from .auth import load_session
from .hmac import require_hmac, HMACCredentials


def require_user_or_hmac(required_scopes: List[str]):
    # OR dependency: returns True if session cookie is valid OR HMAC header valid with scopes
    async def wrapper(request: Request, hmac_result=Depends(_try_hmac(required_scopes))):
        sess = load_session(request.cookies.get("dash_session"))
        if sess or hmac_result:
            return True
        raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Auth required")

    return wrapper


async def _try_session():
    return False


def _try_hmac(required_scopes: List[str]):
    async def inner(_: HMACCredentials = Depends(require_hmac(required_scopes))):
        return True

    return inner
