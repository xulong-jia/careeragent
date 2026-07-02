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
- `human_review`: external reviewer batch with item-level scores, summary metrics, adjudication status and privacy pass.
- `deployment`: cloud deployment, managed DB, secret manager, KMS, TLS, readiness and rollback proof.
- `backup_purge`: privacy deletion to backup purge/restore-block attestation.
- `monitoring`: metrics, logs, tracing, error reporting, alerts and incident runbook proof.
- `security_review`: external security/privacy review outcome.

## Ops Proof Templates

Generate template-only private starting files when needed:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/create_external_ops_proof_template.py \
  --proof-type all \
  --output-dir evidence/private_outputs
```

The generated files are still `template_only=true` and
`production_quality_candidate_signal=false`. They are not proof until a human
operator replaces them with redacted results from real deployment, backup,
monitoring and security-review execution.

## Dry-Run Shape Check

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py --dry-run --output /tmp/careeragent-v35-provider-proof-dry-run.json
```

Dry-run output must report `provider_mode=dry_run` and `production_quality_candidate_signal=false`. It is only a schema/secret-leak check.

## Provider Proof Readiness

Private provider execution requires:

```bash
export AI_PROVIDER_MODE=provider_verified
export LLM_PROVIDER=openai_compatible
export LLM_BASE_URL=...
export LLM_MODEL=...
export LLM_API_KEY=...
export EMBEDDING_PROVIDER=openai_compatible
export EMBEDDING_BASE_URL=...
export EMBEDDING_MODEL=...
export EMBEDDING_API_KEY=...
export DATA_ENCRYPTION_KEY=...
export AUTH_JWT_SECRET=...
PYTHONPATH=backend backend/.venv/bin/python scripts/check_provider_proof_readiness.py
```

Then run:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py \
  --provider openai_compatible \
  --llm-base-url "$LLM_BASE_URL" \
  --llm-model "$LLM_MODEL" \
  --embedding-base-url "$EMBEDDING_BASE_URL" \
  --embedding-model "$EMBEDDING_MODEL" \
  --output evidence/private_outputs/provider_proof.$(date +%Y%m%d-%H%M%S).json \
  --redact \
  --fail-on-not-verified
```

The generated proof must stay in ignored private outputs or `/tmp`.

## Human Review Proof

Use the v3.5-B importer for formal external reviewer batches:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/import_human_review_batch.py \
  --input /tmp/careeragent-v35b-human-review.csv \
  --output evidence/private_outputs/human_review_batch.$(date +%Y%m%d-%H%M%S).json \
  --batch-id human-review-v35b-real-batch \
  --dataset-name anonymized_v35b_external_review \
  --sampling-method stratified_by_task_type_and_risk \
  --reviewer-role external_ai_quality_reviewer \
  --privacy-sanitized
```

Then summarize:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/summarize_human_review_evidence.py \
  --input evidence/private_outputs/human_review_batch.real.json \
  --output /tmp/careeragent-v35b-human-review-summary.json
```

Templates and dry-runs are not human review proof. The evidence package validator must report `human_review_candidate_passed` before this blocker can be considered resolved.

## Private Evidence Validation

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py --evidence-dir evidence/private_outputs --output /tmp/careeragent-v35-evidence-summary.json
```

The validator reports blockers for production-ready candidate and
production-readiness certified status. It distinguishes:

- `missing_deployment`, `deployment_template_only`, `deployment_thresholds_failed`, `deployment_candidate_passed`
- `missing_backup_purge`, `backup_purge_template_only`, `backup_purge_thresholds_failed`, `backup_purge_candidate_passed`
- `missing_monitoring`, `monitoring_template_only`, `monitoring_thresholds_failed`, `monitoring_candidate_passed`
- `missing_security_review`, `security_review_template_only`, `security_review_thresholds_failed`, `security_review_candidate_passed`

Summary JSON, validator output JSON and other non-proof files are ignored as
non-proof artifacts, but every JSON file is still scanned for secret-like
material. Missing external proofs are expected until real external evidence is
collected.

## Completion Boundary

v3.5 is complete when the repository has safe evidence schemas, templates, checklists, scripts, tests and documentation. It is not complete as production readiness until real external proofs are collected and a later read-only certification audit passes.
