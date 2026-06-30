# CareerAgent Evaluation Fixtures

This directory stores deterministic, privacy-safe evaluation fixtures.

## Layout

```text
evals/datasets/smoke/   Synthetic smoke inputs by module
evals/expected/smoke/   Expected contract outputs by module
evals/results/          Local generated run outputs, ignored except .gitkeep
```

## Run

```bash
python scripts/run_evals.py --dataset smoke
python scripts/run_evals.py --dataset smoke --module rag
python scripts/run_evals.py --dataset regression
```

The runner writes `summary.md`, `metrics.json`, and `failed_cases.json`.

`metrics.json` includes a non-secret `run_config` with prompt/schema/retrieval/model/code/evaluation version metadata. This is for deterministic regression traceability only; it is not model comparison or LLM judging.

v1.6 provider and retrieval readiness remains deterministic by default. Run the smoke dataset before enabling any real LLM or external embedding provider, and keep real-provider experiments out of committed `evals/results/` artifacts unless they are sanitized and explicitly reviewed.

## Boundaries

Fixtures use synthetic refs, summaries, and short signals only. Do not add resume raw text, JD raw text, full RAG chunk text, full interview answers, credentials, or private application materials.
