from __future__ import annotations

import hmac
import hashlib
from typing import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import SESSION_COOKIE, load_session
from ..settings import get_settings


def _sign(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def issue_csrf_token(user: str) -> str:
    # Token derived from user + secret; stateless
    secret = get_settings().secret_key
    return _sign(f"csrf:{user}", secret)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # Only protect state-changing methods for cookie-based sessions
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            sess = load_session(request.cookies.get(SESSION_COOKIE))
            if sess:
                supplied = request.headers.get("X-CSRF-Token")
                if not supplied or supplied != issue_csrf_token(sess.user):
                    return JSONResponse({"detail": "Invalid CSRF token"}, status_code=403)
        return await call_next(request)


router = APIRouter(prefix="/auth", tags=["auth"])  # unified with auth namespace


@router.get("/csrf")
def get_csrf(request: Request):
    sess = load_session(request.cookies.get(SESSION_COOKIE))
    if not sess:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return {"token": issue_csrf_token(sess.user)}

