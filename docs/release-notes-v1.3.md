# CareerAgent v1.3 Agent Workflow Baseline Release Notes

Version: `v1.3.0-agent-workflow-baseline`

Scope: deterministic Agent Workflow Baseline + Application Linkage.

## Summary

v1.3 extends `job_application_preparation` from a small deterministic workflow into an end-to-end orchestration baseline. The workflow now links Resume Version, JD, Match Report, optional RAG search, RAG context summary, Project Rewrite, Interview Questions, Study Plan, and Application tracking records.

This release still does not add a real LLM Agent, free-form chat, tool-calling autonomy, automatic job applications, recruitment website integration, automatic resume/project/interview/study-plan edits, embedding/vector DB, or production authentication.

## Delivered Work

### Workflow Baseline

- Expanded `job_application_preparation` to 11 deterministic steps:
  - `validate_inputs`
  - `load_resume_version`
  - `load_job_profile`
  - `run_match_report`
  - `rag_search`
  - `summarize_rag_context`
  - `run_project_rewrites`
  - `generate_interview_questions`
  - `generate_study_plan`
  - `create_or_link_application`
  - `build_final_summary`
- Added request inputs:
  - `project_ids`
  - `application_id`
  - `create_application`
  - `rag_answer_run_ids`
- `project_ids` can be explicit; when empty, the workflow auto-discovers active projects for the selected resume version.
- `rag_answer_run_ids` are passed into Interview and Study Plan generation as optional refs.
- `summarize_rag_context` consumes `rag_search` refs and exposes source counts, usable refs, and warnings without storing document raw text or full chunk text.
- `final_summary` is exposed on `AgentRunRecord` and stored in `output_refs.final_summary`, including summarized RAG context counts and warnings.

### Application Linkage

- Added nullable `applications.agent_run_id`.
- Added application create/update/list support for `agent_run_id`.
- Added validation for missing agent runs.
- Workflow behavior:
  - existing `application_id` links the run to an existing application
  - no `application_id` with `create_application=true` creates a saved draft application
  - no `application_id` with `create_application=false` skips application creation

### Frontend

- AgentRunsPage now supports:
  - Project IDs
  - Existing Application ID
  - Create/link application toggle
  - RAG Answer Run IDs
  - final summary display
- ApplicationTrackerPage now supports:
  - creating records with `agent_run_id`
  - filtering by `agent_run_id`
  - displaying linked agent run refs
- Dashboard now shows:
  - latest agent run status and score
  - linked application summary
  - count of applications linked to agent runs

### Docs

- Updated README.
- Updated current architecture.
- Updated API reference.
- Updated database schema.
- Updated Agent Workflow design.
- Updated Application Management design.
- Updated demo script.
- Added this release notes file.

## API Surface

No new top-level Agent endpoints were added.

Updated request / response fields:

- `POST /api/agents/runs`
  - accepts `project_ids`
  - accepts `application_id`
  - accepts `create_application`
  - accepts `rag_answer_run_ids`
  - response includes `run.final_summary`
- `POST /api/applications`
  - accepts `agent_run_id`
- `PATCH /api/applications/{application_id}`
  - accepts `agent_run_id`
- `GET /api/applications?agent_run_id={agent_run_id}`
  - filters applications by linked agent run

## Data Model

- Added `applications.agent_run_id`.
- Added index `ix_applications_agent_run_id`.
- Added nullable FK from `applications.agent_run_id` to `agent_runs.id`.
- `agent_runs` and `agent_steps` are reused; no new Agent table was added.

## Security And Privacy

- Agent step payloads store refs, short metadata, scores, warnings, and created record IDs only.
- `final_summary` stores score, short strengths/gaps, next actions, and created record refs only.
- Application linkage stores `agent_run_id` only; it does not copy Agent step payloads.
- Application records remain tracking records; no external application is submitted.
- The workflow does not copy Resume raw text, JD raw text, RAG full chunk text, full interview answers, or application materials into Agent steps or Application records.
- No real LLM, embedding/vector DB, recruitment website, or external tool-calling Agent is connected.

## Verification

Run on 2026-06-30:

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`: 252 passed, 6 warnings.
- `cd frontend && npm run build`: passed.
- `PYTHONPATH=backend DATABASE_URL=sqlite:////tmp/careeragent_v13_alembic_check.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head`: passed.
- `backend/.venv/bin/python -m py_compile scripts/seed_demo_data.py`: passed.
- `docker compose config`: passed.
- `git diff --check`: passed.

## Known Not Included

- Real LLM Agent or chat interface.
- True tool-calling autonomy.
- Automatic job application submission.
- Recruitment website integration.
- Automatic state transitions for applications.
- Automatic resume/project/interview/study-plan edits.
- RAG evaluation dashboard.
- Embedding/vector DB or reranker.
- Production authentication or multi-user permission isolation.
