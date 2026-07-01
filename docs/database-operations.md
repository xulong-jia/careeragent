# CareerAgent v3.1 Database Operations

CareerAgent production must run on PostgreSQL-compatible storage. SQLite remains local development/test only and is rejected when `APP_ENV=production`.

## Connection Policy

- Use `DATABASE_URL=postgresql+psycopg://...` from a secret manager or deployment environment.
- Do not commit database credentials.
- Configure pool settings with:
  - `DB_POOL_SIZE`
  - `DB_MAX_OVERFLOW`
  - `DB_POOL_TIMEOUT_SECONDS`
  - `DB_ECHO_SQL=false`
- `APP_ENV=production` rejects `DB_ECHO_SQL=true`.

## Migrations

```bash
DATABASE_URL=postgresql+psycopg://... scripts/db_migrate.sh
```

Dry run:

```bash
DATABASE_URL=postgresql+psycopg://... DRY_RUN=1 scripts/db_migrate.sh
```

Production readiness checks compare Alembic current revision with head revision. A production DB that is not at head must be treated as not ready.

## Backup

```bash
DATABASE_URL=postgresql+psycopg://... BACKUP_DIR=/secure/backups scripts/db_backup.sh
```

The script uses `pg_dump --format=custom` and writes `0600` backup files. It refuses SQLite because SQLite is not a production database path.

Operational requirements outside this repo:

- encrypted backup storage;
- restricted backup operator access;
- off-host replication or object storage;
- periodic restore drills;
- backup inventory with creation time, DB revision, app commit and retention deadline.

## Restore

Restore is destructive and requires explicit confirmation:

```bash
DATABASE_URL=postgresql+psycopg://... \
BACKUP_FILE=/secure/backups/careeragent-YYYYMMDDTHHMMSSZ.dump \
CONFIRM_RESTORE=restore \
scripts/db_restore.sh
```

Always restore to an isolated verification database first. Production restore should happen only after confirming the backup matches the intended commit/migration window.

## Rollback Strategy

CareerAgent v3.1 uses forward Alembic migrations. Do not rely on automatic downgrade in production.

Rollback plan:

1. Pause writes.
2. Snapshot current DB if safe.
3. Restore last known-good backup to isolated DB.
4. Start previous backend/frontend images against isolated DB.
5. Run `/ready`, auth smoke, privacy dry-run, and service-level eval smoke.
6. Promote isolated DB or restore production DB from the verified backup.

## pgvector Foundation

`docker-compose.prod-like.yml` uses `pgvector/pgvector:pg16` so the database can support v3.2 semantic/vector work. v3.1 does not switch the application RAG query path to pgvector; current RAG vectors remain database JSON/local foundation unless later v3.2 code explicitly changes that path.
