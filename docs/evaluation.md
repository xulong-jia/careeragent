# CareerAgent Evaluation

This document is the stable entrypoint for the deterministic evaluation regression foundation, version/privacy governance additions, and Phase 2.1/2.2/2.3 service-level evaluation foundation. The detailed design remains in `docs/evaluation-design.md`.

Phase 2.3 status: CareerAgent now has both synthetic contract regression and service-level evaluation foundation. RAG service-level cases cover lexical/vector/hybrid/no-evidence behavior; parser service-level cases cover JD/Resume evidence, confidence, warnings, and risk flags. This is still not a production-quality benchmark.

## Scope

- 7 smoke modules: `jd_parser`, `resume_parser`, `match`, `rag`, `agent`, `application`, `bad_case`.
- Built-in dataset: `synthetic_smoke_v1`.
- Fileized fixtures: `evals/datasets/smoke` and `evals/expected/smoke`.
- Service-level fixtures: `evals/datasets/service_level`.
- Local runner: `scripts/run_evals.py`.
- Results: ignored `evals/results/<dataset>/summary.md`, `metrics.json`, `failed_cases.json`, `actual_outputs.json`, and `run_config.json`.
- Regression linkage: Bad Cases can be added to the `regression` eval set and marked `verified` after passing linked deterministic evaluation.

## Commands

```bash
backend/.venv/bin/python scripts/run_evals.py --dataset smoke
backend/.venv/bin/python scripts/run_evals.py --dataset synthetic
backend/.venv/bin/python scripts/run_evals.py --dataset service_level
backend/.venv/bin/python scripts/run_evals.py --dataset smoke --module rag
backend/.venv/bin/python scripts/run_evals.py --dataset regression
```

## Boundaries

Synthetic evaluation is deterministic contract regression only. It is not a real LLM judge, not model comparison, not production AI governance, and not an automatic apply system.

Service-level evaluation uses de-identified JD, resume, match, RAG, and agent workflow cases. The runner calls actual current services or runner paths instead of constructing `actual` in the script. Current service-level failures are quality signals, not something to hide.

Current service-level evaluation still runs foundation modules. A pass does not mean parser, RAG, match, or agent production quality.

## v1.5C Governance Additions

- Evaluation API `run_config` records `prompt_version`, `schema_version`, `retrieval_version`, `model_version`, `code_version`, and `evaluation_version`.
- `scripts/run_evals.py` writes the same version metadata under `metrics.run_config`.
- Evaluation case creation still rejects obvious raw private text keys such as `raw_text`, `jd_raw_text`, `chunk_text`, `full_text`, `resume_text`, and `job_text`.
- `metrics.json`, `failed_cases.json`, and `summary.md` must not contain API keys, full resume/JD text, full RAG chunks, or private application materials.

## Phase 2.1 Additions

- `service_level` dataset calls `job_service`, `resume_service`, `match_service`, `rag_service`, and `agent.runner`.
- Metrics include JD skill/responsibility/role checks, Resume section/skill/project/education/risk checks, Match evidence/strength/gap/score checks, RAG recall/citation/source-type checks, and Agent status/step/missing-slot checks.
- `failed_cases.json` includes fields needed for manual Bad Case creation: `case_id`, `module`, `case_type`, `failure_type`, `input_summary`, `expected_summary`, `actual_summary`, `failure_reason`, and `suggested_bad_case_type`.
- The CLI currently writes output files only. The JSON shape maps to existing Evaluation Run/Case/Result schema, but automatic DB write is left as a follow-up to avoid a migration-heavy detour in 2.1.

## Phase 2.2 RAG Additions

- RAG service-level cases include `retrieval_mode` and cover `lexical`, `vector`, `hybrid`, and no-evidence refusal.
- RAG metrics add `retrieval_mode_match`, `average_top_score`, `vector_index_used`, and `uncertainty_match`.
- RAG vector/hybrid eval checks the local persisted-vector path; it is not a final semantic embedding benchmark.

## Phase 2.3 Parser Additions

- JD parser service-level cases increased to 12 and cover required/preferred skills, role category, responsibilities, hidden requirements, evidence, confidence, and warnings.
- Resume parser service-level cases increased to 8 and cover section parsing, skill categories, projects, education, risk flags, evidence, confidence, ambiguous sections, and low-confidence text.
- Parser eval metrics add `evidence_coverage`, `confidence_present`, `warning_expected_match`, `hidden_requirement_hit_rate`, and `risk_flag_hit_rate`.
- Parser eval uses local deterministic parser foundation by default; optional LLM provider runs are not required for tests and are not production-quality benchmark evidence.
