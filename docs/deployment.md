# CareerAgent Deployment Baseline

This is a security/privacy/deployment/operations production foundation for local development, production-like deployment checks and repeatable gates. It is not production-readiness certification and does not make CareerAgent production-ready.

## Local Docker Compose

```bash
cp .env.example .env
docker compose build
docker compose up
```

Default Compose uses:

- SQLite at `backend/local_data/careeragent.db`
- deterministic LLM provider
- local embedding provider
- local vector store setting
- lexical RAG retrieval mode
- P1 token auth with a required `AUTH_JWT_SECRET`

No real AI provider key is required. `AUTH_JWT_SECRET` is still required because business APIs are protected by bearer token auth.

The checked-in `.env.example` contains a dev-only placeholder:

```bash
AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars
```

This is only for local development. Do not commit `.env`. Do not use the dev-only value in production.

`docker-compose.yml` intentionally rejects an empty secret:

```bash
docker compose config
```

Run that command after copying `.env.example` to `.env`, or provide a local secret explicitly:

```bash
AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars docker compose config
```

## Production-like Compose

v3.1 adds a production-like profile with PostgreSQL/pgvector, backend probes and nginx-hosted frontend build:

```bash
cp .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod-like.yml config
docker compose --env-file .env.production -f docker-compose.prod-like.yml build
docker compose --env-file .env.production -f docker-compose.prod-like.yml up -d
```

`.env.production.example` is a template only. Real values must come from a secret manager or private deployment environment.

## Health / Readiness / Metrics

```bash
curl http://localhost:8000/live
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
```

The health response exposes provider modes and feature flags, but not API keys or database credentials. The readiness response checks DB reachability, runtime config validity, local storage writability and Alembic current/head status, and returns only masked config summary. The metrics response exposes non-secret HTTP counters and Agent/Eval/RAG run counts.

## Auth Secret Rules

- Local dev may use the `.env.example` dev-only secret.
- Production must inject a strong random `AUTH_JWT_SECRET` through a secret manager or deployment environment.
- `APP_ENV=production` rejects short secrets and dev-only / replace-me / change-me / placeholder secrets.
- Missing `AUTH_JWT_SECRET` must fail loudly instead of creating a silently unusable auth path.

## Production Database Rule

SQLite is local development only. With `APP_ENV=production`, startup rejects SQLite-style `DATABASE_URL` values such as:

```bash
DATABASE_URL=sqlite:///./local_data/careeragent.db
```

Production must use a PostgreSQL-compatible URL injected by the deployment environment:

```bash
DATABASE_URL=postgresql+psycopg://...
```

v3.1 provides `scripts/db_migrate.sh`, `scripts/db_backup.sh`, `scripts/db_restore.sh`, `docs/database-operations.md` and `docs/retention-backup-policy.md`. Managed PostgreSQL, encrypted backup storage, restore jobs and purge attestation remain deployment responsibilities.

## Logging and Readiness

- Request logs are JSON events from the `careeragent` logger.
- Request logs include request_id, method, path, status_code and duration_ms.
- Request logs do not include request body, Authorization header, raw_text, chunk text, answer text or provider payloads.
- Error responses redact sensitive details before returning them.
- `/ready` and `/api/ready` are public readiness endpoints for deployment checks.

## Real Provider Opt-In

Set these only in local `.env` or a trusted secret manager:

```bash
ENABLE_REAL_LLM=true
LLM_PROVIDER=openai_compatible
LLM_API_BASE_URL=
LLM_API_KEY=
LLM_MODEL=

ENABLE_REAL_EMBEDDING=true
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
```

Before switching real providers on, run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
python3 scripts/run_evals.py --dataset smoke
```

The smoke eval is synthetic contract regression only. Phase 2.1 adds `service_level` evaluation, which uses de-identified sample sets and runner paths that call the actual current service/retriever/parser/agent implementations.

## v3.1 Operations Gates

Run the aggregate gate:

```bash
scripts/run_quality_gates.sh
```

It runs backend tests, synthetic/service-level evals, frontend build, production-like compose config positive/negative checks, Alembic temp DB migration, diff check, artifact scan and secret scan.

## Production Limits

Current v3.1 has token auth, workspace scope, token revoke, route-level RBAC gate, privacy export/delete/delete-summary/audit baseline, sensitive field envelope encryption, structured request logging, readiness checks, production config validation, data encryption key validation, PostgreSQL runtime requirement, production-like compose profile, DB operation scripts, JSON metrics snapshot and operations runbooks. It still does not include production SSO, MFA, refresh-token rotation, DB RLS, Kubernetes, managed observability, automated backup purge, cloud deployment certification, recruitment scraping, or auto-apply.

Current deployment status is `production deployment/database/operations foundation candidate`, not `production-ready`. The next phase should be v3.2 Production AI Quality Upgrade.
