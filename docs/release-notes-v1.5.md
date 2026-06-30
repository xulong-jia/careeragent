# CareerAgent v1.5 Release Notes

## v1.5C Scope

v1.5C adds Privacy / Security / Data Governance controls on top of v1.5B. The work is intentionally narrow: redaction utilities, privacy-safe previews, delete/archive APIs, version metadata tracking, UI affordances, and regression tests. It does not add real LLM calls, embeddings/vector DB, pgvector, auto-apply, recruitment website integration, deployment/monitoring/backup, or production multi-user governance.

## v1.5C Backend

- Added `app.core.privacy` with `safe_preview`, `redact_text`, and `redact_mapping` for email/phone/API-key/token/secret masking and long-text replacement with length/hash/short preview.
- Added `app.core.versioning` constants: `PROMPT_VERSION`, `SCHEMA_VERSION`, `RETRIEVAL_VERSION`, `MODEL_VERSION`, and `EVALUATION_VERSION`.
- RAG `retrieval_debug` now includes retrieval/schema/model version metadata without exposing document raw text or chunk full text.
- Agent `build_final_summary` output includes safe version metadata alongside refs, counts, RAG context summary, and created record IDs.
- Evaluation API `run_config` and `scripts/run_evals.py` metrics include prompt/schema/retrieval/model/code/evaluation version metadata.
- Added delete/archive endpoints:
  - `DELETE /api/resumes/{resume_id}` soft-deletes the resume and archives its versions.
  - `DELETE /api/jobs/{jd_id}` archives the JD.
  - `DELETE /api/applications/{application_id}` archives the application and records status history.
  - `DELETE /api/rag/documents/{doc_id}` deletes the document and its chunks; persisted answer runs retain only safe refs/citations.
- Default Application list/stats exclude `archived`; `GET /api/applications?status=archived` remains available for explicit review.
- Resume/JD/RAG preview generation now uses shorter privacy-safe previews with secret masking.

## v1.5C Frontend

- ResumeCenterPage supports confirmed resume archive/delete with confirmation and list refresh.
- JDCenterPage supports JD archive/delete with confirmation and list refresh.
- ApplicationTrackerPage supports application archive through the DELETE endpoint; archived records disappear from default board/list and can be viewed with the archived status filter.
- KnowledgeBasePage supports RAG document deletion and explains that answer history keeps safe refs only.
- Reflection/interview notes and RAG document UI copy reiterate summary/preview-only usage.

## v1.5C Tests

- Added privacy redaction tests.
- Added delete/archive API tests for Resume, JD, Application, RAG document, and missing-record errors.
- Added privacy-safe response regression coverage for full raw text / chunk text avoidance.
- Added version metadata tests for RAG, Evaluation, and eval runner behavior.

## v1.5C Boundaries

v1.5C still does not provide legal-grade erasure guarantees, auth/multi-user isolation, production audit logs, backups, deployment hardening, real LLM calls, LLM judge, embeddings/vector DB, automatic application submission, or recruitment website integration. It is a local deterministic governance baseline for the current prototype.

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
