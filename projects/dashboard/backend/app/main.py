from __future__ import annotations

# pip install fastapi uvicorn[standard] pydantic-settings orjson
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .settings import get_settings
from .security.rate_limit import RateLimitMiddleware
from .security.csrf import CSRFMiddleware, router as csrf_router
from .db import init_db
from .domains.auth.router import router as auth_router
from .domains.files.router import router as files_router
from .domains.reddit.router import router as reddit_router
from .domains.keys.router import router as keys_router
from .domains.tasks.router import router as tasks_router
from .domains.ops.router import router as ops_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Moonshit Dashboard API",
        version="0.1.0",
        summary="Personal dashboard backend for moonshit.dev",
        default_response_class=ORJSONResponse,
        openapi_version="3.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS (locked if origin provided)
    if settings.cors_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.cors_origin],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["*"],
        )

    # Simple token-bucket rate limiter per IP with path groups
    groups = {
        f"{settings.api_root}/auth": "10/minute",
        f"{settings.api_root}/files/upload": "5/minute",
        f"{settings.api_root}/reddit": "30/minute",
    }
    app.add_middleware(RateLimitMiddleware, default_rate=settings.rate_default, groups=groups)

    # CSRF protection for cookie session flows
    app.add_middleware(CSRFMiddleware)

    # Health probe (DB hook can be added later)
    @app.get("/health", tags=["ops"])  # not under /api for convenience
    def health():
        ok = True
        db = "unknown"
        try:
            from .db import get_conn
            c = get_conn()
            c.execute("SELECT 1")
            c.close()
            db = "ok"
        except Exception:
            ok = False
            db = "error"
        return {"status": "ok" if ok else "degraded", "db": db}

    # DB init
    init_db()

    # API routers
    api = settings.api_root.rstrip("/")
    app.include_router(auth_router, prefix=api)
    app.include_router(csrf_router, prefix=api)
    app.include_router(files_router, prefix=api)
    app.include_router(reddit_router, prefix=api)
    app.include_router(keys_router, prefix=api)
    app.include_router(tasks_router, prefix=api)
    app.include_router(ops_router, prefix=api)

    # OpenAPI security schemes
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.summary,
            routes=app.routes,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).update(
            {
                "cookieAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "dash_session",
                },
                "hmacAuth": {
                    "type": "http",
                    "scheme": "hmac-sha256",
                    "description": "HMAC header: Authorization: HMAC keyId=<id>, ts=<unix>, nonce=<uuid>, sig=<base64>"
                },
            }
        )
        schema["security"] = [
            {"cookieAuth": []},
            {"hmacAuth": []},
        ]
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[assignment]

    return app


# Entrypoint for `uvicorn app.main:app`
app = create_app()
