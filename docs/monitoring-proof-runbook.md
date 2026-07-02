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
3. Verify error visibility through external error reporting or platform runtime error logs.
4. Verify dashboards and alert rules use redacted identifiers only.
5. If distributed tracing is not enabled, record that limitation explicitly.
6. If external Sentry/Logfire/New Relic-style error reporting is not enabled,
   record `no_external_sentry` or an equivalent limitation explicitly.
7. Confirm incident runbook location and ownership.
8. Copy `evidence/templates/monitoring_proof.template.json` to `evidence/private_outputs/`.
9. Fill redacted dashboard refs and boolean outcomes.
10. Set `production_quality_candidate_signal=true` only when all candidate monitoring checks pass.

## Counts As Proof

- Redacted dashboard ids or links.
- Alert rule verification refs.
- Logs/metrics/traces/error-reporting evidence that excludes private payloads.
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

## Validate

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35c-evidence-summary.json
```

The monitoring status must be `monitoring_candidate_passed`.

## Failure Handling

Keep failed monitoring artifacts private. Fix missing telemetry, redaction or alert rules before generating a new proof.
