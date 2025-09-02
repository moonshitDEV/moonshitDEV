# Project Status — moonshit.dev Dashboard

This document summarizes the current state, what’s working, what’s broken/missing, and an ordered plan to make all features work end‑to‑end.

## Overview

- Stack: FastAPI backend (`/api/v1`), React/Tailwind frontend (static, served by nginx), nginx reverse proxy, systemd service for API.
- Auth: Session login (argon2id) with signed cookie + CSRF for state‑changing requests. Optional HMAC for API clients + API keys persisted in SQLite.
- Files: User‑scoped uploads under `DASH_DATA_ROOT/<user>/uploads`, list/upload/download/zip.
- Reddit: Comprehensive service layer ready (via PRAW/HTTPX) but UI not built; requires env tokens.

## Deployed State

- Domain: https://moonshit.dev/
- Frontend root: `/var/www/moonshit/current` (symlink to release dir).
- API: gunicorn/uvicorn on 127.0.0.1:8000, proxied by nginx.
- Health: `/health` returns `{ status: ok, db: ok }`.
- Docs: `/api/docs`, `/api/redoc`, `/api/openapi.json`.
- Login hero: `/login-hero.png` now present (live).

## What’s Working Now

- Login/logout: Session cookie, argon2id verify, CSRF token endpoint (`/api/v1/auth/csrf`), rate‑limited auth routes.
- Files API: List, mkdir, rename, delete, upload (single/multi), on‑the‑fly zipping and downloads; HMAC support for headless clients.
- API Keys: Issue/revoke/list; persisted in SQLite with encrypted secret at rest and hash for audit; HMAC verification supports replay/timestamp checks.
- OpenAPI/Routes: Route listing and filtered OpenAPI JSON generation via `/api/v1/ops/*`; used by UI API Explorer.
- Nginx: Proxies `/api/*`, serves static SPA, exposes health/docs with proper CSP; rate limits for sensitive paths.

## What’s Broken/Missing (User‑visible)

- Frontend features: Minimal UI only. “Files”, “API Keys”, and “API Explorer” exist, but need polish and robust error handling; “Reddit” is a placeholder.
- CSRF handling: UI handles it for Files/Keys, but errors are not surfaced clearly (e.g., lockout or 429 messages).
- Build artifact perms: Local `frontend/dist/` is root‑owned from a prior build; we worked around with `dist2`. Clean rebuild needed in CI/server.
- Reddit UI: No screens wired; requires env configuration (tokens per profile) and component work.
- Tests: No automated tests; only manual verification and a health probe.

## What’s Broken/Missing (Backend/infra)

- Rate‑limit/lockout UX: Login lockouts not communicated to UI; HMAC nonce cache is in‑memory (should be Redis with TTL in prod).
- Upload policy: `DASH_UPLOAD_UNRESTRICTED=true` allows any MIME/size within disk; policy toggles and MIME allowlist need to be exposed/admin‑configurable.
- Secrets lifecycle: API key verification falls back to decrypting secret with `DASH_SECRET_KEY`; ensure key rotation procedure/documentation.
- DB/backup: SQLite used for API keys; migration/backup plan not defined.
- CI/CD: No automated build/deploy; releases are manual.

## High‑Priority Fixes (to “make features work”)

1) Frontend polish and error surfacing
   - Show auth errors: invalid creds, 429 lockouts with countdown, CSRF failures.
   - Files: progress UI, empty states, failures; confirm zip/download flows; folder create/rename/delete UX.
   - Keys: show scopes clearly; copy helpers; revoke confirmation.

2) Reddit feature MVP (read‑only first)
   - Env: document and set `REDDIT_<PROFILE>_*` variables on server.
   - UI: profile selector; subreddit listing (new/hot/top), post details and comments (read‑only); fall back to RSS where PRAW creds missing.

3) Build/deploy hygiene
   - Clean `frontend/dist` ownership; standardize `npm run build` to write to `dist/`.
   - Add CI job to build UI and rsync to `/var/www/moonshit/releases/<ts>` then flip `current` symlink; no service restart required for static changes.

4) Rate‑limit clarity and resilience
   - UI: display “Locked. Retry in Ns” on 429; exponential backoff on retries.
   - Backend: optional Redis backend for HMAC nonce/lockouts (configurable, fallback to memory).

5) Security and config hardening
   - Rotate `DASH_SECRET_KEY` procedure documented; enforce non‑default in prod.
   - Optional: turn off `DASH_UPLOAD_UNRESTRICTED` in prod and define allowed MIME types.

## Next Feature Increments

- Reddit write actions: submit, comment, mod tools (already implemented server‑side); add UI and scope‑gated controls.
- Tasks domain: UI to trigger background tasks (scaffold present), with rate limiting and audit log.
- API tokens UX: show creation time, last used (add columns), and scope tooltips.
- Export/import: Zip selection and upload import of zips into folders.

## Operational Tasks

- Credentials: Admin is `shitadmin` with a known pass (see `/etc/default/dash-api`); rotate on handoff.
- Environment: Ensure `DASH_*` and `REDDIT_*` env vars set in `/etc/default/dash-api`; run `make prod-restart` to apply changes.
- Data paths: `DASH_DATA_ROOT` defaults to `/srv/dash-data` (0700 per user); ensure disk space and backup.
- Logs: `journalctl -u dash-api -f` for API; nginx logs for access/errors.

## How To Verify (Manual)

- Health: `curl https://moonshit.dev/health` → `{ status: ok }`.
- Login: use configured admin; confirm 401 on bad creds, 200 on success; test lockout after repeated failures.
- Files: list `/`, upload files and zip; download multiple as zip; test delete/rename; verify CSRF required on state changes.
- Keys: issue key with scopes; list keys; revoke and verify 404 on reuse; try HMAC auth to `/api/v1/files/list`.
- Docs: `/api/docs` loads under CSP; OpenAPI JSON downloads via UI “API Explorer”.

## Immediate Next Steps (Proposed Order)

1) Implement UI error handling and UX polish for Login/Files/Keys (fast wins).
2) Wire Reddit read‑only UI and document required env; verify RSS fallback without creds.
3) Fix build perms, add a `Makefile` target to build to `dist/` and a simple rsync deploy (already added `prod-deploy-frontend`).
4) Add Redis option (behind env) for HMAC nonce + lockout store; keep in‑memory fallback.
5) Document rotation procedures for admin password and `DASH_SECRET_KEY`.

## References

- Backend settings: `code/backend/app/settings.py`
- Auth/session/CSRF: `code/backend/app/security/{auth,csrf}.py`
- Files API: `code/backend/app/domains/files/router.py`
- Reddit services: `code/backend/app/domains/reddit/{router,services}.py`
- API keys/HMAC: `code/backend/app/domains/keys/router.py`, `code/backend/app/security/hmac.py`, `code/backend/app/db.py`
- Nginx site: `code/nginx/site-moonshit.dev`
- Make targets: `code/Makefile` (`prod-deploy-frontend`, `prod-deploy-all`)
