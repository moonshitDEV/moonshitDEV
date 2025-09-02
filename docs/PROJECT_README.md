# moonshit.dev — Phase 1 Implementation (Scaffold)

Assumptions (applied by default):
- Single-node Ubuntu host with nginx and systemd.
- Backend binds `127.0.0.1:8000`; nginx terminates TLS and proxies `/api/`.
- Admin login is single-user; hash provided via env var.
- File storage lives under `/srv/dash-data/<user>/uploads` with `0700` perms.
- OpenAPI version pinned to `3.1.0`.

What’s included:
- Backend (FastAPI + Gunicorn): `backend/` with health, auth (cookie), files service, HMAC verifier stub, rate limiter, OpenAPI 3.1.
- Frontend (React + Tailwind): `frontend/` with theme tokens, basic shell (Dashboard/Files/Reddit/Login), SEO meta + JSON-LD.
- Ops: nginx site (`nginx/site-moonshit.dev`), systemd unit, env template, `setup.sh`, and `backend/nginx.md`.

Quick start (dev):
- Makefile helpers:
  - Setup: `make install` (creates `.venv/` and installs backend deps)
  - API: `make dev-api` (FastAPI on `127.0.0.1:8000` with reload)
  - Web: `make dev-ui` (Vite on `http://localhost:5173`, proxies `/api` → `127.0.0.1:8000`)
  - Both: `make dev` (API in background, UI in foreground)
  - Health: `make health` and OpenAPI: `make openapi`

If you prefer explicit commands:
- API: `python -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt && uvicorn app.main:app --app-dir backend --reload`
- Web: `cd frontend && pnpm i && pnpm dev` (or `npm install && npm run dev`).

Deploy:
- `sudo ./setup.sh` (idempotent; skips overwriting existing systemd/nginx by default), then edit `/etc/default/dash-api` (set `DASH_SECRET_KEY` and `DASH_ADMIN_PASS_HASH`),
- `sudo systemctl status dash-api && curl -fsSL http://127.0.0.1:8000/health`.

Ops helpers (Makefile):
- `make prod-status` — systemd status for `dash-api`.
- `make prod-restart` — restart API and reload nginx.
- `make prod-logs` — tail logs.

Overwrites
- To overwrite existing service/nginx files intentionally: `sudo ./setup.sh --force` (backs up with `.bak.<ts>`), or target a subset with `--force-service` or `--force-nginx`.

Next milestones:
- Wire Reddit typed endpoints + proxy registry with scopes and auditing.
- Add CSRF token for state-changing cookie flows.
- Add backups (SQLite + uploads rotation) and audit logs.
