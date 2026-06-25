# CareerAgent v1.0.0 Interview Center Release Notes

Release name: `v1.0.0-interview-center`

This release adds a deterministic Interview Center workflow on top of the existing local SQLite workbench. It does not introduce real LLM calls, LLM judging, embeddings, vector search, Study Plan writeback, or agentic full workflow execution.

## 10A Questions Backend

- Added `interview_questions` and `interview_answers` database tables.
- Added `POST /api/interviews/questions/generate`.
- Added `GET /api/interviews/questions`.
- Implemented deterministic question generation from JD profile, structured resume, optional project facts, and optional project rewrite refs.
- Added `expected_points` and `source_refs`.
- `source_refs` store only source type/id/field/label and short preview, not Resume/JD full raw text.

## 10B Answers And Scoring

- Added `POST /api/interviews/answers`.
- Added `GET /api/interviews/answers`.
- Added `POST /api/interviews/answers/{answer_id}/score`.
- Saved full `answer_text` locally in SQLite for deterministic scoring.
- API responses and lists default to `answer_text_preview`, not full answer text.
- Added deterministic score dimensions:
  - `structure`
  - `technical_depth`
  - `business_understanding`
  - `evidence`
  - `clarity`
  - `risk_control`
  - `overall_average`
- Added deterministic `feedback` and `weakness_tags`.

## 10C Frontend Page

- Added `frontend/src/api/interviews.ts`.
- Added Interview TypeScript types.
- Added `InterviewCenterPage`.
- Registered Interview Center navigation.
- Frontend workflow supports:
  - question generation form
  - warnings / need more info display
  - question filters
  - question selection
  - answer submit
  - answer list
  - answer scoring
  - scores / feedback / weakness tags display
- The page does not display Resume/JD full raw text.
- Saved answer lists display preview only.

## 10D Dashboard, Docs, Tests

- Added `GET /api/interviews/stats`.
- Dashboard now shows independent Interview Training stats, separate from Application Tracking interview stages:
  - question count
  - answer count
  - scored answer count
  - latest average score
  - latest weakness tags
- Added `backend/tests/test_interview_stats_api.py`.
- Stats tests cover empty stats, generated-question stats, submitted-answer stats, scored-answer stats, latest weakness tags, latest average score, and privacy exclusions.
- Updated README, architecture docs, API reference, database schema, demo script, and final acceptance report.

## 10E Final Handoff

- Added this release note.
- Updated final acceptance documentation for v1.0.0.
- Recorded final verification results.
- No tag was created in this step.

## Safety And Privacy

- Resume/JD default API responses do not return full raw text.
- Interview `source_refs` store only short previews and references.
- Answer submit/list responses default to `answer_text_preview`.
- Full `answer_text` is stored only in the local DB for deterministic scoring.
- Dashboard stats do not return or display full answer text.
- Scoring is deterministic and does not use an LLM judge.
- Feedback asks users to strengthen existing facts and evidence; it must not invent experience, metrics, company claims, production status, or unsupported outcomes.
- Study Plan is not automatically written.
- The release does not commit `local_data`, SQLite DB files, `dist`, `node_modules`, cache directories, uploads, logs, exports, `.env`, or API keys.

## Verification

Run on 2026-06-25:

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`: 216 passed, 6 warnings.
- `cd frontend && npm run build`: passed.
- `docker compose config`: passed.
- `python3 -m py_compile scripts/seed_demo_data.py`: passed.
- `git diff --check`: passed.
- `docker compose build`: not verified because the current environment Docker daemon/socket is unavailable; this is an environment limitation, not a code failure. `docker compose config` passed.

## Explicitly Not Included

- Study Plan Center.
- Automatic Study Plan writeback.
- Real LLM question generation or LLM judge.
- RAG completion.
- Embedding or vector DB integration.
- Agent full workflow.
- Authentication or production multi-user isolation.
- Automatic resume modification.
- Real interview answer submission or private interview data.

## Follow-Up Plan

- Study Plan Center.
- RAG completion integration with strict source grounding.
- Agent full workflow with controlled tool-calling.
- Bad Case and Evaluation completion for Interview Center regressions.
- Optional v1.0 readonly acceptance and annotated tag: `v1.0.0-interview-center`.
