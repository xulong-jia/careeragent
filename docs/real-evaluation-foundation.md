# CareerAgent Phase 2.1 Real Evaluation Foundation

阶段 2.1 建立 service-level evaluation foundation。它真实调用当前模块，但不是 production-quality benchmark。

## Dataset

`evals/datasets/service_level/` contains de-identified, self-contained cases:

| Module | Cases | Calls |
| --- | ---: | --- |
| JD Parser | 8 | `job_service.create_job` |
| Resume Parser | 5 | `resume_service.create_resume`, `parse_resume`, `check_resume_risk` |
| Match | 5 | `resume_service`, `job_service`, `match_service.run_match_report` |
| RAG Retrieval | 6 | `rag_service.create_document`, `index_document`, `answer_question` |
| Agent Workflow | 3 | `agent.runner.run_workflow` |

The samples use Example companies, Example schools, synthetic candidate names, and no real phone, email, API key, job link, or private document.

## Commands

```bash
backend/.venv/bin/python scripts/run_evals.py --dataset synthetic --output-dir /tmp/careeragent-evals-synthetic
backend/.venv/bin/python scripts/run_evals.py --dataset service_level --output-dir /tmp/careeragent-evals-service
```

Each run writes:

- `summary.md`
- `metrics.json`
- `failed_cases.json`
- `actual_outputs.json`
- `run_config.json`

## Metrics

- JD Parser: `required_skill_hit_rate`, `preferred_skill_hit_rate`, `responsibility_hit_rate`, `role_category_match`, `case_pass`.
- Resume Parser: `section_hit_rate`, `skill_hit_rate`, `project_hit_rate`, `education_hit_rate`, `risk_flags_match`, `case_pass`.
- Match: `evidence_dimension_coverage`, `strength_keyword_hit_rate`, `gap_keyword_hit_rate`, `score_in_expected_range`, `risk_flags_match`, `case_pass`.
- RAG: `recall_at_k_term_hit`, `citation_present`, `expected_source_type_match`, `retrieval_mode_match`, `average_top_score`, `vector_index_used`, `uncertainty_match`, `case_pass`.
- Agent: `expected_status_match`, `expected_step_coverage`, `expected_missing_slot_match`, `case_pass`.
- Overall: total, passed, failed, pass rate, failed case ids, by-module pass rate.

## Bad Case Connection

`failed_cases.json` includes:

- `case_id`
- `module`
- `case_type`
- `failure_type`
- `input_summary`
- `expected_summary`
- `actual_summary`
- `failure_reason`
- `suggested_bad_case_type`

This is enough for manual Bad Case creation. Automatic Bad Case draft creation is left for Agent Workflow/quality-loop hardening; it should not block 2.1.

## DB Boundary

The current CLI writes fileized outputs only. The output shape maps to existing `evaluation_runs`, `evaluation_cases`, and `evaluation_results`, but automatic DB writes are intentionally deferred to avoid a migration-heavy detour in 2.1.

## Current Limits

- JD/Resume parsing remains deterministic/mock.
- RAG has a local vector production foundation with persisted chunk vectors, but local bag-of-words vectors are not final semantic embeddings or a production-scale vector DB.
- Match remains rule/overlap based, not trustworthy six-dimension scoring.
- Agent remains a synchronous fixed workflow.
- Service-level eval is a foundation for finding failures, not proof of production quality.

Next phase should be 2.3 Real JD Parser + Resume Parser.
