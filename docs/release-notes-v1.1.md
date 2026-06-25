# CareerAgent v1.1.0 Study Plan Center Release Notes

Version: `v1.1.0-study-plan-center`

Scope: deterministic Study Plan Center MVP.

## Summary

v1.1.0 adds a DB-backed Study Plan Center that turns existing CareerAgent signals into deterministic learning phases and tasks. It includes backend persistence, generate/list/detail APIs, task status updates, stats aggregation, a StudyPlanPage frontend workflow, and Dashboard study stats.

This release does not add real LLM generation, RAG completion, Agent full workflow, external learning platform integration, calendar reminders, authentication, or multi-user isolation.

## Delivered Work

### 11A Backend Tables + Generate API

- Added `study_plans` table and SQLAlchemy model.
- Added schema, repository, service, and API layers.
- Added `POST /api/study-plans/generate`.
- Implemented deterministic study plan generation from:
  - `target_role`
  - Profile target roles and skill map
  - Match gaps and rewrite priorities
  - Project Rewrite missing points and evidence signals
  - Interview weakness tags
  - request-level weakness tags
- Added `phases` JSON with stable `task_id` values.
- Added source refs with preview-first privacy boundaries.

### 11B Task Status + Stats

- Added `GET /api/study-plans`.
- Added `GET /api/study-plans/{study_plan_id}`.
- Added `PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}`.
- Added `GET /api/study-plans/stats`.
- Supported task status values:
  - `todo`
  - `in_progress`
  - `done`
  - `blocked`
  - `skipped`
- Stats aggregate plan/task status from `study_plans.phases` JSON.

### 11C StudyPlanPage

- Added frontend API wrapper in `frontend/src/api/studyPlans.ts`.
- Added Study Plan TypeScript types.
- Added StudyPlanPage.
- Connected the page to real backend APIs:
  - generate study plan
  - list/filter study plans
  - get study plan detail
  - update task status
- Displayed phases, tasks, resources, deliverables, acceptance criteria, and source refs preview.
- Registered Study Plan navigation and route.

### 11D Dashboard Study Stats

- Dashboard now reads `GET /api/study-plans/stats`.
- Dashboard shows:
  - Study Plans
  - Active Study Plans
  - Pending Tasks
  - Blocked Tasks
  - Done Tasks
  - Latest Study Target
  - In Progress task summary
- Stats API failure falls back to null / 0 / empty state and does not block other Dashboard modules.

## API Surface

- `POST /api/study-plans/generate`
- `GET /api/study-plans`
- `GET /api/study-plans/{study_plan_id}`
- `PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}`
- `GET /api/study-plans/stats`

## Data Model

- `study_plans`
- `source_refs`
- `phases` JSON
- phase-level `resources`, `deliverables`, and `acceptance_criteria`
- task-level stable `task_id`
- task `status`: `todo`, `in_progress`, `done`, `blocked`, `skipped`
- plan `status`: `active`, `completed`, `archived`

## Security And Privacy

- `source_refs` are preview-first and store short references, not full source text.
- Study Plan APIs do not return Resume/JD full `raw_text`.
- Study Plan APIs do not return full interview `answer_text`.
- Dashboard study stats only shows aggregate plan/task counts and latest target role.
- The system does not automatically modify resumes, projects, interview answers, applications, or study plan source records.
- Generation is deterministic and does not call a real LLM.
- No external learning platform API or calendar reminder integration is included.
- No real API keys, local DB files, `local_data`, `dist`, `node_modules`, or caches are part of the release.

## Verification

Run on 2026-06-25:

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`: 237 passed, 6 warnings.
- `cd frontend && npm run build`: passed.
- `docker compose config`: passed.
- `python3 -m py_compile scripts/seed_demo_data.py`: passed.
- `git diff --check`: passed.
- `docker compose build`: not verified because the current environment Docker daemon/socket is unavailable. `docker compose config` passed.

## Known Not Included

- Real LLM generation or LLM judge.
- RAG completion integration.
- Agent full workflow.
- External learning platform APIs.
- Calendar reminders.
- Authentication or multi-user permission isolation.
- Production-grade privacy, logging, and access control hardening.

## Next Steps

- v1.1 final readonly acceptance.
- Optional annotated tag after acceptance: `v1.1.0-study-plan-center`.
- Later phase planning for RAG completion, controlled Agent workflow, external integrations, and auth/multi-user boundaries.
