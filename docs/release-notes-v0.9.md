# CareerAgent v0.9.0 Project Optimization Release Notes

Release theme: `v0.9.0-project-optimization`

v0.9.0 adds the Project Optimization Center deterministic MVP on top of the v0.8 Resume/Profile Foundation. The release focuses on storing user-confirmed project facts, generating conservative rewrite suggestions against a JD, and exposing the workflow in the frontend without using a real LLM.

## 9A Project Facts Backend

- Added `projects` table and Alembic migration.
- Added Project model, schema, repository, service and API.
- Added Project CRUD APIs:
  - `POST /api/projects`
  - `GET /api/projects`
  - `GET /api/projects/{project_id}`
  - `PATCH /api/projects/{project_id}`
- Supports optional `profile_id` and `resume_version_id` references.
- Validates referenced Profile and Resume Version when IDs are provided.
- Supports filtering by `profile_id`, `resume_version_id` and `status`.

## 9B Project Rewrite Backend

- Added `project_rewrites` table and Alembic migration.
- Added Project Rewrite schema, deterministic service and API.
- Added rewrite APIs:
  - `POST /api/projects/{project_id}/rewrite`
  - `GET /api/project-rewrites/{rewrite_id}`
- Persists:
  - `matched_points`
  - `missing_points`
  - `evidence_required`
  - `rewritten_bullets`
  - `forbidden_changes`
  - `risk_flags`
  - `rewrite_strategy`
- Rewrite rules are deterministic and based only on saved project facts plus JD profile.

## 9C ProjectOptimizationPage

- Added frontend Project API wrappers.
- Added Project and Project Rewrite TypeScript types.
- Added ProjectOptimizationPage.
- Registered Project Optimization navigation and page routing.
- Page supports:
  - Project list.
  - Create and update project facts.
  - Project detail.
  - Run deterministic rewrite.
  - Display matched points, missing points, evidence required, rewritten bullets, forbidden changes and risk flags.
- Dashboard now includes project count, active project count and latest project name/status.

## 9D Dashboard / Docs / Tests Handoff

- Refined Dashboard Project Optimization summary.
- Updated README with v0.9 capabilities and boundaries.
- Updated current architecture, API reference, database schema and final acceptance report.
- Confirmed project rewrite JSON fields and safety boundaries in docs.

## 9E Final Handoff

- Finalized v0.9 acceptance documentation.
- Added this release notes document.
- Updated demo flow to include Project Optimization:
  - Create project facts.
  - Create or select JD.
  - Run rewrite.
  - Review matched / missing / evidence / risk / forbidden changes.

## Safety And Boundaries

- No real LLM is used.
- No automatic write-back to Resume Version.
- No automatic project fact generation from resume raw text.
- No fabricated project experience, company, user count, revenue, accuracy, production status, business scale or tech stack.
- Missing evidence is reported through `evidence_required` and `risk_flags`.
- `forbidden_changes` explicitly reminds users not to add unsupported facts.
- Project facts should use synthetic data or user-confirmed public summaries, not real company confidential information or sensitive commercial data.
- `local_data/`, DB files, uploads, build outputs, caches and API keys must not be committed.

## Test Results

Validated on 2026-06-24:

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`: 193 passed, 6 warnings.
- `cd frontend && npm run build`: passed.
- `docker compose config`: passed.
- `python3 -m py_compile scripts/seed_demo_data.py`: passed.
- `git diff --check`: passed.

`docker compose build` was not verified in the current environment because Docker daemon/socket was unavailable. This is recorded as an environment limitation, not a code failure.

## Not Included

- Interview Center.
- Study Plan Center.
- Real LLM parser, reviewer, judge or Agent.
- Embedding / vector DB.
- Match scoring rewrite.
- Automatic application submission.
- Authentication or multi-user permission system.
- Automatic write-back from project rewrite to resume version.

## Next Candidates

- Interview Center.
- Study Plan Center.
- RAG completion with real embedding/vector store when in scope.
- Agent workflow completion with controlled tool calling when in scope.
