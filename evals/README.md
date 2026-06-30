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

## Boundaries

Fixtures use synthetic refs, summaries, and short signals only. Do not add resume raw text, JD raw text, full RAG chunk text, full interview answers, credentials, or private application materials.
