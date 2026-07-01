# CareerAgent Evaluation Fixtures

This directory stores deterministic, privacy-safe evaluation fixtures.

## Layout

```text
evals/datasets/smoke/   Synthetic smoke inputs by module
evals/datasets/service_level/  De-identified service-level cases
evals/expected/smoke/   Expected contract outputs by module
evals/results/          Local generated run outputs, ignored except .gitkeep
```

## Run

```bash
python scripts/run_evals.py --dataset smoke
python scripts/run_evals.py --dataset synthetic
python scripts/run_evals.py --dataset service_level
python scripts/run_evals.py --dataset smoke --module rag
python scripts/run_evals.py --dataset regression
```

The runner writes `summary.md`, `metrics.json`, `failed_cases.json`, `actual_outputs.json`, and `run_config.json`.

`metrics.json` includes a non-secret `run_config` with prompt/schema/retrieval/model/code/evaluation version metadata. This is for deterministic regression traceability only; it is not model comparison or LLM judging.

`service_level` uses a temporary SQLite database and calls current CareerAgent services. It is a real evaluation foundation, but it still evaluates foundation service behavior and is not a production-quality benchmark.

Phase 2.3 parser cases cover 12 JD parser cases and 8 resume parser cases. Parser metrics include role/category hits, section/skill/project/education hits, risk flag hit rate, evidence coverage, confidence presence, warning expectations, and case pass.

Phase 2.2 RAG cases cover `lexical`, `vector`, `hybrid`, and no-evidence behavior. RAG metrics include recall/citation/source type plus `retrieval_mode_match`, `average_top_score`, `vector_index_used`, and uncertainty matching.

The current RAG path uses a local bag-of-words vectorizer with DB-persisted chunk vectors. It is a production foundation, not a final semantic embedding benchmark. Run the smoke dataset before enabling any real LLM or external embedding provider, and keep real-provider experiments out of committed `evals/results/` artifacts unless they are sanitized and explicitly reviewed.

The current parser path uses local deterministic parser foundation by default. Optional LLM parser runs must use runtime secrets only and must not commit raw private outputs or provider traces.

## Boundaries

Smoke fixtures use synthetic refs, summaries, and short signals only. Service-level fixtures may include de-identified JD/resume/RAG text so the current services can run; do not add real names, real employers, real contact details, credentials, private application materials, or committed eval run outputs.
