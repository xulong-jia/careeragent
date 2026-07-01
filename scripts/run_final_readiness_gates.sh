#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/backend/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

OUTPUT_ROOT="${OUTPUT_ROOT:-/tmp/careeragent-final-readiness-gates}"
EVAL_ROOT="$OUTPUT_ROOT/evals"
FRONTEND_BUILD_DIR="$OUTPUT_ROOT/frontend-build"
PROVIDER_PROOF="$OUTPUT_ROOT/provider_proof.json"
DEPLOYMENT_PROOF="$OUTPUT_ROOT/deployment_proof.json"
AI_REPORT_DIR="$OUTPUT_ROOT/ai-quality-report"

rm -rf "$OUTPUT_ROOT"
mkdir -p "$EVAL_ROOT" "$AI_REPORT_DIR"

export PYTHONPATH="$ROOT_DIR/backend"
export APP_ENV="${APP_ENV:-test}"
export AUTH_JWT_SECRET="${AUTH_JWT_SECRET:-final-gate-local-auth-secret-with-more-than-32-chars}"
export DATA_ENCRYPTION_KEY="${DATA_ENCRYPTION_KEY:-MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew=}"
export DATA_ENCRYPTION_KEY_ID="${DATA_ENCRYPTION_KEY_ID:-final-gate-local-v1}"
export BACKEND_CORS_ORIGINS="${BACKEND_CORS_ORIGINS:-http://localhost:5173}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-final-gate-postgres-password-with-more-than-32-chars}"

echo "== git status =="
git -C "$ROOT_DIR" status -sb
git -C "$ROOT_DIR" rev-parse HEAD

echo "== backend tests =="
"$PYTHON_BIN" -m pytest -p no:cacheprovider "$ROOT_DIR/backend/tests"

echo "== eval: synthetic =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_evals.py" \
  --dataset synthetic \
  --output-dir "$EVAL_ROOT/synthetic"

echo "== eval: service_level =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_evals.py" \
  --dataset service_level \
  --output-dir "$EVAL_ROOT/service_level"

echo "== eval: benchmark =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_evals.py" \
  --dataset benchmark \
  --output-dir "$EVAL_ROOT/benchmark"

echo "== eval: anonymized_benchmark =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_evals.py" \
  --dataset anonymized_benchmark \
  --output-dir "$EVAL_ROOT/anonymized_benchmark"

echo "== AI provider validation =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/validate_ai_providers.py" \
  --output "$PROVIDER_PROOF"

echo "== AI quality certification report =="
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_ai_quality_certification.py" \
  --eval-dir "$EVAL_ROOT/anonymized_benchmark" \
  --provider-proof "$PROVIDER_PROOF" \
  --output-dir "$AI_REPORT_DIR"

echo "== frontend gates =="
(
  cd "$ROOT_DIR/frontend"
  npm run build -- --outDir "$FRONTEND_BUILD_DIR"
  npm run lint
  npm run typecheck
  npm run test
  npm run test:e2e
  npm run test:e2e:browser
)

echo "== docker compose config =="
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for final readiness compose gates." >&2
  exit 2
fi

AUTH_JWT_SECRET="$AUTH_JWT_SECRET" \
DATA_ENCRYPTION_KEY="$DATA_ENCRYPTION_KEY" \
docker compose -f "$ROOT_DIR/docker-compose.yml" config >"$OUTPUT_ROOT/docker-compose.local.yml"

AUTH_JWT_SECRET="$AUTH_JWT_SECRET" \
DATA_ENCRYPTION_KEY="$DATA_ENCRYPTION_KEY" \
docker compose -f "$ROOT_DIR/docker-compose.prod-like.yml" config >"$OUTPUT_ROOT/docker-compose.prod-like.yml"

if COMPOSE_DISABLE_ENV_FILE=1 env -u AUTH_JWT_SECRET \
  DATA_ENCRYPTION_KEY="$DATA_ENCRYPTION_KEY" \
  docker compose -f "$ROOT_DIR/docker-compose.yml" config >"$OUTPUT_ROOT/docker-compose.missing-secret.log" 2>&1; then
  echo "docker compose unexpectedly passed without AUTH_JWT_SECRET." >&2
  exit 1
fi

echo "== production deployment proof validation =="
APP_ENV=production \
AUTH_JWT_SECRET="$AUTH_JWT_SECRET" \
DATA_ENCRYPTION_KEY="$DATA_ENCRYPTION_KEY" \
DATA_ENCRYPTION_KEY_ID="$DATA_ENCRYPTION_KEY_ID" \
BACKEND_CORS_ORIGINS="$BACKEND_CORS_ORIGINS" \
POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
"$PYTHON_BIN" "$ROOT_DIR/scripts/validate_production_deployment.py" \
  --allow-local-placeholders \
  --strict \
  --output "$DEPLOYMENT_PROOF"

echo "== alembic temp DB =="
TMP_DB="$(mktemp -t careeragent-final-alembic.XXXXXX.db)"
DATABASE_URL="sqlite:///$TMP_DB" "$PYTHON_BIN" -m alembic -c "$ROOT_DIR/backend/alembic.ini" upgrade head
rm -f "$TMP_DB"

echo "== diff/artifact/secret scans =="
git -C "$ROOT_DIR" diff --check

TRACKED_FORBIDDEN="$(
  git -C "$ROOT_DIR" ls-files |
    grep -E '(^|/)(\.env|local_data|uploads|vector_index|\.db|dist|node_modules|evals/results|logs|backups|coverage|playwright-report|test-results)' |
    grep -Ev '(^|/)(\.env\.example|\.env\.production\.example|evals/results/\.gitkeep)$' ||
    true
)"
if [[ -n "$TRACKED_FORBIDDEN" ]]; then
  echo "Tracked forbidden artifacts found:" >&2
  echo "$TRACKED_FORBIDDEN" >&2
  exit 1
fi

git -C "$ROOT_DIR" check-ignore .env local_data uploads vector_index frontend/dist frontend/node_modules evals/results logs backups coverage playwright-report test-results || true
grep -R "sk-" "$ROOT_DIR" \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=dist \
  --exclude-dir=.venv \
  --exclude-dir=coverage \
  --exclude-dir=playwright-report \
  --exclude-dir=test-results \
  || true

echo "final readiness gates passed"
echo "outputs: $OUTPUT_ROOT"
