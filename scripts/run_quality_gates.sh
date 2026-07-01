#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/backend/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

export PYTHONPATH="$ROOT_DIR/backend"
export APP_ENV="${APP_ENV:-test}"
export AUTH_JWT_SECRET="${AUTH_JWT_SECRET:-test-auth-secret-for-careeragent-p1}"
export DATA_ENCRYPTION_KEY="${DATA_ENCRYPTION_KEY:-MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew=}"
export DATA_ENCRYPTION_KEY_ID="${DATA_ENCRYPTION_KEY_ID:-quality-gate-test-v1}"

EVAL_OUTPUT_ROOT="${EVAL_OUTPUT_ROOT:-/tmp/careeragent-evals-v31}"
FRONTEND_BUILD_DIR="${FRONTEND_BUILD_DIR:-/tmp/careeragent-frontend-build-v31}"
COMPOSE_CONFIG_OUT="${COMPOSE_CONFIG_OUT:-/tmp/careeragent-prod-like-compose.yml}"

echo "== backend tests =="
"$PYTHON_BIN" -m pytest -p no:cacheprovider "$ROOT_DIR/backend/tests"

echo "== synthetic evals =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_evals.py" \
  --dataset synthetic \
  --output-dir "$EVAL_OUTPUT_ROOT/synthetic"

echo "== service-level evals =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_evals.py" \
  --dataset service_level \
  --output-dir "$EVAL_OUTPUT_ROOT/service_level"

echo "== frontend build =="
(
  cd "$ROOT_DIR/frontend"
  npm run build -- --outDir "$FRONTEND_BUILD_DIR"
)

echo "== docker compose config =="
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for the production-like compose gate." >&2
  exit 2
fi

GATE_DATA_KEY="$("$PYTHON_BIN" - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode("utf-8"))
PY
)"
EMPTY_ENV_FILE="$(mktemp)"
trap 'rm -f "$EMPTY_ENV_FILE"' EXIT

env \
  APP_ENV=production \
  BACKEND_CORS_ORIGINS=https://careeragent.example.com \
  AUTH_JWT_SECRET=quality-gate-auth-secret-with-more-than-32-random-chars \
  DATA_ENCRYPTION_KEY="$GATE_DATA_KEY" \
  DATA_ENCRYPTION_KEY_ID=quality-gate-v1 \
  POSTGRES_PASSWORD=quality-gate-postgres-password-with-more-than-32-chars \
  VITE_API_BASE_URL=/api \
  docker compose --env-file "$EMPTY_ENV_FILE" -f "$ROOT_DIR/docker-compose.prod-like.yml" config >"$COMPOSE_CONFIG_OUT"

if env -u AUTH_JWT_SECRET \
  APP_ENV=production \
  BACKEND_CORS_ORIGINS=https://careeragent.example.com \
  DATA_ENCRYPTION_KEY="$GATE_DATA_KEY" \
  DATA_ENCRYPTION_KEY_ID=quality-gate-v1 \
  POSTGRES_PASSWORD=quality-gate-postgres-password-with-more-than-32-chars \
  docker compose --env-file "$EMPTY_ENV_FILE" -f "$ROOT_DIR/docker-compose.prod-like.yml" config >/tmp/careeragent-compose-negative.log 2>&1; then
  echo "compose config unexpectedly passed without AUTH_JWT_SECRET." >&2
  exit 1
fi

echo "== alembic temp sqlite gate =="
TMP_DB="$(mktemp -t careeragent-alembic.XXXXXX.db)"
DATABASE_URL="sqlite:///$TMP_DB" "$PYTHON_BIN" -m alembic -c "$ROOT_DIR/backend/alembic.ini" upgrade head
rm -f "$TMP_DB"

echo "== diff/artifact/secret scans =="
git -C "$ROOT_DIR" diff --check

TRACKED_ARTIFACTS="$(git -C "$ROOT_DIR" ls-files | rg '(^|/)(dist|node_modules|__pycache__)(/|$)|\.pyc$|\.db$|\.sqlite3?$|evals/results/.+' | rg -v '^evals/results/\.gitkeep$' || true)"
if [[ -n "$TRACKED_ARTIFACTS" ]]; then
  echo "Tracked generated artifacts found:" >&2
  echo "$TRACKED_ARTIFACTS" >&2
  exit 1
fi

if git -C "$ROOT_DIR" grep -nE 'sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16}' -- ':!frontend/package-lock.json'; then
  echo "Potential committed secret pattern found." >&2
  exit 1
fi

echo "quality gates passed"
