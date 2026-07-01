# CareerAgent Phase 2.6 Security / Privacy / Deployment Hardening

阶段 2.6 把 CareerAgent 从前序 production foundation 推进到 security / privacy / deployment production foundation。它仍不是 production-ready，也不代表可以直接处理真实敏感求职材料。

## Scope

已补齐的 hardening foundation：

- Config validation：`APP_ENV=production` 启动时拒绝空、过短或 dev-only / replace-me / change-me / placeholder `AUTH_JWT_SECRET`，拒绝 SQLite production database URL，并拒绝 `*` CORS。
- Config summary：readiness 只返回 masked secret/provider config、database driver、token expiry 和 feature flags，不返回 secret value。
- Health/readiness：`GET /health` 继续作为 alive check；`GET /ready` 和 `GET /api/ready` 检查 DB reachability 与 runtime config validity。
- Structured logging：新增 `careeragent` JSON log event，request middleware 记录 request_id、method、path、status_code 和 duration_ms，不记录 body。
- Redaction：集中 masking email、phone、JWT、API key、secret/token 字段和长 raw text；统一错误响应 details 经过 redaction。
- Data deletion summary/proof：`GET /api/privacy/delete-summary` 预览当前 user/workspace 可删除资源计数；`DELETE /api/privacy/delete-all` 返回 `deletion_proof_id`、resource-level counts 和 backup/retention limitation note。
- Audit foundation：register/login、Agent run create/resume/retry/cancel、Evaluation run、Bad Case create 和 privacy delete-all 写入 privacy-safe `audit_logs` metadata。
- PostgreSQL production boundary：SQLite 明确只允许 local dev/test；production runtime validation 要求 PostgreSQL-compatible `DATABASE_URL`。

## Runtime Config Rules

Local development may use `.env.example`:

```bash
AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars
DATABASE_URL=sqlite:///./local_data/careeragent.db
APP_ENV=development
```

Production must inject runtime config from a trusted environment or secret manager:

```bash
APP_ENV=production
AUTH_JWT_SECRET=<strong random secret, at least 32 chars>
DATABASE_URL=postgresql+psycopg://...
BACKEND_CORS_ORIGINS=https://your-frontend.example
```

Do not store real DB credentials, provider keys, JWT secrets, resumes, JDs, RAG documents, application records, interview notes or evaluation outputs in committed files.

## Privacy Boundary

The current system reduces accidental exposure but does not provide full compliance:

- Resume/JD/RAG `raw_text` can still be stored in plaintext database columns.
- There is no production encryption-at-rest implementation, key management, key rotation or legal hold workflow.
- Deletion proof covers active database rows in the current workspace only.
- Backup purge, log retention, exported artifacts and external provider deletion are documented gaps.
- API responses should continue using preview/ref/summary shapes, not full raw payloads.

## Observability Boundary

Structured logs are request-level foundation:

- Include request_id for correlation.
- Include event name, HTTP path/status/duration and sanitized metadata.
- Exclude request/response body, Authorization headers, raw_text, full answer text, chunk text and provider payloads.
- `/ready` exposes masked config summary and DB/config status.

This is not centralized observability, SIEM, alerting, tracing, metrics SLO, or audit pipeline.

## Data Deletion / Retention Boundary

The privacy delete-all flow covers the current user/workspace business objects:

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

## Quality Gates

Phase 2.6 gates are listed in `docs/quality-gates.md`. Required checks include backend tests, synthetic/service-level eval, frontend build, Docker config positive/negative secret checks, Alembic upgrade, diff hygiene, ignore/artifact scan, secret scan, readiness tests, redaction tests and privacy deletion tests.

## Remaining Gaps

- Raw text encryption interface / encryption-at-rest is still missing.
- PostgreSQL deployment is enforced for production config but not provisioned by this repository.
- RBAC remains role foundation only; no full policy engine, SSO, MFA, refresh-token rotation or session/device management.
- Observability remains structured local logs and readiness endpoints; no centralized log pipeline or alerts.
- Frontend still lacks full lint/minimal UI test coverage and object selector replacement for every ID-driven workflow.
- Backup, restore, retention, legal hold and backup erasure proof remain future production-readiness work.

阶段完成标准：Security / Privacy / Deployment 达到 production foundation，不得称为 production-ready。
