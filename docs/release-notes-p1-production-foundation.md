# CareerAgent P1 Production Foundation Release Notes

P1 adds the first production-foundation layer for Auth, Workspace, Data Isolation, privacy operations, and PostgreSQL readiness. This is a checkpoint, not a production-ready claim.

## Included

- Auth endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`.
- Password/token security baseline: PBKDF2 password hash and HS256 bearer token signed by `AUTH_JWT_SECRET`.
- Workspace model: `users`, `workspaces`, `workspace_memberships`, and request-scoped current user/workspace context.
- Route protection: business `/api/*` routes require bearer token except health/register/login.
- Data isolation: owned repositories/services filter by current `user_id` and `workspace_id`; cross-user detail access returns not found or unauthorized.
- Privacy endpoints: `GET /api/privacy/export`, `DELETE /api/privacy/delete-all`, `GET /api/privacy/audit-log`.
- Frontend auth gate: login/register screen, token storage, Authorization header injection, logout, and 401 token cleanup.
- PostgreSQL readiness: `psycopg[binary]` dependency placeholder and documented PostgreSQL `DATABASE_URL` format.
- Documentation: README, architecture, API reference, database schema, safety checklist, and this P1 note.

## Not Included

- Full production RBAC, SSO, MFA, refresh token rotation, password reset, email verification, account recovery, or organization admin UI.
- Database row-level security, centralized audit/SIEM, production retention policy, backup erasure proof, or irreversible deletion proof.
- Managed PostgreSQL deployment, pgvector rollout, cloud secret manager, production observability, SLA, or incident response workflow.
- Real LLM/RAG/Agent/business feature expansion, automatic applications, recruitment website integration, or LLM judge.

## Operational Notes

- `AUTH_JWT_SECRET` is required. In `APP_ENV=production`, it must be at least 32 characters.
- `API_RATE_LIMIT_PER_MINUTE=0` disables the local in-process limiter. Set a positive value for a basic per-process guard; production should use an edge/API gateway limiter.
- Existing local SQLite rows are backfilled to default owner/workspace by migration for prototype continuity. A real production migration needs explicit user/workspace mapping.
- Privacy delete-all returns delete counts and records an audit event. It does not prove backup erasure or legal compliance.

## Verification Scope

P1 should be accepted only if backend tests, frontend build, Alembic upgrade from an empty DB, Docker Compose config, eval smoke, diff check, and artifact/secret scan pass or are explicitly reported as blocked by local infrastructure.
