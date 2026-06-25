# CareerAgent v1.2.0 RAG Completion Release Notes

Version: `v1.2.0-rag-completion`

Scope: deterministic RAG Completion / Grounded Answer Integration MVP.

## Summary

v1.2.0 completes the deterministic RAG Completion MVP. It tightens the grounded answer contract, persists answer runs, adds answer history UI, adds Dashboard RAG stats, and lets Interview Center / Study Plan Center optionally reference grounded RAG answer runs as preview-first evidence refs.

This release does not add real LLM answers or judges, embeddings, vector DB, reranking, RAG evaluation dashboard, Agent full workflow, automatic write-back workflows, answer delete/update/export, authentication, or multi-user isolation.

## Delivered Work

### 12A Contract Tightening

- Standardized `POST /api/rag/answer` grounded answer response.
- Preserved the legacy `sources` field for compatibility.
- Added:
  - `evidence_summary`
  - `citations`
  - `source_refs`
  - `retrieval_debug`
- Grounded hits return `grounded=true` and `uncertainty=grounded`.
- No-source answers return `grounded=false` and `uncertainty=no_relevant_source`.
- Low-evidence paths support `uncertainty=insufficient_evidence`.
- Deterministic answers are generated only from snippets and evidence summaries.

### 12B Answer Run Persistence

- Added `rag_answer_runs` table and migration.
- Added answer run model, schema, repository, service, and API support.
- Updated `POST /api/rag/answer`:
  - request supports `persist`, default `true`
  - response includes `answer_run_id`
- Added:
  - `GET /api/rag/answers`
  - `GET /api/rag/answers/{answer_run_id}`
- Supported answer run filters:
  - `grounded`
  - `uncertainty`
  - `retrieval_mode`
- `persist=false` returns `answer_run_id=null` and does not write history.

### 12C KnowledgeBasePage Answer History

- Added frontend API wrappers:
  - `listRagAnswerRuns`
  - `getRagAnswerRun`
- Added answer run TypeScript types.
- Added KnowledgeBasePage Answer History:
  - grounded filter
  - uncertainty filter
  - retrieval mode filter
  - answer run list
  - answer run detail
- Polished immediate answer display:
  - Answer Run ID
  - grounded / uncertainty
  - answer type
  - evidence summary
  - citations
  - source refs preview
  - collapsible retrieval debug

### 12D RAG Stats + Optional Downstream Refs

- Added `GET /api/rag/stats`.
- Dashboard now displays:
  - RAG Documents
  - Indexed Documents
  - RAG Chunks
  - Grounded Answers
  - Ungrounded Answers
  - Latest RAG Answer
  - Latest RAG Uncertainty
- App state now includes `ragStats`.
- RAG stats API failure falls back to null / 0 / empty state and does not block other Dashboard modules.
- Interview question generation supports optional `rag_answer_run_ids`:
  - grounded runs supplement preview-first `source_refs`
  - ungrounded runs return warnings and are not treated as reliable sources
  - missing runs return `rag_answer_run_not_found`
- Study Plan generation supports optional `rag_answer_run_ids`:
  - grounded runs can create `rag_grounded_evidence` review tasks
  - ungrounded runs only record uncertainty refs and are not treated as strong sources
  - missing runs return `rag_answer_run_not_found`
- InterviewCenterPage and StudyPlanPage include RAG Answer Run IDs inputs.

## API Surface

- `POST /api/rag/documents`
- `GET /api/rag/documents`
- `GET /api/rag/documents/{doc_id}`
- `POST /api/rag/documents/{doc_id}/index`
- `GET /api/rag/chunks`
- `POST /api/rag/search`
- `POST /api/rag/answer`
- `GET /api/rag/answers`
- `GET /api/rag/answers/{answer_run_id}`
- `GET /api/rag/stats`

Note: chunk listing is implemented as `GET /api/rag/chunks` with optional `doc_id` and `source_type` filters.

## Data Model

- `rag_documents`
- `rag_chunks`
- `rag_answer_runs`
- `rag_answer_runs.evidence_summary`
- `rag_answer_runs.citations_json`
- `rag_answer_runs.source_refs_json`
- `rag_answer_runs.retrieval_debug_json`

`rag_answer_runs` persists only the answer contract, short snippets/previews, and safe retrieval metadata.

## Frontend

- KnowledgeBasePage supports document create/list/detail, indexing, chunk view, search, deterministic answer, grounded answer display, answer history filters/list/detail, citations, source refs preview, and retrieval debug.
- Dashboard shows RAG document/chunk/answer-run stats.
- InterviewCenterPage and StudyPlanPage accept optional RAG Answer Run IDs.

## Security And Privacy

- API responses do not return document full `raw_text` by default.
- API responses do not return full chunk text.
- API responses do not return Resume/JD full `raw_text`.
- API responses do not return complete interview `answer_text`.
- `citations` expose only short snippets.
- `source_refs` expose only short previews.
- `retrieval_debug` stores IDs, scores, counts, query tokens, filters, and insufficient reason only.
- RAG refs do not automatically modify Resume, Project, Interview, Study Plan, Application, or task status.
- RAG refs are source/evidence references, not evidence of personal experience unless separately verified.
- No real LLM is connected.
- No embedding/vector DB or reranker is connected.
- No Agent full workflow is connected.
- No real API keys, local DB files, `local_data`, `dist`, `node_modules`, or caches are part of the release.

## Verification

Run on 2026-06-25:

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`: 251 passed, 6 warnings.
- `cd frontend && npm run build`: passed.
- `docker compose config`: passed.
- `python3 -m py_compile scripts/seed_demo_data.py`: passed.
- `git diff --check`: passed.
- `docker compose build`: not verified because the current environment Docker daemon/socket is unavailable. `docker compose config` passed.

## Known Not Included

- Real LLM answer generation or LLM judge.
- Embedding, vector DB, or reranker.
- RAG evaluation dashboard.
- Agent full workflow.
- Automatic write-back workflow to Resume, Project, Interview, Study Plan, or Application.
- Answer delete/update/export.
- Production-grade authentication or multi-user permission isolation.

## Next Steps

- v1.2 final readonly acceptance.
- Optional annotated tag after acceptance: `v1.2.0-rag-completion`.
- Later planning for real LLM integration, vector retrieval, controlled Agent workflow, RAG evaluation, and production privacy hardening.
