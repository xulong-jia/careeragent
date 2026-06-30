# CareerAgent v1.5 Release Notes

## v1.5B Scope

v1.5B adds the Bad Case + Evaluation Regression Foundation. It turns the existing manual Bad Case and deterministic Evaluation MVP into a small regression loop without adding real LLM calls, embeddings, vector DB, auto-apply, or production multi-user governance.

## Backend

- Extended `bad_cases` with `root_cause`, `fix_strategy`, `tags`, `added_to_eval_set`, `verified_at`, `regression_evaluation_run_id`, and `regression_evaluation_case_id`.
- Added `verified` as a Bad Case lifecycle status.
- Added direct Bad Case routes under `/api/bad-cases`, including stats and `POST /api/bad-cases/{bad_case_id}/add-to-eval`.
- Kept legacy `/api/evaluations/bad-cases` routes for compatibility.
- Expanded deterministic evaluation modules to `jd_parser`, `resume_parser`, `match`, `rag`, `agent`, `application`, and `bad_case`.
- Added `GET /api/evaluations/datasets`.
- Evaluation metrics now include `failed_case_ids`.
- Evaluation `run_config` records deterministic prompt/schema/retrieval/model/code version metadata.
- Regression runs update linked Bad Cases: passing linked cases mark Bad Case `verified`; failing linked cases keep or return the Bad Case to an unverified state.

## Fileized Evals

- Added privacy-safe smoke datasets under `evals/datasets/smoke`.
- Added expected baselines under `evals/expected/smoke`.
- Added `scripts/run_evals.py` with:
  - `python scripts/run_evals.py --dataset smoke`
  - `python scripts/run_evals.py --dataset smoke --module rag`
  - `python scripts/run_evals.py --dataset regression`
- Runner output is written to ignored `evals/results/` files: `summary.md`, `metrics.json`, and `failed_cases.json`.

## Frontend

- QualityReviewPage shows Bad Case stats, lifecycle fields, tags, regression linkage, and Add to regression eval action.
- EvaluationPage shows dataset metadata, 7-module smoke selection, run config, failed cases, and result detail.

## Boundaries

v1.5B does not add:

- real LLM calls
- LLM judge
- embeddings, vector DB, pgvector, FAISS, or reranker
- auto-apply
- recruitment website integration
- automatic resume/project/application mutation
- production-grade auth or multi-user isolation
- full privacy deletion workflows

Bad Case and Evaluation payloads remain summary/ref based and must not include resume raw text, JD raw text, RAG full chunk text, full interview answers, credentials, or private application materials.
