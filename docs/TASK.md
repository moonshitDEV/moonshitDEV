# moonshit.dev — Full Phase‑1 Blueprint (no code)




NOTES: The domain is moonshit.dev. ANy questions you must ask!


## 0) Objective
Personal dashboard with secure login, file explorer, and a Reddit control panel. Design matches the dark theme provided. Backend = FastAPI. Frontend = React/Tailwind. nginx fronts everything. OpenAPI **3.1.0** exposed.

---

## 1) Visual system (tokens)
- **Background** `#0F1117`; **Panels** `#151922`; **Card** `#1B2130`; **Borders** `#232B3A`
- **Text** primary `#E8ECF3`, secondary `#A2AEC3`, muted `#7B869C`
- **Accents** cyan `#2DD4FF`, magenta `#FF4D8D`, lime `#C7F23A`, yellow `#FFD84D`
- Radius: cards 12px, modals 16px. Soft single shadow.
- Fonts: Inter (UI), JetBrains Mono (numbers).

---

## 2) Architecture
- **Frontend** at `/` (built static assets).
- **Backend** at `/api/v1` (loopback bind `127.0.0.1:8000`).
- **nginx**: TLS, security headers, `limit_req` on sensitive routes.
- **Sessions**: cookie (`HttpOnly`, `Secure`, `SameSite=Lax`, 24h). CSRF on state‑changing routes.
- **API access for external clients**: HMAC keys with scopes.
- **Secrets**: `.env` for local dev; server secrets in `/etc/default/dash-api`.

---

## 3) Auth & Keys
- **Login**: single user v1. Hash = `argon2id`. Backoff + temp lock after failed attempts. IP + account rate limits.
- **API HMAC** (for non‑browser clients):
  - Header: `Authorization: HMAC keyId=<id>, ts=<unix>, nonce=<uuid>, sig=<base64(hmac_sha256(secret, method|path|ts|nonce|sha256(body)))>`
  - Scopes per key (`reddit:read`, `reddit:write`, `files:read`, etc). Replay defense on `ts/nonce`.
- **Cookie vs HMAC**: cookie for web UI, HMAC for programmatic access.

---

## 4) Files service (explorer)
- Root: `/srv/dash-data/<user>/uploads/` (0700). Normalize paths. MIME allowlist. Size limit default 50MB.
- Endpoints (all under `/api/v1`):
  - `GET  /files/list?path=/` → `[ {name,type,bytes,mtime} ]`
  - `POST /files/upload?path=/subdir` (multipart) → `{stored, sha256}`
  - `GET  /files/download?path=/...` (supports `Range`)
  - `POST /files/mkdir` `{path}`
  - `POST /files/rename` `{from,to}`
  - `DELETE /files?path=/...`
- UI: folder icon opens modal with tree + table, drag‑drop upload.

---

## 5) Reddit service — typed endpoints (explicit)
**Profiles**: `lexdata859` → default `r/newsoflexingtonky`, `moonshitDEV` → default `r/moonshitDEV`. Profile selected via header toggle or path param. All endpoints require session or HMAC scope.

### Read (subs, listings, search)
- `GET  /reddit/{profile}/me`
- `GET  /reddit/{profile}/subs?modonly=true|false&after=&limit=`
- `GET  /reddit/{profile}/r/{sub}/about`
- `GET  /reddit/{profile}/r/{sub}/rules`
- `GET  /reddit/{profile}/r/{sub}/wiki/{path}`
- `GET  /reddit/{profile}/r/{sub}/{sort}?after=&t=` where `{sort} ∈ new|hot|top|rising|controversial`
- `GET  /reddit/{profile}/search?q=&sub=&type=link|comment|sr`
- `GET  /reddit/{profile}/comments/{post_id}` (thread + context)

### Write posts & comments
- `POST /reddit/{profile}/r/{sub}/submit`  
  Body: `{kind:self|link|media, title, text?, url?, nsfw?, spoiler?, flair?}`
- `POST /reddit/{profile}/comment`  
  Body: `{parent_id, text}` (new comment or reply)
- `POST /reddit/{profile}/edit`  
  Body: `{thing_id, text}` (edit post or comment)
- `POST /reddit/{profile}/delete`  
  Body: `{thing_id}`
- `POST /reddit/{profile}/vote`  
  Body: `{thing_id, dir: 1|0|-1}`
- `POST /reddit/{profile}/save` / `POST /reddit/{profile}/unsave`  
  Body: `{thing_id}`
- **Media**: `POST /reddit/{profile}/media/asset` → returns media id for later submit.

### Moderation (read & write)
- **Read queues**:
  - `GET /reddit/{profile}/r/{sub}/modqueue`
  - `GET /reddit/{profile}/r/{sub}/reports`
  - `GET /reddit/{profile}/r/{sub}/spam`
  - `GET /reddit/{profile}/r/{sub}/edited`
  - `GET /reddit/{profile}/r/{sub}/unmoderated`
  - `GET /reddit/{profile}/r/{sub}/mod/log` (modlog)
- **Actions**:
  - `POST /reddit/{profile}/mod/approve` `{thing_id}`
  - `POST /reddit/{profile}/mod/remove` `{thing_id, spam?:bool}`
  - `POST /reddit/{profile}/mod/lock` / `unlock` `{thing_id}`
  - `POST /reddit/{profile}/mod/sticky` `{thing_id, state:bool}`
  - `POST /reddit/{profile}/mod/distinguish` `{thing_id, how:yes|no|admin|special}`
  - `POST /reddit/{profile}/mod/ban` / `unban` `{user, sub, reason?, days?}`
  - `POST /reddit/{profile}/r/{sub}/flair/user` `{user, flair_text?, flair_template_id?}`
  - `POST /reddit/{profile}/r/{sub}/flair/link` `{thing_id, flair_text?, flair_template_id?}`
  - `POST /reddit/{profile}/r/{sub}/set_suggested_sort` `{thing_id, sort}`

### Messaging / inbox
- `GET  /reddit/{profile}/inbox?type=all|unread&after=&limit=`
- `POST /reddit/{profile}/message` `{to, subject, text}`

### Universal proxy (full surface coverage)
- `POST /reddit/{profile}/proxy` → `{ namespace, operation, params }`
  - Backed by allowlisted registry of PRAW/Reddit ops. JSON‑Schema validated. Per‑op rate caps. Response clamp. Audit log.
- Discovery:
  - `GET /reddit/ops` (list allowed ops)
  - `GET /reddit/ops/{namespace}/{operation}` (param schema + notes)

---

## 6) Reddit dashboard UX
- Header toggle selects active profile; persisted.
- **On load**: show the active profile’s default subreddit listing (`new` by default).
- **Go to subreddit**: input supports any `r/<name>`; history dropdown. Switches view instantly.
- **Compose**: Markdown editor with preview; flags (NSFW, spoiler, flair). Validates subreddit rules before submit.
- **Moderation**: dedicated Mod Queue view with bulk approve/remove and quick filters (reports/spam/edited/unmod).
- **RSS fallback (read‑only)**: if API is unavailable, read `https://www.reddit.com/r/<sub>/.rss` server‑side and render items; clearly marked as read‑only.

---

## 7) OpenAPI & privacy
- **OpenAPI**: `/openapi.json` with `openapi: "3.1.0"` and JSON Schema 2020‑12 components. `/docs` and `/redoc` enabled.
- **SecuritySchemes**: `cookieAuth`, `hmacAuth`, optional `apiKeyAuth` (local‑only).
- **Privacy page** (content): what is stored (username, hash, sessions, API keys, rate counters, file metadata, encrypted Reddit tokens), what is not, locations, retention, your controls (revoke keys, logout all, unlink Reddit, delete files).

---

## 8) Security & rate limits
- nginx `limit_req` on `/auth/*`, `/files/upload`, `/reddit/*/submit`, `/reddit/*/proxy`.
- App token buckets per route group and per API key. Return `X‑RateLimit‑*` and `Retry‑After` on 429.
- CORS locked to your origin. CSRF on cookie flows. Input validation everywhere.
- Token storage encrypted at rest. Least‑privilege file perms.

---

## 9) Extensibility & efficiency
- **Versioned API**: `/api/v1` now; reserve `/api/v2` for breaks.
- **By‑feature folders**: `domains/files`, `domains/reddit`, `domains/tasks`, etc.
- **Auto router include**: new feature = drop `router.py` and it registers.
- **Plugin hook**: `plugins/` with `register(app)` for third‑party features.
- **Scaffold scripts**:
  - `scripts/new_feature.sh <name>` → backend skeleton
  - `scripts/new_endpoint.sh <feature> <verb> <path>` → route + schema stubs
  - `pnpm gen:feature <name>` → frontend route + nav stub
  - `pnpm gen:api` → regenerate TS client from OpenAPI
- **Scopes** per feature: `<feat>:read|write|admin` applied to cookie/HMAC.

---

## 10) Observability & backups
- `/health` shows `{status:"ok"}` and DB probe status when configured.
- Logs: nginx access/error; app audit for write/mod actions and proxy calls.
- Backups: nightly SQLite `.backup` to `/var/backups/dash/` (7 daily, 4 weekly). Include uploads with rotation.

---

## 11) nginx & deployment
- `location /` → frontend build.  
- `location /api/` → `http://127.0.0.1:8000/` with headers.  
- TLS via certbot. Zero‑downtime static deploy by versioned build dir + symlink swap.

---

## 12) Environment (no secrets in repo)
- **Dashboard**: `DASH_ENV`, `DASH_SECRET_KEY`, `DASH_RATE_DEFAULT`, `DASH_UPLOAD_MAX_MB`.
- **Auth**: `DASH_ADMIN_USER`, `DASH_ADMIN_PASS_HASH`.
- **API Keys**: managed at runtime; stored hashed; export via admin endpoints.
- **Reddit** (two script apps): for each profile → `REDDIT_<PROFILE>_CLIENT_ID`, `REDDIT_<PROFILE>_CLIENT_SECRET`, `REDDIT_<PROFILE>_REFRESH_TOKEN` (encrypted at rest), `REDDIT_<PROFILE>_USER_AGENT`.

---

## 13) Milestones
- **Day 0**: repos, theme tokens, env layout, nginx site, acceptance tests list.
- **Day 1**: auth + files + OpenAPI 3.1; frontend shell with explorer.
- **Day 2**: Reddit typed endpoints + proxy + UI (toggle, listing, compose, mod queue); RSS fallback.

---

## 14) Acceptance criteria
- Login is resistant to brute force; lockout works; logs record attempts.
- OpenAPI 3.1 published; client types can be generated.
- File explorer lists/uploads/downloads with limits; path traversal blocked.
- Reddit: can read any subreddit; post and comment; vote/save; perform mod actions where permitted; search works.
- Proxy advertises full op registry; non‑allowlisted ops rejected with guidance.
- RSS fallback renders when API unavailable.
- Privacy page live and accurate.

---

## 15) Risks & decisions to lock now
- Hasher = **argon2id**. Session store = cookie v1; Redis optional later.
- Upload cap default = 50MB; MIME allowlist text/images/pdf/zip. Executables blocked.
- Reddit proxy enabled with strict allowlist + audit. Clear scopes for HMAC keys.

---

## 16) Quick ops checklist
- `sudo nginx -t && sudo systemctl reload nginx`
- `journalctl -u dash-api.service -f`
- `curl -fsSL http://127.0.0.1:8000/health`

> This document is the build contract for Phase‑1. No code here; implementation follows this map exactly.
