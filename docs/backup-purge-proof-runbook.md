# Backup Purge Proof Runbook

This runbook collects external backup, restore and privacy deletion evidence. It does not create proof by itself.

## Prepare

- Managed database backup settings and retention policy.
- A synthetic or approved anonymized deletion test subject.
- Privacy delete-all output for the same subject.
- Restore drill environment and legal hold behavior documentation.
- A private output path under `evidence/private_outputs/`.

## Execute

1. Verify a managed database backup exists for the target environment.
2. Run a restore test in an isolated environment.
3. Execute delete-all for the approved test subject.
4. Verify backup purge or retention expiry handling for the deleted subject.
5. Verify legal hold behavior and restore-after-delete blocking or redaction.
6. Copy `evidence/templates/backup_purge_proof.template.json` to `evidence/private_outputs/`.
7. Fill only redacted evidence refs and boolean outcomes.
8. Set `production_quality_candidate_signal=true` only when all backup purge checks pass.

## Counts As Proof

- Redacted backup policy and restore drill refs.
- Delete-all proof id for the approved test subject.
- Evidence that restored backups cannot reintroduce deleted private data after purge or redaction.
- Legal hold behavior review.

## Does Not Count

- Application delete API output alone.
- Template JSON with `template_only=true`.
- Raw backup ids, customer ids, legal documents or deletion logs committed to Git.
- A restore test that does not check deleted-subject behavior.

## Validate

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35c-evidence-summary.json
```

The backup purge status must be `backup_purge_candidate_passed`.

## Failure Handling

If restore, purge, legal hold or retention behavior fails, keep the failed evidence private, document the blocker, and rerun after the backup policy is corrected.
