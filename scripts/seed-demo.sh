#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root/apps/api"
: "${APP_ENV:?Set APP_ENV=development or test explicitly}"
if [[ "$APP_ENV" != development && "$APP_ENV" != test ]]; then echo 'Demo seed requires a non-production target'; exit 1; fi
.venv/bin/alembic upgrade head
PYTHONPATH="$repo_root/apps/api" .venv/bin/python "$repo_root/demo/seed.py" --environment demo "$@"
