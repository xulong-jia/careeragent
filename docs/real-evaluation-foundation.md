# CareerAgent Phase 2.1 Real Evaluation Foundation

阶段 2.1 建立 service-level evaluation foundation。它真实调用当前模块，但不是 production-quality benchmark。

## Dataset

`evals/datasets/service_level/` contains de-identified, self-contained cases:

| Module | Cases | Calls |
| --- | ---: | --- |
| JD Parser | 12 | `job_service.create_job` |
| Resume Parser | 8 | `resume_service.create_resume`, `parse_resume`, `check_resume_risk` |
| Match | 9 | `resume_service`, `job_service`, `match_service.run_match_report`, `match_service.compare_matches` |
| Project Rewrite | 6 | `project_service.create_project`, `job_service.create_job`, `project_rewrite_service.create_project_rewrite` |
| RAG Retrieval | 6 | `rag_service.create_document`, `index_document`, `answer_question` |
| Agent Workflow | 8 | `agent_service.create_run_for_workflow`, `resume_run`, `retry_run`, `cancel_run`, `agent.runner.run_workflow` |

The samples use Example companies, Example schools, synthetic candidate names, and no real phone, email, API key, job link, or private document.

v3.2 adds `evals/datasets/benchmark/`, a 100-case synthetic benchmark foundation:

| Module | Cases |
| --- | ---: |
| JD Parser | 30 |
| Resume Parser | 20 |
| RAG Retrieval | 20 |
| RAG Answer | 10 |
| Match | 10 |
| Project Rewrite | 5 |
| Agent Workflow | 5 |

`human_review_sample.jsonl` is synthetic reviewer data for calibration and agreement metrics. It is not a real human-review protocol.

v3.4 blocker rework adds `evals/datasets/anonymized_benchmark/`, a 155-case
manually curated anonymized real-world-style benchmark foundation. It includes
formal human review and advisory LLM judge sample fixtures. It is stronger than
the synthetic benchmark but still must not be represented as private production
data or completed external review.

## Commands

```bash
backend/.venv/bin/python scripts/run_evals.py --dataset synthetic --output-dir /tmp/careeragent-evals-synthetic
backend/.venv/bin/python scripts/run_evals.py --dataset service_level --output-dir /tmp/careeragent-evals-service
backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --output-dir /tmp/careeragent-evals-benchmark
backend/.venv/bin/python scripts/run_evals.py --dataset anonymized_benchmark --output-dir /tmp/careeragent-evals-anonymized
```

Each run writes:

- `summary.md`
- `metrics.json`
- `failed_cases.json`
- `actual_outputs.json`
- `run_config.json`

## Metrics

- JD Parser: `required_skill_hit_rate`, `preferred_skill_hit_rate`, `responsibility_hit_rate`, `role_category_match`, `hidden_requirement_hit_rate`, `evidence_coverage`, `confidence_present`, `warning_expected_match`, `case_pass`.
- Resume Parser: `section_hit_rate`, `skill_hit_rate`, `project_hit_rate`, `education_hit_rate`, `risk_flag_hit_rate`, `evidence_coverage`, `confidence_present`, `case_pass`.
- Match: `dimension_score_present_rate`, `evidence_dimension_coverage`, `strength_keyword_hit_rate`, `gap_keyword_hit_rate`, `score_in_expected_range`, `risk_flag_hit_rate`, `rewrite_priority_hit_rate`, `scoring_method_present`, `confidence_present`, `case_pass`.
- Project Rewrite: `before_after_present`, `evidence_required_present`, `forbidden_changes_present`, `risk_level_present`, `matched_requirement_hit_rate`, `missing_point_hit_rate`, `risk_flag_hit_rate`, `bullet_keyword_hit_rate`, `fabrication_guard_pass`, `case_pass`.
- RAG: `recall_at_k_term_hit`, `citation_present`, `expected_source_type_match`, `retrieval_mode_match`, `average_top_score`, `vector_index_used`, `uncertainty_match`, `case_pass`.
- Agent: `expected_status_match`, `expected_step_coverage`, `missing_slot_match`, `resume_success`, `retry_success`, `cancel_success`, `bad_case_payload_present`, `run_config_present`, `privacy_safe_payload_present`, `case_pass`.
- Overall: total, passed, failed, pass rate, failed case ids, by-module pass rate.
- Benchmark RAG retrieval: `recall_at_k`, `mrr`, `precision_at_k`, `citation_coverage`, `source_type_match`, `no_evidence_refusal_accuracy`, `reranker_improvement_rate`.
- Benchmark RAG answer: `groundedness`, `unsupported_claim_rate`, `citation_required_pass_rate`, `refusal_accuracy`, `answer_schema_pass_rate`.
- Benchmark Match: `score_in_expected_range`, `ranking_consistency`, `evidence_completeness`, `gap_identification_precision`, `human_agreement`, `stability_delta`.
- Human review summary: reviewed count, score delta, disagreement rate, human agreement rate, ranking consistency, score distribution, dimension disagreement.
- Bad-case regression trend: candidate count, reopened count, regression pass rate and privacy-safe bad-case candidates.

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

This is enough for manual Bad Case creation across most modules. Phase 2.5 adds automatic Agent step failure Bad Case draft creation and `bad_case_payload` persistence for Agent Workflow runs.

## DB Boundary

The current CLI writes fileized outputs only. The output shape maps to existing `evaluation_runs`, `evaluation_cases`, and `evaluation_results`, but automatic DB writes are intentionally deferred to avoid a migration-heavy detour in 2.1.

## Current Limits

- v3.2 benchmark is synthetic large-sample foundation only. It does not replace real anonymized data, provider runs, LLM judge calibration, or human review.
- JD/Resume parsing now has parser production foundation fields, evidence, confidence, warnings, parser metadata, and optional LLM provider fallback. Default tests still use deterministic local parser foundation.
- RAG has a local vector production foundation with persisted chunk vectors, v3.2 provider metadata, reranker contract and optional LLM grounded answer path, but local/offline vectors are not final semantic embeddings or a production-scale vector DB.
- Match and Project Rewrite now have 2.4 trustworthy foundation fields, service-level metrics and v3.2 synthetic calibration helpers, but remain uncalibrated against large real human agreement benchmarks.
- Agent Workflow now has 2.5 production foundation lifecycle, resume/retry/cancel, multiple fixed workflows, and failure Bad Case drafts. It remains a synchronous local runner, not a durable production workflow engine.
- Service-level eval is a foundation for finding failures, not proof of production quality.

Next phase should be v3.3 Frontend Productization & End-to-End Experience.
