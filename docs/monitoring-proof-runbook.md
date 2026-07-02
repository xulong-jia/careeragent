# Monitoring Proof Runbook

This runbook collects external observability evidence. It does not create proof by itself.

## Prepare

- Centralized logs and metrics in the deployed environment.
- Alert rules for health/readiness or equivalent availability checks.
- Error visibility through either external error reporting or platform runtime
  error logs plus verified alert delivery.
- Distributed tracing for certified/enhanced observability.
- A privacy redaction check for logs/traces/errors.
- An incident runbook.
- A private output path under `evidence/private_outputs/`.

## Execute

1. Verify logs and metrics receive events from the deployed app.
2. Trigger or simulate a safe health/readiness alert.
3. Configure backend `SENTRY_DSN` and frontend `VITE_SENTRY_DSN` through the
   deployment secret manager. Keep `SENTRY_SEND_DEFAULT_PII=false`.
4. Set `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, and trace sample rates for both
   backend and frontend. Use the same release string for a single deployed build.
5. Verify external error reporting with a synthetic backend/frontend event that
   contains no resume, JD, interview, RAG chunk, token or raw user text.
6. Verify distributed tracing links a frontend request to the backend without
   propagating trace headers to unrelated origins.
7. Verify dashboards and alert rules use redacted identifiers only.
8. If distributed tracing is not enabled, record that limitation explicitly.
9. If external Sentry/Logfire/New Relic-style error reporting is not enabled,
   record `no_external_sentry` or an equivalent limitation explicitly.
10. Confirm incident runbook location and ownership.
11. Copy `evidence/templates/monitoring_proof.template.json` to `evidence/private_outputs/`.
12. Fill redacted dashboard refs and boolean outcomes.
13. Set `production_quality_candidate_signal=true` only when all candidate monitoring checks pass.

## Counts As Proof

- Redacted dashboard ids or links.
- Alert rule verification refs.
- Logs/metrics/traces/error-reporting evidence that excludes private payloads.
- Redacted Sentry issue/event ids and trace ids.
- Incident runbook ref.

## Does Not Count

- Local `/metrics` output only.
- Template JSON with `template_only=true`.
- Screenshots or logs containing resume text, JD text, RAG chunks, interview answers, tokens or raw trace payloads.
- Alert rules that were configured but never verified.

## Candidate vs Certified

`monitoring_candidate_passed` requires real, redacted evidence for:

- `logs_enabled=true`
- `metrics_enabled=true`
- `alert_rules_configured=true`
- `health_check_alert_verified=true`
- `incident_runbook_exists=true`
- non-empty `dashboard_refs`
- `production_quality_candidate_signal=true`

Distributed tracing and external error reporting are stronger certified-level
observability requirements. A candidate proof may set `tracing_enabled=false`
and/or `error_reporting_enabled=false` only when the limitations clearly state
the missing capability and the proof still covers runtime error visibility,
alert delivery and incident response. Missing alerts or missing incident
runbook always fails candidate status.

For certified observability, set `tracing_enabled=true` and
`error_reporting_enabled=true` only after real external evidence exists. The
proof must not include raw Sentry event payloads, stack locals, request bodies,
authorization headers, cookies, resume text, JD text, interview answers, RAG
chunks or tokens.

## Sentry Runtime Variables

Backend runtime:

- `SENTRY_DSN`
- `SENTRY_ENVIRONMENT`
- `SENTRY_RELEASE`
- `SENTRY_TRACES_SAMPLE_RATE`
- `SENTRY_SEND_DEFAULT_PII=false`
- `ENABLE_OBSERVABILITY_TEST_ENDPOINT=false`

Frontend runtime/build vars:

- `VITE_SENTRY_DSN`
- `VITE_SENTRY_ENVIRONMENT`
- `VITE_SENTRY_RELEASE`
- `VITE_SENTRY_TRACES_SAMPLE_RATE`
- `VITE_SENTRY_TRACE_TARGETS`
- `VITE_ENABLE_OBSERVABILITY_TEST_TOOLS=false`

`SENTRY_AUTH_TOKEN` is build-time only for source map upload. Store it in CI or
Render build secrets, never in committed env files and never in runtime JS.

For a temporary tracing proof run, set `VITE_ENABLE_OBSERVABILITY_TEST_TOOLS=true`
and redeploy the frontend. The app will create one synthetic
`observability.trace_check` transaction and fetch `/live` without auth headers,
request body or private user text. Set it back to `false` after collecting
redacted trace ids.

## Validate

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35c-evidence-summary.json
```

The monitoring status must be `monitoring_candidate_passed`.

## Failure Handling

Keep failed monitoring artifacts private. Fix missing telemetry, redaction or alert rules before generating a new proof.
