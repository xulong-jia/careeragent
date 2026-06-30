# CareerAgent v1.6 Release Notes

v1.6 adds Production AI & Deployment Readiness without changing the default deterministic product behavior.

## v1.6A Audit Decisions

- Default startup remains deterministic and keyless.
- Real LLM and embedding providers are opt-in through env flags.
- Vector retrieval uses a local deterministic baseline; pgvector/FAISS are not required by default.
- Docker Compose remains local and reproducible without external services.

## v1.6B Provider Boundary

- Added `backend/app/ai/llm_provider.py`.
- Added `backend/app/ai/embedding_provider.py`.
- Added `backend/app/ai/validators.py`.
- Added `backend/app/ai/prompts/` as the prompt boundary directory.
- Added config for provider mode, model, timeout, temperature, embedding dimension, vector store, retrieval mode, and real-provider feature flags.
- Health check now exposes provider/vector modes without secrets.

## v1.6C Retrieval Hardening

- RAG search accepts optional `retrieval_mode`: `lexical`, `vector`, or `hybrid`.
- Default remains `lexical`.
- `vector` and `hybrid` use deterministic local embeddings and do not require FAISS/pgvector.
- Chunks now receive deterministic `embedding_id` metadata.
- `retrieval_debug` includes safe mode/version/model fields and no full raw text or chunk text.

## v1.6D Deployment Readiness

- `.env.example` includes real-provider placeholders only.
- `docker-compose.yml` passes deterministic defaults and empty provider placeholders.
- Added deployment and AI provider docs.

## Validation

Executed on 2026-06-30:

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`: 284 passed, 6 warnings.
- `cd frontend && npm run build`: passed; local Node 20.17.0 prints a Vite 20.19+ version warning, but build exits 0.
- `PYTHONPATH=backend DATABASE_URL=sqlite:////tmp/careeragent_v16_alembic_check.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head`: passed.
- `docker compose config`: passed.
- `docker compose build`: passed.
- `backend/.venv/bin/python -m py_compile scripts/seed_demo_data.py scripts/run_evals.py`: passed.
- `python3 scripts/run_evals.py --dataset smoke`: 7/7 passed.
- `git diff --check`: passed.

## Boundaries

v1.6 still does not add automatic applications, recruitment website integration, production auth/multi-tenancy, LLM judge, cloud deployment automation, Kubernetes, monitoring, or production erasure guarantees.
