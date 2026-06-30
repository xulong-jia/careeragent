# CareerAgent v1.5B/v1.5C Evaluation

This document is the stable entrypoint for the v1.5B deterministic evaluation regression foundation and the v1.5C version/privacy governance additions. The detailed design remains in `docs/evaluation-design.md`.

## Scope

- 7 smoke modules: `jd_parser`, `resume_parser`, `match`, `rag`, `agent`, `application`, `bad_case`.
- Built-in dataset: `synthetic_smoke_v1`.
- Fileized fixtures: `evals/datasets/smoke` and `evals/expected/smoke`.
- Local runner: `scripts/run_evals.py`.
- Results: ignored `evals/results/<dataset>/summary.md`, `metrics.json`, and `failed_cases.json`.
- Regression linkage: Bad Cases can be added to the `regression` eval set and marked `verified` after passing linked deterministic evaluation.

## Commands

```bash
backend/.venv/bin/python scripts/run_evals.py --dataset smoke
backend/.venv/bin/python scripts/run_evals.py --dataset smoke --module rag
backend/.venv/bin/python scripts/run_evals.py --dataset regression
```

## Boundaries

Evaluation is deterministic regression tracking only. It is not a real LLM judge, not model comparison, not production AI governance, and not an automatic apply system. Fixtures and results must use synthetic refs, summaries, and short signals only.

## v1.5C Governance Additions

- Evaluation API `run_config` records `prompt_version`, `schema_version`, `retrieval_version`, `model_version`, `code_version`, and `evaluation_version`.
- `scripts/run_evals.py` writes the same version metadata under `metrics.run_config`.
- Evaluation case creation still rejects obvious raw private text keys such as `raw_text`, `jd_raw_text`, `chunk_text`, `full_text`, `resume_text`, and `job_text`.
- `metrics.json`, `failed_cases.json`, and `summary.md` must not contain API keys, full resume/JD text, full RAG chunks, or private application materials.
