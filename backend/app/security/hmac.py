from __future__ import annotations

# Built-in HMAC verification for API clients
import base64
import hashlib
import hmac
import time
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi import status as http
from cryptography.fernet import Fernet  # pip install cryptography
from ..settings import get_settings
from ..db import lookup_api_key, create_api_key


class HMACCredentials:
    def __init__(self, key_id: str, ts: int, nonce: str, sig: str, scope_ok: bool):
        self.key_id = key_id
        self.ts = ts
        self.nonce = nonce
        self.sig = sig
        self.scope_ok = scope_ok


_nonce_cache: set[str] = set()


def _hash_secret(secret: str) -> str:
    # Use SHA256 for HMAC secret hash at rest (not for password auth)
    return hashlib.sha256(secret.encode()).hexdigest()


def parse_auth_header(value: str) -> Optional[dict[str, str]]:
    if not value or not value.startswith("HMAC "):
        return None
    parts = value[len("HMAC "):].split(",")
    data = {}
    for p in parts:
        if "=" in p:
            k, v = p.strip().split("=", 1)
            data[k] = v
    return data


def require_hmac(required_scopes: list[str]):
    async def dep(request: Request) -> HMACCredentials:
        hdr = request.headers.get("Authorization")
        parsed = parse_auth_header(hdr)
        if not parsed:
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Missing HMAC header")

        key_id = parsed.get("keyId")
        ts_str = parsed.get("ts")
        nonce = parsed.get("nonce")
        sig = parsed.get("sig")
        if not key_id or not ts_str or not nonce or not sig:
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC header")

        if nonce in _nonce_cache:
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Replay detected")
        try:
            ts = int(ts_str)
        except ValueError:
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Bad timestamp")

        if abs(time.time() - ts) > 300:
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Timestamp skew too large")

        rec = lookup_api_key(key_id)
        if not rec:
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Unknown key")
        scopes = set((rec.get("scopes") or "").split(","))

        body_bytes = await request.body()
        body_hash = hashlib.sha256(body_bytes or b"").hexdigest()
        canonical = "|".join([request.method.upper(), request.url.path, str(ts), nonce, body_hash])
        # We cannot recover the secret from hash; for verification we need the raw secret.
        # Expect clients to send correct signature with their secret; server verifies via derived request.
        # For this scaffold, we temporarily store a transient map of key_id->secret for issued keys
        # to support verification without a full KMS. On production, load from a secure secrets vault.
        secret_bytes = _ISSUED_SECRETS.get(key_id)
        if not secret_bytes:
            enc = rec.get("secret_enc")
            if enc:
                # Derive Fernet key from DASH_SECRET_KEY
                key = hashlib.sha256(get_settings().secret_key.encode()).digest()
                fkey = base64.urlsafe_b64encode(key)
                f = Fernet(fkey)
                try:
                    secret_bytes = f.decrypt(enc)
                except Exception:
                    raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Secret invalid")
            else:
                raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Secret not available for verification")
        expected = base64.b64encode(hmac.new(secret_bytes, canonical.encode(), hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(http.HTTP_401_UNAUTHORIZED, detail="Bad signature")

        # Nonce memory cache (short-lived); in prod use Redis with TTL
        _nonce_cache.add(nonce)
        if len(_nonce_cache) > 10000:
            _nonce_cache.clear()

        scope_ok = all(s in scopes for s in required_scopes)
        if not scope_ok:
            raise HTTPException(http.HTTP_403_FORBIDDEN, detail="Insufficient scope")

        return HMACCredentials(key_id, ts, nonce, sig, scope_ok)

    return dep


_ISSUED_SECRETS: dict[str, bytes] = {}

def new_key(scopes: list[str]) -> tuple[str, str]:
    kid = uuid.uuid4().hex
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    # Encrypt secret for verification and store hash for audit
    key = hashlib.sha256(get_settings().secret_key.encode()).digest()
    fkey = base64.urlsafe_b64encode(key)
    f = Fernet(fkey)
    enc = f.encrypt(secret.encode())
    create_api_key(kid, _hash_secret(secret), scopes, secret_enc=enc)
    _ISSUED_SECRETS[kid] = secret.encode()
    return kid, secret
