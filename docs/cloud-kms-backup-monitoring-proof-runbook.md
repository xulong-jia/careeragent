# Cloud, KMS, Backup And Monitoring Proof Runbook

This runbook describes the external operational evidence required after v3.5 preparation.

## Cloud Deployment Proof

Use `evidence/templates/deployment_proof.template.json` as the shape. The private proof must cover:

- audited Git commit SHA
- cloud provider, region and service
- managed database
- secret manager
- KMS or managed key controls
- TLS
- `/live`, `/ready` and `/metrics`
- rollback test or rehearsal

Local Docker Compose and `scripts/validate_production_deployment.py` are foundation proof only.

## Backup Purge Proof

Use `evidence/templates/backup_purge_proof.template.json` as the shape. The proof must link a privacy deletion proof id to backup purge status, legal hold status and restore-block validation.

Deletion API output alone is not enough; the backup system must prove that deleted subjects cannot be restored after purge completion.

## Monitoring Proof

Use `evidence/templates/monitoring_proof.template.json` as the shape. The proof must cover metrics, centralized logs, tracing, error reporting, alert rules, privacy redaction and incident runbook readiness.

Application logs or local `/metrics` output alone are not central observability proof.

## Security Review Proof

Use `evidence/templates/security_review_proof.template.json` as the shape. Production-readiness certified status requires external security/privacy review evidence with zero open critical/high findings or an explicit blocker decision.

## Package Validation

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35-evidence-summary.json
```

The validator summarizes blockers; it does not replace the final read-only certification audit.
