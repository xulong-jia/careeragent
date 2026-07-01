# v3.5 External Production Evidence Package

v3.5 is an evidence package preparation phase. It adds schemas, templates, checklists and proof helper scripts for external production validation. It does not make CareerAgent production-ready by itself.

The current conservative tag is `v3.4.0-production-foundation-reaudit-passed`. That tag is a foundation/re-audit pass marker only. It is not a production-ready, production-ready-candidate or production-readiness-certified release.

## Evidence Layout

- Public schemas: `evidence/schemas/`
- Public safe templates: `evidence/templates/`
- Public checklists: `evidence/checklists/`
- Private generated outputs: `evidence/private_outputs/`

`evidence/private_outputs/` is ignored by Git except for `.gitkeep`. Real provider proofs, human review imports, cloud deployment artifacts, backup purge attestations, monitoring screenshots and external security reports must stay in ignored private outputs or `/tmp`.

## Proof Types

- `provider`: external embedding and LLM provider proof with redacted endpoint metadata.
- `human_review`: external reviewer agreement and privacy pass summary.
- `deployment`: cloud deployment, managed DB, secret manager, KMS, TLS, readiness and rollback proof.
- `backup_purge`: privacy deletion to backup purge/restore-block attestation.
- `monitoring`: metrics, logs, tracing, error reporting, alerts and incident runbook proof.
- `security_review`: external security/privacy review outcome.

## Dry-Run Shape Check

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py --dry-run --output /tmp/careeragent-v35-provider-proof-dry-run.json
```

Dry-run output must report `provider_mode=not_verified` and `production_quality_candidate_signal=false`. It is only a schema/secret-leak check.

## Private Evidence Validation

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py --evidence-dir evidence/private_outputs --output /tmp/careeragent-v35-evidence-summary.json
```

The validator reports blockers for production-ready candidate and production-readiness certified status. Missing external proofs are expected until real external evidence is collected.

## Completion Boundary

v3.5 is complete when the repository has safe evidence schemas, templates, checklists, scripts, tests and documentation. It is not complete as production readiness until real external proofs are collected and a later read-only certification audit passes.
