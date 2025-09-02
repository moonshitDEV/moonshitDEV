#!/usr/bin/env bash
set -euo pipefail

# Setup backend service and nginx site for moonshit.dev

# Flags: --force, --force-service, --force-nginx
FORCE_SERVICE=0
FORCE_NGINX=0
for arg in "$@"; do
  case "$arg" in
    --force)
      FORCE_SERVICE=1; FORCE_NGINX=1;;
    --force-service)
      FORCE_SERVICE=1;;
    --force-nginx)
      FORCE_NGINX=1;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)." >&2
  exit 1
fi

APP_DIR=/opt/moonshit/backend
SITE_CONF=/etc/nginx/sites-available/moonshit.dev
SITE_LINK=/etc/nginx/sites-enabled/moonshit.dev
ENV_FILE=/etc/default/dash-api
REDDIT_ENV_FILE=/etc/default/dash-reddit
LIMITS_CONF=/etc/nginx/conf.d/limit_zones.conf
WWW_DIR=/var/www/moonshit
VAR_LIB=/var/lib/dash

mkdir -p "$APP_DIR"
rsync -a backend/ "$APP_DIR"/

python3 -m venv /opt/moonshit/venv || true
/opt/moonshit/venv/bin/pip install --upgrade pip
/opt/moonshit/venv/bin/pip install -r "$APP_DIR/requirements.txt"

UNIT_PATH=/etc/systemd/system/dash-api.service
if [[ -f "$UNIT_PATH" && $FORCE_SERVICE -eq 0 ]]; then
  echo "systemd unit exists at $UNIT_PATH — skipping (use --force-service to overwrite)"
else
  if [[ -f "$UNIT_PATH" ]]; then cp -a "$UNIT_PATH"{,.bak.$(date +%s)}; fi
  install -m 644 backend/systemd/dash-api.service "$UNIT_PATH"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  install -m 640 backend/etc/default/dash-api.env.example "$ENV_FILE"
  echo "Wrote $ENV_FILE (edit secrets!)"
fi

if [[ ! -f "$REDDIT_ENV_FILE" ]]; then
  install -m 640 backend/etc/default/reddit.env.sample "$REDDIT_ENV_FILE"
  echo "Wrote $REDDIT_ENV_FILE (populate Reddit credentials per profile)"
fi

if [[ -f "$SITE_CONF" && $FORCE_NGINX -eq 0 ]]; then
  echo "nginx site exists at $SITE_CONF — skipping (use --force-nginx to overwrite)"
else
  if [[ -f "$SITE_CONF" ]]; then cp -a "$SITE_CONF"{,.bak.$(date +%s)}; fi
  install -m 644 nginx/site-moonshit.dev "$SITE_CONF"
fi

[[ -L "$SITE_LINK" ]] || ln -s "$SITE_CONF" "$SITE_LINK"

if [[ -f "$LIMITS_CONF" && $FORCE_NGINX -eq 0 ]]; then
  echo "nginx conf.d exists at $LIMITS_CONF — skipping (use --force-nginx to overwrite)"
else
  if [[ -f "$LIMITS_CONF" ]]; then cp -a "$LIMITS_CONF"{,.bak.$(date +%s)}; fi
  install -m 644 nginx/conf.d/limit_zones.conf "$LIMITS_CONF"
fi

mkdir -p /srv/dash-data
chown -R www-data:www-data /srv/dash-data || true
mkdir -p "$VAR_LIB" && chown -R www-data:www-data "$VAR_LIB"

# Build frontend if Node/npm available
if command -v npm >/dev/null 2>&1; then
  pushd frontend >/dev/null
  npm ci || npm install
  npm run build
  popd >/dev/null
  ts=$(date +%Y%m%d%H%M%S)
  mkdir -p "$WWW_DIR/releases/$ts"
  rsync -a frontend/dist/ "$WWW_DIR/releases/$ts"/
  ln -sfn "$WWW_DIR/releases/$ts" "$WWW_DIR/current"
  chown -R www-data:www-data "$WWW_DIR"
fi

systemctl daemon-reload
systemctl enable --now dash-api

nginx -t && systemctl reload nginx

echo "Setup complete. Health: curl -fsSL http://127.0.0.1:8000/health"
