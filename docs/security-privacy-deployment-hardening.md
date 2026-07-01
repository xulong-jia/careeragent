# CareerAgent v3.0 Security / Privacy / Data Governance

v3.0 在 2.6 security/privacy/deployment foundation 之上，补齐应用层敏感数据加密、token revoke、RBAC role gate、删除 proof dry-run/execute 和更严格 audit/redaction。当前状态是 security/privacy/data-governance production foundation candidate，不是 production-ready，也不是合规删除或企业级安全认证。

## Scope

已完成的 v3.0 foundation：

- Application-layer encryption-at-rest：新增 `app.core.crypto` Fernet envelope，写入时保存 `{v,key_id,alg,ciphertext}`，读取时兼容 legacy plaintext。
- Sensitive DB fields：Resume `raw_text`、JD `raw_text`、RAG document/chunk/answer run、Interview answer、Application notes/interview_notes/reflection/status note、Bad Case free text 写入加密字段。
- Evaluation privacy：Evaluation case/result JSON payload 写入前 redaction；Bad Case 派生 eval 的 summary 类字段也走 redaction。
- Key foundation：新增 `DATA_ENCRYPTION_KEY` / `DATA_ENCRYPTION_KEY_ID`；production runtime 拒绝缺失、无效或本地 dev key。
- Token/session foundation：access token 增加 `jti`；`POST /api/auth/logout` 写入 `revoked_tokens`，被 revoke 的 token 返回 `token_revoked`。
- RBAC foundation：workspace membership role 驱动 route permission gate；viewer 只读，member 可写基础业务，owner/admin 可执行 privacy delete 和 audit log 查看。
- Audit foundation：mutating protected API 写入 action/ref/count metadata，不记录 request body；audit metadata 会转 JSON-safe 并 redaction。
- Privacy delete proof：`DELETE /api/privacy/delete-all?dry_run=true` 返回 dry-run proof；execute 返回 `deletion_proof_id`、before counts、deleted counts、retained records、audit event id、backup purge limitation。
- Runtime hardening：沿用 2.6 production validation、masked config summary、structured request logging、redacted errors、readiness checks 和 production SQLite rejection。

## Runtime Config Rules

Local development may use `.env.example`:

```bash
APP_ENV=development
AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars
DATA_ENCRYPTION_KEY=<dev-only Fernet key from .env.example>
DATA_ENCRYPTION_KEY_ID=local-dev-v1
DATABASE_URL=sqlite:///./local_data/careeragent.db
```

Production must inject runtime config from a trusted environment or secret manager:

```bash
APP_ENV=production
AUTH_JWT_SECRET=<strong random secret, at least 32 chars>
DATA_ENCRYPTION_KEY=<strong Fernet key generated for production>
DATA_ENCRYPTION_KEY_ID=<stable production key id, e.g. prod-2026-07-v1>
DATABASE_URL=postgresql+psycopg://...
BACKEND_CORS_ORIGINS=https://your-frontend.example
```

Do not store real DB credentials, provider keys, JWT secrets, encryption keys, resumes, JDs, RAG documents, application records, interview notes or evaluation outputs in committed files.

## Encryption Boundary

v3.0 protects the main sensitive application fields at the repository/service write path. It does not claim complete enterprise key management:

- Existing legacy plaintext rows are readable for compatibility, but v3.0 does not include an automatic backfill migration that rewrites historical rows.
- Only the active configured Fernet key can decrypt current envelopes; multi-key decrypt, KMS integration and automated rotation jobs are future hardening.
- Database/filesystem/cloud provider encryption, managed backup encryption and object-store encryption remain deployment responsibilities.
- Evaluation payloads are redacted rather than encrypted so test result contracts remain inspectable without raw private text.

## Privacy Boundary

The system reduces accidental exposure but is not a legal compliance product:

- Default Resume/JD/RAG responses still expose short masked previews only, not full raw payloads.
- Application and Bad Case detail APIs return decrypted values to the authorized current user/workspace context; UI-level privacy-safe display is a v3.3 productization requirement.
- Deletion proof covers active database rows in the current app database scope. It does not purge backups, logs, exported files, local screenshots, provider traces or external systems.
- Audit logs retain redacted tombstones for governance trail.

## Data Deletion / Retention Boundary

The privacy delete-all flow covers current scoped business objects:

- profiles, resumes, resume_versions
- job_descriptions, job_profiles
- match_reports, projects, project_rewrites
- interview_questions, interview_answers
- study_plans
- applications, application_status_history
- rag_documents, rag_chunks, rag_answer_runs
- agent_runs, agent_steps
- bad_cases, evaluation_runs, evaluation_cases, evaluation_results

The returned `deletion_proof_id` is an application-level proof identifier, not a legal deletion certificate. Backups, logs, manually exported files, external AI provider traces and deployment-platform retention still need a production policy.

## Observability Boundary

Structured logs are request-level foundation:

- Include request_id for correlation.
- Include event name, HTTP path/status/duration and sanitized metadata.
- Exclude request/response body, Authorization headers, raw_text, full answer text, chunk text and provider payloads.
- `/ready` exposes masked config summary and DB/config status.

This is not centralized observability, SIEM, alerting, tracing, metrics SLO, or audit pipeline.

## Remaining Gaps

- No KMS/HSM integration, no multi-key decrypt set, no online key rotation/backfill job.
- No refresh token rotation, session/device management, SSO or MFA.
- RBAC is route-level role foundation, not a full policy engine or database RLS.
- v3.1 adds backup/restore scripts and retention policy docs; automated backup purge, legal hold and deletion attestation remain future production hardening.
- Audit logs are DB-local redacted records, not centralized immutable audit/SIEM.
- Frontend privacy-safe display, selectors and E2E coverage remain v3.3 work.
- Production AI quality, semantic provider, large benchmark and human review remain v3.2 work.

阶段完成标准：v3.0 达到 Security / Privacy / Data Governance production foundation candidate；不得称为 production-ready。
