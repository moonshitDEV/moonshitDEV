## nginx for moonshit.dev

Files:
- `nginx/site-moonshit.dev` — primary site config (HTTPS + headers + limits)

Key points:
- TLS via certbot managed certs under `/etc/letsencrypt/live/moonshit.dev/`.
- Frontend served at `/var/www/moonshit/current` with SPA fallback.
- Backend proxied at `/api/` to `127.0.0.1:8000` (Gunicorn/Uvicorn).
- Security headers enabled; strict CSP tuned for SPA.
- `limit_req` buckets for login, uploads, and sensitive Reddit endpoints.

Commands:
- Test: `sudo nginx -t`
- Reload: `sudo systemctl reload nginx`

Install notes:
- `setup.sh` skips overwriting existing nginx files by default to avoid duplicates.
- Use `sudo ./setup.sh --force-nginx` to overwrite site or conf.d files (it creates a timestamped `.bak`).
