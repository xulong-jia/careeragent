# Security Review Proof Runbook

This runbook collects external security and privacy review evidence. It does not create proof by itself.

## Prepare

- The audited Git commit and deployment evidence scope.
- Auth/session, privacy deletion, encryption, rate limit and dependency scan materials.
- A reviewer who is independent from the implementation work.
- A private output path under `evidence/private_outputs/`.

## Execute

1. Provide the reviewer with redacted docs, configs and test commands.
2. Review auth/session controls, token revoke, RBAC and workspace isolation.
3. Review privacy, PII redaction, delete proof and backup purge behavior.
4. Run or review dependency scan and secret scan results.
5. Review rate limit and abuse-control posture.
6. Record findings counts and unresolved blockers.
7. Copy `evidence/templates/security_review_proof.template.json` to `evidence/private_outputs/`.
8. Set `production_quality_candidate_signal=true` only when no critical, high or unresolved findings remain.

## Counts As Proof

- Redacted external reviewer identifier.
- Review scope covering auth/session, privacy, dependencies, secrets, PII redaction and rate limits.
- Finding counts with zero critical, zero high and zero unresolved findings.
- Redacted evidence refs to scans or review notes.

## Does Not Count

- Self-attestation by the implementation agent.
- Template JSON with `template_only=true`.
- A scan with unresolved critical/high findings.
- Committed pentest reports, exploit details, customer data, infrastructure ids or credentials.

## Validate

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35c-evidence-summary.json
```

The security review status must be `security_review_candidate_passed`.

## Failure Handling

Do not edit the proof to pass. Keep failed reports private, fix the finding, rerun review or document why production readiness remains blocked.
