# CareerAgent Retention and Backup Policy v3.1

This policy defines the production target for backups, restores and deletion follow-up. The repository provides scripts and runbooks; the actual encrypted backup storage, retention scheduler and purge attestation must be implemented in the deployment platform.

## Active Data

Active application data lives in PostgreSQL in production. Privacy delete covers active rows for the scoped user/workspace and returns an application-level `deletion_proof_id`.

## Backups

Minimum production policy:

- create encrypted PostgreSQL backups with `scripts/db_backup.sh` or a managed database backup service;
- store backups outside the app container and outside Git;
- restrict backup read/restore permissions to production operators;
- record backup timestamp, DB revision, app commit, retention deadline and storage location;
- run restore drills before relying on the backup policy.

Recommended retention baseline:

- daily backups retained for 30 days;
- weekly backups retained for 12 weeks if business/legal requirements need longer recovery windows;
- no indefinite raw private data retention unless a legal hold is explicitly recorded.

## Backup Purge After Privacy Delete

When a user deletion executes:

1. Store the `deletion_proof_id` and deletion timestamp.
2. Mark backups created before that timestamp as containing deleted-user historical data.
3. Prevent those backups from being restored into production without re-running the deletion.
4. Let marked backups expire at the next retention window, unless legal hold applies.
5. Record purge/expiry evidence in the production audit system.

v3.4 rework adds a backup purge / legal deletion attestation template in
`docs/production-evidence-templates.md`. The repository still does not automate
managed backup purge. The privacy API and final audit must report this
limitation honestly unless an external managed backup proof is attached.

Required production attestation fields:

- `deletion_proof_id`;
- active DB deletion timestamp;
- affected backup ids;
- `backup_purge_status`;
- legal hold status;
- retention expiry;
- restore block rule;
- operator/auditor;
- immutable audit artifact.

Do not mark backup purge complete when the actual status is `not_implemented`,
`pending_retention_expiry` or `legal_hold`.

## Restore Rules

Use `scripts/db_restore.sh` only with explicit confirmation:

```bash
CONFIRM_RESTORE=restore BACKUP_FILE=/secure/backups/file.dump scripts/db_restore.sh
```

After any restore, operators must:

- run migrations to head;
- check `/ready`;
- re-apply any privacy deletes that occurred after the backup timestamp;
- run smoke/eval gates before reopening traffic.

## Repository Hygiene

Backups and dumps must not enter Git. `.gitignore` blocks:

- `backups/`
- `**/backups/`
- `*.dump`
- `*.backup`

Status: policy and attestation foundation. Production certification still requires platform-level backup encryption, retention automation and purge evidence.
