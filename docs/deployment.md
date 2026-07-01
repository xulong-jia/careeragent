# CareerAgent Phase 2.0 Deployment Baseline

This is a production hardening baseline for local development and repeatable checks. It is not a production SaaS runbook and does not make CareerAgent production-ready.

## Local Docker Compose

```bash
cp .env.example .env
docker compose build
docker compose up
```

Default Compose uses:

- SQLite at `backend/local_data/careeragent.db`
- deterministic LLM provider
- deterministic embedding provider
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
```

The health response exposes provider modes and feature flags, but not API keys or database credentials.

## Auth Secret Rules

- Local dev may use the `.env.example` dev-only secret.
- Production must inject a strong random `AUTH_JWT_SECRET` through a secret manager or deployment environment.
- `APP_ENV=production` rejects short secrets and dev-only / replace-me / change-me placeholder secrets.
- Missing `AUTH_JWT_SECRET` must fail loudly instead of creating a silently unusable auth path.

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

The smoke eval is synthetic contract regression only. Phase 2.1 must replace this with de-identified real sample sets and runner paths that call the actual service/retriever/parser/agent implementations.

## Production Limits

Current P1 has token auth, workspace scope, privacy export/delete/audit baseline, and PostgreSQL driver readiness. It still does not include production SSO, MFA, full RBAC, cloud deployment scripts, Kubernetes, monitoring, automatic backup, retention policy, backup erasure proof, recruitment scraping, or auto-apply.

Current deployment status is `production hardening baseline`, not `production-ready`. The next phase is 2.1 Real Evaluation Foundation.
