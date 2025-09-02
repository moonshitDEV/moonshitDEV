from __future__ import annotations

# pip install argon2-cffi itsdangerous
import time
from dataclasses import dataclass
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi import status as http
from itsdangerous import BadSignature, URLSafeSerializer

from ..settings import get_settings


ph = PasswordHasher()  # argon2id defaults


def verify_password(hash_str: str, password: str) -> bool:
    try:
        ph.verify(hash_str, password)
        return True
    except VerifyMismatchError:
        return False


def session_signer() -> URLSafeSerializer:
    s = URLSafeSerializer(get_settings().secret_key, salt="dash-session")
    return s


SESSION_COOKIE = "dash_session"
SESSION_MAX_AGE = 24 * 3600


@dataclass
class Session:
    user: str
    iat: int


def create_session_cookie(user: str) -> str:
    s = session_signer()
    payload = {"u": user, "iat": int(time.time())}
    return s.dumps(payload)


def load_session(cookie: Optional[str]) -> Optional[Session]:
    if not cookie:
        return None
    try:
        data = session_signer().loads(cookie)
    except BadSignature:
        return None
    iat = int(data.get("iat", 0))
    if time.time() - iat > SESSION_MAX_AGE:
        return None
    return Session(user=data.get("u", ""), iat=iat)


# Simple in-memory lockouts; swap with Redis in prod
_fail_tracker: dict[str, tuple[int, float]] = {}


def _fail_key(user: str, ip: str) -> str:
    return f"{user}|{ip}"


def record_failure(user: str, ip: str) -> float:
    count, until = _fail_tracker.get(_fail_key(user, ip), (0, 0.0))
    count += 1
    backoff = min(300.0, 2 ** min(8, count))  # cap at 5m
    unlock_at = time.time() + backoff
    _fail_tracker[_fail_key(user, ip)] = (count, unlock_at)
    return backoff


def can_attempt(user: str, ip: str) -> tuple[bool, float]:
    count, until = _fail_tracker.get(_fail_key(user, ip), (0, 0.0))
    if until and time.time() < until:
        return False, until - time.time()
    return True, 0.0


def clear_failures(user: str, ip: str) -> None:
    _fail_tracker.pop(_fail_key(user, ip), None)


# Dependencies
def require_session(request: Request) -> Session:
    sess = load_session(request.cookies.get(SESSION_COOKIE))
    if not sess:
        raise HTTPException(status_code=http.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return sess


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    ip = request.client.host if request.client else "?"
    ok, wait = can_attempt(username, ip)
    if not ok:
        raise HTTPException(status_code=429, detail=f"Locked. Retry in {int(wait)}s")

    settings = get_settings()
    if username != settings.admin_user or not settings.admin_pass_hash or not verify_password(
        settings.admin_pass_hash, password
    ):
        backoff = record_failure(username, ip)
        raise HTTPException(status_code=http.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    clear_failures(username, ip)
    cookie = create_session_cookie(username)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=cookie,
        max_age=SESSION_MAX_AGE,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response, sess: Session = Depends(require_session)):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(sess: Session = Depends(require_session)):
    return {"user": sess.user}


# Temporary: debug settings (only from localhost)
@router.get("/debug_env")
def debug_env(request: Request):
    if request.client and request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=http.HTTP_404_NOT_FOUND, detail="Not Found")
    s = get_settings()
    return {"admin_user": s.admin_user, "has_hash": bool(s.admin_pass_hash)}
