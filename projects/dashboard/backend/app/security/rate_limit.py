from __future__ import annotations

import time
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def parse_rate(rate: str) -> tuple[int, float]:
    # e.g., "60/minute", "10/second"
    count, per = rate.split("/")
    n = int(count)
    window = {
        "second": 1.0,
        "sec": 1.0,
        "s": 1.0,
        "minute": 60.0,
        "min": 60.0,
        "m": 60.0,
        "hour": 3600.0,
        "h": 3600.0,
    }[per]
    return n, window


class TokenBucket:
    def __init__(self, capacity: int, refill_seconds: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_seconds = refill_seconds
        self.updated = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated
        self.updated = now
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.capacity / self.refill_seconds))
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_rate: str = "60/minute", key_fn: Optional[Callable[[Request], str]] = None, groups: Optional[dict[str, str]] = None):
        super().__init__(app)
        self.capacity, self.window = parse_rate(default_rate)
        self.buckets: dict[str, TokenBucket] = {}
        self.key_fn = key_fn or (lambda r: r.client.host if r.client else "unknown")
        # Path prefix -> rate string
        self.groups = groups or {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Pick group by longest matching prefix
        capacity = self.capacity
        window = self.window
        if self.groups:
            path = request.url.path
            match = ""
            for prefix, rate in self.groups.items():
                if path.startswith(prefix) and len(prefix) > len(match):
                    match = prefix
                    c, w = parse_rate(rate)
                    capacity, window = c, w

        # Include API key if present in Authorization HMAC header
        auth = request.headers.get("Authorization", "")
        kid = ""
        if auth.startswith("HMAC "):
            for part in auth[5:].split(','):
                part = part.strip()
                if part.startswith("keyId="):
                    kid = part.split("=", 1)[1]
                    break
        key = f"{self.key_fn(request)}|{kid}|{capacity}/{int(window)}"
        bucket = self.buckets.get(key)
        if bucket is None:
            bucket = self.buckets[key] = TokenBucket(capacity, window)

        if not bucket.allow():
            retry = 1
            return JSONResponse(
                {
                    "detail": "Rate limit exceeded",
                },
                status_code=429,
                headers={"Retry-After": str(retry), "X-RateLimit-Limit": str(capacity), "X-RateLimit-Remaining": "0"},
            )

        resp = await call_next(request)
        # Approximate remaining tokens (not exact across workers)
        resp.headers.setdefault("X-RateLimit-Limit", str(capacity))
        return resp
