#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/backend/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required." >&2
  exit 2
fi

export PYTHONPATH="$ROOT_DIR/backend"
TARGET_REVISION="${TARGET_REVISION:-head}"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  "$PYTHON_BIN" -m alembic -c "$ROOT_DIR/backend/alembic.ini" current
  "$PYTHON_BIN" -m alembic -c "$ROOT_DIR/backend/alembic.ini" heads
  exit 0
fi

"$PYTHON_BIN" -m alembic -c "$ROOT_DIR/backend/alembic.ini" upgrade "$TARGET_REVISION"
