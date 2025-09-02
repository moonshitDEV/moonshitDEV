#!/usr/bin/env bash
set -euo pipefail
curl -fsSL http://127.0.0.1:8000/health | jq .

