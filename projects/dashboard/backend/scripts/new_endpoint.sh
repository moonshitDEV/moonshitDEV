#!/usr/bin/env bash
set -euo pipefail

feature=${1:-}
verb=${2:-}
path=${3:-}
if [[ -z "$feature" || -z "$verb" || -z "$path" ]]; then
  echo "Usage: $0 <feature> <verb> <path>" >&2
  exit 1
fi

file="backend/app/domains/$feature/router.py"
if [[ ! -f "$file" ]]; then
  echo "Feature $feature not found. Run new_feature.sh first." >&2
  exit 1
fi

cat >> "$file" <<PY

@router.${verb}("${path}")
def todo_${verb}_$(echo "$path" | tr -cd '[:alnum:]' )():
    return {"todo": "implement ${verb} ${path}"}
PY

echo "Added endpoint ${verb} ${path} to ${file}"

