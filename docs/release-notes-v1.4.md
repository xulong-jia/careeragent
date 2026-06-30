# CareerAgent v1.4 Release Notes

## Scope

v1.4 focuses on Product Operations / Application Management Hardening. It strengthens manual application tracking after v1.3 Agent Workflow Baseline without changing the RAG v1.2 contract or turning the Agent into a real LLM/tool-calling system.

## Backend

- Application records now require valid `jd_id` and `resume_version_id` for tracking.
- `match_report_id` and `agent_run_id` remain optional linkage fields and are validated when provided.
- `applications` now supports source URL, location, priority, notes, interview question IDs, and last contact date.
- Added `application_status_history`.
- Application creation writes initial status history.
- Status patch writes history only when the status changes.
- Non-status patches do not duplicate status history.
- Added `GET /api/applications/{application_id}/status-history`.
- Added `POST /api/applications/{application_id}/reflection`.
- Enhanced stats now include total, by status, active/interview/offer/rejected/withdrawn counts, conversion rates, upcoming/overdue counts, and latest applications.

## Frontend

- ApplicationTrackerPage now includes an Application Board grouped by status.
- Create/edit flows include priority, source URL, location, notes, interview question IDs, and last contact date.
- Detail view shows linked JD, Resume Version, Match Report, Agent Run, status history, and reflection fields.
- Filters include priority, Match Report ID, and Agent Run ID.
- Dashboard now shows application operations metrics including upcoming, overdue, conversion, and latest application.

## Tests

- Backend tests cover JD/Resume binding, initial status history, status-change history, non-status patch behavior, invalid status handling, reflection endpoint, stats shape, filters, Agent regression, and privacy-safe responses.
- Existing RAG v1.2 and Agent v1.3 contracts remain covered by the full backend test suite.

## Boundaries

v1.4 does not add:

- real LLM calls
- embeddings, vector DB, pgvector, or FAISS
- auto apply
- recruitment website integration
- automatic status transitions
- automatic Bad Case or Study Plan writes from reflection
- production-grade multi-user auth
- full privacy deletion workflows

Application notes, interview notes, and reflection fields are for short synthetic/local summaries only. Do not store real resumes, full JDs, full interview transcripts, credentials, or private application materials in Git.
