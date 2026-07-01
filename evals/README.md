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

`service_level` uses a temporary SQLite database and calls current CareerAgent services. It is a real evaluation foundation, but it still evaluates deterministic/mock service behavior and is not a production-quality benchmark.

v1.6 provider and retrieval readiness remains deterministic by default. Run the smoke dataset before enabling any real LLM or external embedding provider, and keep real-provider experiments out of committed `evals/results/` artifacts unless they are sanitized and explicitly reviewed.

## Boundaries

Smoke fixtures use synthetic refs, summaries, and short signals only. Service-level fixtures may include de-identified JD/resume/RAG text so the current services can run; do not add real names, real employers, real contact details, credentials, private application materials, or committed eval run outputs.
