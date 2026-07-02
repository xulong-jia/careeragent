# Deployment Proof Runbook

This runbook collects external deployment evidence. It does not create proof by itself.

## Prepare

- A production-like or production deployment for the audited Git commit.
- Managed database, secret manager and KMS/encryption key controls.
- TLS endpoint, backend `/live` and `/ready` endpoints, migration logs and rollback plan.
- A private output path under `evidence/private_outputs/`.

## Execute

1. Deploy the audited commit to the target environment.
2. Run migrations and record the redacted migration status.
3. Verify `/live`, `/ready`, frontend smoke flow and API smoke tests.
4. Verify managed DB, secret manager, KMS/encryption key, TLS and rollback plan.
5. Copy `evidence/templates/deployment_proof.template.json` to `evidence/private_outputs/`.
6. Replace template fields with redacted real evidence refs.
7. Set `template_only=false` or remove it only after real checks pass.
8. Set `production_quality_candidate_signal=true` only when all deployment checks pass.

## Render Backend Notes

- Deploy the backend as a Render Docker web service from `backend/`.
- The backend container listens on `0.0.0.0` and reads `PORT` from the runtime environment, defaulting to `8000` for local Docker/prod-like compose.
- Use `/ready` as the Render health check path so database reachability and Alembic head status are checked before treating the service as ready.
- Inject `DATABASE_URL`, `AUTH_JWT_SECRET`, `DATA_ENCRYPTION_KEY`, `DATA_ENCRYPTION_KEY_ID` and `BACKEND_CORS_ORIGINS` through Render environment variables or secret management. Do not commit real values.
- Use the deployed backend URL as the frontend `VITE_API_BASE_URL` when deploying the frontend as a Render static site.

## Counts As Proof

- Redacted cloud deployment run id or release id.
- Redacted app URL proof with TLS enabled.
- Health/readiness/smoke-test result refs.
- Migration and rollback verification refs.
- Managed DB, secret manager and KMS/encryption key evidence refs.

## Does Not Count

- Local Docker Compose output.
- Template JSON with `template_only=true`.
- Screenshots or logs containing account ids, credentials, raw user data or database URLs.
- A deployment that was not tied to the audited commit.

## Validate

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35c-evidence-summary.json
```

The deployment status must be `deployment_candidate_passed`.

## Failure Handling

Keep failed proof attempts in `evidence/private_outputs/` or `/tmp` only. Do not commit them. Fix the deployment, rerun checks, and produce a new redacted private proof.
