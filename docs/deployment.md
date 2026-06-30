# CareerAgent v1.6 Deployment Readiness

This is a local deployment baseline, not a production SaaS runbook.

## Deterministic Docker Compose

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

No real API key is required.

## Health Check

```bash
curl http://localhost:8000/health
```

The health response exposes provider modes and feature flags, but not API keys or database credentials.

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

## Limits

v1.6 does not add auth, multi-tenancy, RBAC, cloud deployment scripts, Kubernetes, monitoring, automatic backup, recruitment scraping, or auto-apply. Those require separate design.
