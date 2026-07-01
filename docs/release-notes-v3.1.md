# CareerAgent v3.1 Production Deployment, Database & Operations Foundation

v3.1 moves CareerAgent from v3.0 security/privacy/data-governance foundation toward production-like operations. It is a production deployment/database/operations foundation candidate, not production-ready certification.

## Added

- `docker-compose.prod-like.yml` with PostgreSQL/pgvector, backend readiness healthcheck and nginx-hosted frontend build.
- `.env.production.example` as a private production env template.
- `frontend/Dockerfile.production` and `frontend/nginx.conf`.
- DB pool config and production validation for `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS` and `DB_ECHO_SQL=false`.
- `/live` and `/api/live`.
- Enhanced `/ready` and `/api/ready` with storage writability, Alembic current/head and provider/vector summaries.
- `/metrics` and `/api/metrics` with HTTP counters and Agent/Eval/RAG run counts.
- Structured non-sensitive run logs for Agent, Evaluation and RAG operations.
- `scripts/db_migrate.sh`, `scripts/db_backup.sh`, `scripts/db_restore.sh` and `scripts/run_quality_gates.sh`.
- Production deployment, database operations, operations monitoring, data governance and retention/backup runbooks.

## Boundaries

- SQLite remains local dev/test only.
- pgvector is available in the deployment profile, but the application RAG query path remains local/database JSON foundation until v3.2.
- `/metrics` is a foundation JSON snapshot, not a full Prometheus/OpenTelemetry/SIEM integration.
- Backup purge is documented as a production policy, not automated by this repo.
- v3.1 does not change AI quality, model providers, parser semantics, reranking or frontend productization.

## Required Gates

Run:

```bash
scripts/run_quality_gates.sh
```

The script covers backend tests, synthetic/service-level evals, frontend build, production-like compose config positive/negative checks, Alembic temp DB migration, diff check and artifact/secret scans.

Only v3.4 final read-only audit can decide whether a production-ready candidate tag is allowed.
