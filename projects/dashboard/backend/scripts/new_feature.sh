#!/usr/bin/env bash
set -euo pipefail

name=${1:-}
if [[ -z "$name" ]]; then
  echo "Usage: $0 <feature-name>" >&2
  exit 1
fi

base="backend/app/domains/$name"
mkdir -p "$base"
cat > "$base/router.py" <<'PY'
from fastapi import APIRouter

router = APIRouter(prefix="/%s", tags=["%s"])  # fill in

# Add endpoints here
PY

touch "$base/__init__.py"
echo "Created feature skeleton at $base"

