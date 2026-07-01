# CareerAgent v3.1 Operations Runbook

v3.1 establishes operations foundation for production-like environments. It does not replace managed observability, SIEM, cloud alerts or an incident process.

## Probes

- Liveness: `GET /live` or `GET /api/live`
- Health summary: `GET /health`
- Readiness: `GET /ready` or `GET /api/ready`
- Metrics snapshot: `GET /metrics` or `GET /api/metrics`

Expected deployment behavior:

- Liveness proves the process responds.
- Health exposes non-secret provider and mode metadata.
- Readiness proves config, DB reachability, storage writability and production migration state.
- Metrics exposes non-secret HTTP counters and Agent/Eval/RAG DB counts.

## Structured Logs

Backend logs use JSON events from the `careeragent` logger. v3.1 adds run-level events for:

- `agent_run_created`
- `agent_run_resumed`
- `agent_run_retried`
- `agent_run_cancelled`
- `evaluation_run_created`
- `evaluation_case_created`
- `evaluation_case_created_from_bad_case`
- `rag_document_created`
- `rag_document_indexed`
- `rag_search_completed`
- `rag_answer_completed`

Logs include ids, status, counts, provider/model metadata and request_id. They must not include raw resume text, JD text, RAG chunk text, questions, answers, Authorization headers, tokens, provider keys or full request payloads.

## Metrics

`/metrics` returns:

- process uptime;
- HTTP request count, status classes and duration summary;
- in-process domain event counters;
- DB counts for `agent_runs`, `evaluation_runs`, `rag_documents`, `rag_chunks` and `rag_answer_runs`.

These are foundation metrics for visibility. Production should export them to a managed metrics backend and define alert rules for:

- readiness not ready;
- high 5xx rate;
- auth failure spike;
- session revoke anomaly;
- agent failure rate;
- eval benchmark regression;
- RAG no-evidence spike;
- failed migrations;
- DB connection failures;
- unexpected drop in Agent/Eval/RAG run counts;
- repeated RAG no-evidence/ungrounded trends after v3.2 benchmark integration.

## Tracing and Error Reporting

v3.1 provides request_id correlation but not distributed tracing. Production should connect:

- OpenTelemetry or platform tracing;
- centralized error reporting;
- log retention with PII-safe redaction;
- audit log export for immutable retention.

## Incident Checklist

1. Check `/live`, `/health`, `/ready`, `/metrics`.
2. Capture request_id and event name from structured logs.
3. Confirm current git commit, image digest and Alembic revision.
4. Verify DB reachability and migration state.
5. For data privacy incidents, run privacy export/delete dry-run only with authorized owner/admin context.
6. If rollback is required, follow `docs/database-operations.md`.

## v3.4 Rework Evidence

- `scripts/run_final_readiness_gates.sh` aggregates backend tests, evals,
  Playwright Chromium browser E2E, compose checks, deployment proof validation,
  Alembic temp DB and artifact/secret scans.
- `scripts/validate_production_deployment.py` emits local production-like proof
  JSON with masked secrets.
- `docs/production-evidence-templates.md` defines cloud, managed DB, secret
  manager/KMS, backup purge/legal deletion and observability proof fields.

These are evidence foundations. They do not replace actual managed log drains,
metrics dashboards, tracing, error reporting, alert delivery or incident drills.

## Status

Current status after v3.4 blocker rework: production deployment/database/operations evidence foundation. It is not production-readiness certified until v3.4 final read-only audit passes all remaining external proof checks.
