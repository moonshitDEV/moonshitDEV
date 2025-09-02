#!/usr/bin/env bash
set -euo pipefail

# Deploys the built frontend to a remote server using rsync, then reloads nginx.
#
# Env vars:
#   DEPLOY_HOST   user@host SSH target (required)
#   DEPLOY_PATH   target directory on server (default: /var/www/moonshit/current)
#
# This script builds into frontend/dist2 to avoid local permissions on dist/.

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here/frontend"

if [[ -z "${DEPLOY_HOST:-}" ]]; then
  echo "DEPLOY_HOST is required (e.g., user@moonshit.dev)" >&2
  exit 2
fi

DEPLOY_PATH=${DEPLOY_PATH:-/var/www/moonshit/current}

echo "Building frontend (outDir=dist2)..."
npm run build -- --outDir dist2

echo "Rsync to $DEPLOY_HOST:$DEPLOY_PATH ..."
rsync -avz --delete dist2/ "$DEPLOY_HOST:$DEPLOY_PATH/"

echo "Reloading nginx..."
ssh "$DEPLOY_HOST" 'sudo nginx -t && sudo systemctl reload nginx'

echo "Done."

