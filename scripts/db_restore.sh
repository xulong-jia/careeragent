#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required." >&2
  exit 2
fi

if [[ "$DATABASE_URL" == sqlite:* ]]; then
  echo "SQLite is local/dev only. Production restore requires PostgreSQL." >&2
  exit 2
fi

if [[ -z "${BACKUP_FILE:-}" ]]; then
  echo "BACKUP_FILE is required." >&2
  exit 2
fi

if [[ "${CONFIRM_RESTORE:-}" != "restore" ]]; then
  echo "Set CONFIRM_RESTORE=restore to run a destructive restore." >&2
  exit 2
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "pg_restore is required for PostgreSQL restores." >&2
  exit 2
fi

pg_restore --clean --if-exists --dbname "$DATABASE_URL" "$BACKUP_FILE"
