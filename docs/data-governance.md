# CareerAgent Data Governance v3.1

CareerAgent handles sensitive job-search data: resumes, JD interpretation, RAG documents/chunks, interview answers, application notes, project rewrites, bad cases and evaluation artifacts. v3.0 added application-level encryption/redaction/RBAC/delete proof foundation; v3.1 adds production-like database and operations controls.

## Protected Data

Sensitive fields include:

- resume raw text and parsed private content;
- JD raw text;
- RAG document raw text, chunk text and answer run private fields;
- interview answers;
- application notes, reflection, status notes and interview notes;
- project rewrite inputs/outputs that may reveal private work history;
- bad case descriptions and expected/actual behavior;
- evaluation case/result payloads.

## Controls

- Encryption-at-rest foundation: Fernet envelope encryption for main sensitive DB write paths.
- Key id: `DATA_ENCRYPTION_KEY_ID` recorded with encrypted envelopes.
- Production validation: `APP_ENV=production` requires valid non-local `DATA_ENCRYPTION_KEY`.
- Access control: protected APIs require bearer auth and workspace membership role checks.
- RBAC: viewer is read-only; member can mutate ordinary business objects; owner/admin can access privacy delete and audit endpoints.
- Redaction: logs, audit metadata and eval payloads use redaction helpers and must not store raw private text.
- Deletion proof: privacy delete supports dry-run and execute proof ids.
- Operations: production DB must be PostgreSQL-compatible; `/ready` checks DB reachability and migration state.

## Delete Proof Boundary

Application deletion proof covers active application database rows in the current workspace/user scope. It does not automatically purge:

- database backups;
- object storage;
- provider traces;
- exported files;
- local screenshots;
- centralized logs;
- external job boards or email systems.

Those systems require the retention/backup policy in `docs/retention-backup-policy.md`.

## Future Hardening

Not yet production-certified:

- KMS/HSM integration;
- multi-key decrypt and automatic rotation/backfill;
- database RLS;
- immutable audit/SIEM export;
- legal hold workflow;
- automated backup purge attestation;
- SSO/MFA/session/device management;
- frontend privacy-safe display and E2E proof.

Status: v3.1 production data governance foundation, not production-readiness certified.
