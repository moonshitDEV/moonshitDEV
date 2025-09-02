# Moonshit Dashboard API

- Framework: FastAPI (OpenAPI 3.1)
- Server: Gunicorn + UvicornWorker
- Bind: 127.0.0.1:8000 (nginx proxy)
- API root: `/api/v1`

## Endpoints
- `/health` — `{ "status": "ok" }`
- `/openapi.json` — OpenAPI 3.1 schema
- `/docs`, `/redoc` — interactive docs
- `/api/v1/auth/login`, `/logout`, `/me`
- `/api/v1/files/*` — list/upload/download/mkdir/rename/delete/zip
- `/api/v1/keys` — list, `POST /new`, `POST /revoke`
- `/api/v1/reddit/*` — typed Reddit endpoints + `/ops` + `/proxy`

## Security
- Sessions: signed cookie (`HttpOnly`, `Secure`, `SameSite=Lax`, 24h)
- Password hash: `argon2id`
- HMAC for programmatic clients (header format per TASK.md)
- Rate limiting: token-bucket per IP (app) + nginx `limit_req` (edge)
- CSRF: cookie flows must include `X-CSRF-Token` from `/api/v1/auth/csrf` for state-changing requests
- API keys: created with `POST /api/v1/keys/new` and returned once; server stores only hash and scopes

## Configuration
- Env vars prefixed `DASH_` (see `etc/default/dash-api.env.example`).
- Reddit creds: use `etc/default/reddit.env.sample` and export alongside your service environment. Provide per-profile variables:
  - `REDDIT_<PROFILE>_CLIENT_ID`, `REDDIT_<PROFILE>_CLIENT_SECRET`, `REDDIT_<PROFILE>_USER_AGENT`
  - Either `REDDIT_<PROFILE>_REFRESH_TOKEN` or `REDDIT_<PROFILE>_USERNAME` + `REDDIT_<PROFILE>_PASSWORD`
- Admin password hash: generate via `python -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('yourpass'))"` and set `DASH_ADMIN_PASS_HASH`.
- Upload root per user: `/srv/dash-data/<user>/uploads` (0700).
 - Upload policy: `DASH_UPLOAD_UNRESTRICTED=true` (default) disables mime/size checks. Set to `false` to enforce `DASH_UPLOAD_MAX_MB` and a safe MIME allowlist.

## Run (dev)
- `python -m venv .venv && . .venv/bin/activate`
- `pip install -r backend/requirements.txt`
- `uvicorn app.main:app --reload --app-dir backend`

## Deploy (prod)
- `sudo ./setup.sh` (copies backend, installs service, configures nginx)
- Edit `/etc/default/dash-api` with secrets.
- `sudo systemctl status dash-api && curl -fsSL http://127.0.0.1:8000/health`

## Ops Cheat Sheet
- `journalctl -u dash-api -f`
- `sudo nginx -t && sudo systemctl reload nginx`
- Backups: snapshot `/srv/dash-data` and DB (when added) to `/var/backups/dash/`.

## Notes
- Reddit endpoints implemented via PRAW; provide env vars `REDDIT_<PROFILE>_{CLIENT_ID,CLIENT_SECRET,REFRESH_TOKEN,USER_AGENT}` for each profile.
- RSS fallback engages on API failure for listings to maintain read-only visibility.
- All third-party imports include pip hints in comments.
