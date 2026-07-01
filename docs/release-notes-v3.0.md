# v3.0 Security / Privacy / Data Governance

v3.0 moves CareerAgent from a 2.6 security/privacy/deployment production foundation into a security/privacy/data-governance production foundation candidate. It is still not production-ready.

## Completed

- Added Fernet envelope encryption helpers with key id metadata and legacy plaintext read compatibility.
- Added `DATA_ENCRYPTION_KEY` / `DATA_ENCRYPTION_KEY_ID` config and production fail-fast validation.
- Encrypted repository/service write paths for Resume raw text, JD raw text, RAG document/chunk/answer-run private fields, Interview answers, Application notes/reflection/status notes, and Bad Case free text.
- Redacted Evaluation case/result JSON and Bad Case-derived summary fields before persistence.
- Added access token `jti`, `revoked_tokens`, logout revoke, and revoked-token rejection.
- Added route-level RBAC permission checks from `workspace_memberships.role`.
- Added mutating API audit foundation with JSON-safe redacted metadata.
- Enhanced privacy delete-all with `dry_run`, execute proof, retained records, audit event id, verification status, and backup purge limitation.
- Added tests for encryption envelope behavior, production config rejection, at-rest sensitive field protection, token revoke, RBAC gate, redaction, audit safety, and privacy proof behavior.

## Still Not Production-Ready

- No KMS/HSM integration, multi-key decrypt set, online key rotation or historical plaintext backfill migration.
- No production backup purge/restore/legal-hold runbook or deletion attestation.
- No SSO, MFA, refresh-token rotation, device/session management, DB RLS, centralized SIEM or immutable audit store.
- No production deployment proof, managed PostgreSQL runbook, metrics/tracing/alerting, or cloud secret manager integration.
- Core AI quality remains deterministic/local foundation until v3.2 semantic providers, large benchmark and human review.

Next recommended phase: v3.1 Production Deployment, Database & Operations Foundation.
