PY ?= python3
VENV := .venv
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help venv install install-backend ui-install dev-api dev-ui dev cp-env openapi health clean prod-status prod-restart prod-logs prod-build-frontend prod-deploy-frontend prod-deploy-all

help:
	@echo "Targets:"
	@echo "  venv           Create local Python venv at $(VENV)"
	@echo "  install        Create venv and install backend deps"
	@echo "  dev-api        Run FastAPI dev server with reload (127.0.0.1:8000)"
	@echo "  ui-install     Install frontend deps (npm/pnpm/yarn)"
	@echo "  dev-ui         Run Vite dev server (http://localhost:5173)"
	@echo "  dev            Run API and UI (UI foreground)"
	@echo "  cp-env         Copy env.sample to .env if missing"
	@echo "  openapi        Download OpenAPI JSON from dev API to openapi.json"
	@echo "  health         Curl API health endpoint"
	@echo "  clean          Remove venv and build artifacts"
	@echo "  prod-status    systemd status for dash-api (sudo)"
	@echo "  prod-restart   Restart dash-api and reload nginx (sudo)"
	@echo "  prod-logs      Tail dash-api journal (sudo)"
	@echo "  prod-build-frontend  Build UI into frontend/dist2 (no root perms needed)"
	@echo "  prod-deploy-frontend Deploy UI to server via rsync (requires DEPLOY_HOST)"
	@echo "  prod-deploy-all      Deploy UI and reload services on server"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(PIP) install --upgrade pip wheel >/dev/null

install: venv install-backend

install-backend:
	@$(PIP) install -r $(BACKEND_DIR)/requirements.txt

dev-api: venv
	@echo "Starting API on 127.0.0.1:8000 (reload)"
	@$(UVICORN) app.main:app --app-dir $(BACKEND_DIR) --host 127.0.0.1 --port 8000 --reload

ui-install:
	@if command -v pnpm >/dev/null 2>&1; then \
	  (cd $(FRONTEND_DIR) && pnpm i); \
	elif command -v yarn >/dev/null 2>&1; then \
	  (cd $(FRONTEND_DIR) && yarn install); \
	else \
	  (cd $(FRONTEND_DIR) && npm install); \
	fi

dev-ui:
	@cd $(FRONTEND_DIR) && npm run dev

# Convenience: start API in background and then UI in foreground
dev: venv ui-install
	@$(UVICORN) app.main:app --app-dir $(BACKEND_DIR) --host 127.0.0.1 --port 8000 --reload & \
	API_PID=$$!; \
	trap 'kill $$API_PID' INT TERM EXIT; \
	cd $(FRONTEND_DIR) && npm run dev

cp-env:
	@([ -f .env ] || cp -n env.sample .env) && echo ".env ready"

openapi:
	@curl -fsS http://127.0.0.1:8000/openapi.json -o openapi.json && echo "Saved openapi.json"

health:
	@curl -fsS http://127.0.0.1:8000/health && echo

clean:
	@rm -rf $(VENV) $(FRONTEND_DIR)/dist openapi.json
	@echo "Cleaned"

prod-status:
	@sudo systemctl status dash-api --no-pager -l || true

prod-restart:
	@sudo systemctl restart dash-api && sudo systemctl reload nginx && echo "dash-api restarted; nginx reloaded"

prod-logs:
	@sudo journalctl -u dash-api -f -n 200

# Production helpers
prod-build-frontend:
	@cd $(FRONTEND_DIR) && npm run build -- --outDir dist2

# Usage: make prod-deploy-frontend DEPLOY_HOST=user@host [DEPLOY_PATH=/var/www/moonshit/current]
prod-deploy-frontend: prod-build-frontend
	@DEPLOY_PATH=$${DEPLOY_PATH:-/var/www/moonshit/current}; \
	rsync -avz --delete frontend/dist2/ $$DEPLOY_HOST:$$DEPLOY_PATH/

# Usage: make prod-deploy-all DEPLOY_HOST=user@host [DEPLOY_PATH=/var/www/moonshit/current]
prod-deploy-all: prod-deploy-frontend
	@ssh $$DEPLOY_HOST 'sudo nginx -t && sudo systemctl reload nginx && sudo systemctl restart dash-api'
