#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required." >&2
  exit 2
fi

if [[ "$DATABASE_URL" == sqlite:* ]]; then
  echo "SQLite is local/dev only. Use PostgreSQL pg_dump for production backups." >&2
  exit 2
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump is required for PostgreSQL backups." >&2
  exit 2
fi

mkdir -p "$BACKUP_DIR"
OUTPUT_FILE="${OUTPUT_FILE:-$BACKUP_DIR/careeragent-$(date -u +%Y%m%dT%H%M%SZ).dump}"
pg_dump "$DATABASE_URL" --format=custom --file="$OUTPUT_FILE"
chmod 600 "$OUTPUT_FILE"
echo "$OUTPUT_FILE"
