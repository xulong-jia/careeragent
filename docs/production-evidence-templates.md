# CareerAgent Production Evidence Templates

These templates define the evidence required for final production readiness. They are not completed proof.

## Cloud Deployment Proof

Required fields:

- provider:
- region:
- service:
- image digest:
- git commit:
- domain:
- TLS certificate issuer and expiry:
- backend readiness URL:
- frontend URL:
- migration command and revision:
- rollback procedure tested:
- proof artifact links:

## Managed PostgreSQL Proof

- provider and instance class:
- PostgreSQL version:
- pgvector availability:
- private networking:
- automated backup policy:
- restore drill timestamp:
- migration revision:
- connection pool limits:
- monitoring dashboard:

## Secret Manager / KMS Proof

- secret manager provider:
- secrets stored:
- access principals:
- KMS key id:
- rotation period:
- last rotation proof:
- break-glass owner:
- audit log export:

## Key Rotation Backfill Plan

1. Add new `DATA_ENCRYPTION_KEY_ID`.
2. Deploy multi-key decrypt support.
3. Re-encrypt sensitive rows in batches.
4. Verify row counts and random decrypt samples.
5. Retire old key after retention window and legal hold review.

Current repo status: single active key foundation only. Multi-key decrypt/backfill remains future hardening.

## Backup Purge / Legal Deletion Attestation

Required fields:

- deletion proof id:
- user/workspace scope:
- active DB deletion timestamp:
- affected backup ids:
- backup purge status:
- retention expiry:
- legal hold status:
- restore block rule:
- operator:
- audit artifact:

Do not mark `backup_purge_status=complete` unless the managed backup system has actually purged or expired the affected backup.

## Observability Proof

- log drain destination:
- metrics backend:
- tracing backend:
- error reporting project:
- alert rule ids:
- on-call owner:
- privacy redaction review:
- incident drill timestamp:
