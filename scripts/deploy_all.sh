#!/usr/bin/env bash
set -euo pipefail

# Deploys frontend and restarts backend on the remote server.
#
# Env vars:
#   DEPLOY_HOST   user@host SSH target (required)
#   DEPLOY_PATH   target directory for frontend (default: /var/www/moonshit/current)
#
# Note: Assumes backend is already installed as systemd service 'dash-api'.
# If you deploy backend code by git pull on the server, uncomment the line below
# and set REPO_DIR to the server-side repo path.

export DEPLOY_PATH=${DEPLOY_PATH:-/var/www/moonshit/current}

"$(dirname "$0")/deploy_frontend.sh"

echo "Restarting backend service on $DEPLOY_HOST ..."
ssh "$DEPLOY_HOST" 'sudo systemctl restart dash-api'

echo "Deployment complete."

