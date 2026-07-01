# CareerAgent Session Security Foundation

v3.4 blocker rework adds session list/revoke foundation on top of bearer token auth.

## Backend

New session metadata is stored in `auth_sessions`:

- `session_id`
- `user_id`
- `workspace_id`
- `token_jti`
- `device_label`
- `issued_at`
- `expires_at`
- `revoked_at`
- `revoke_reason`

Endpoints:

- `GET /api/auth/sessions`
- `POST /api/auth/sessions/{session_id}/revoke`

Revoked sessions are denied by `get_current_user`, and revocation writes an `auth.session_revoke` audit event.

## Frontend

`AppShell` exposes a session menu showing active/revoked sessions and a revoke action. If the current session is revoked, local auth state is cleared and the user returns to sign-in.

## Tests

`backend/tests/test_p1_auth_workspace_isolation.py` covers:

- session list scoped to current user;
- current session marker;
- revoke session;
- revoked token/session denial;
- audit log creation.

## Boundary

Current implementation still stores the bearer token in `localStorage`. Production-readiness certification may still require httpOnly cookie + refresh token rotation, SSO/MFA, device risk controls and managed session policy.
