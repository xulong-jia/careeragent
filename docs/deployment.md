# CareerAgent Deployment Baseline

This is a security/privacy/deployment production foundation for local development and repeatable checks. It is not a production SaaS runbook and does not make CareerAgent production-ready.

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

## Health Check

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

The health response exposes provider modes and feature flags, but not API keys or database credentials. The readiness response checks DB reachability and runtime config validity, and returns only masked config summary.

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

This repository does not provision managed PostgreSQL, backups, restore jobs or retention policies.

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

## Production Limits

Current v3.0 has token auth, workspace scope, token revoke, route-level RBAC gate, privacy export/delete/delete-summary/audit baseline, sensitive field envelope encryption, structured request logging, readiness checks, production config validation, data encryption key validation, and PostgreSQL runtime requirement for production. It still does not include production SSO, MFA, refresh-token rotation, DB RLS, cloud deployment scripts, Kubernetes, centralized monitoring, automatic backup, retention policy, backup erasure proof, recruitment scraping, or auto-apply.

Current deployment status is `security/privacy/data-governance production foundation candidate`, not `production-ready`. The next phase should be v3.1 Production Deployment, Database & Operations Foundation.
