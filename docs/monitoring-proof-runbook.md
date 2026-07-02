# Monitoring Proof Runbook

This runbook collects external observability evidence. It does not create proof by itself.

## Prepare

- Centralized logs, metrics, tracing and error reporting in the deployed environment.
- Alert rules for health/readiness or equivalent availability checks.
- A privacy redaction check for logs/traces/errors.
- An incident runbook.
- A private output path under `evidence/private_outputs/`.

## Execute

1. Verify logs, metrics, traces and error reporting receive events from the deployed app.
2. Trigger or simulate a safe health/readiness alert.
3. Verify dashboards and alert rules use redacted identifiers only.
4. Confirm incident runbook location and ownership.
5. Copy `evidence/templates/monitoring_proof.template.json` to `evidence/private_outputs/`.
6. Fill redacted dashboard refs and boolean outcomes.
7. Set `production_quality_candidate_signal=true` only when all monitoring checks pass.

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

## Validate

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35c-evidence-summary.json
```

The monitoring status must be `monitoring_candidate_passed`.

## Failure Handling

Keep failed monitoring artifacts private. Fix missing telemetry, redaction or alert rules before generating a new proof.
