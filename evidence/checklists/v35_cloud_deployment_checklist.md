# v3.5 Cloud Deployment Checklist

- [ ] Production commit SHA matches the audited source revision.
- [ ] Service is deployed in the intended cloud region.
- [ ] Managed PostgreSQL or equivalent production database is configured.
- [ ] Secret manager injects auth, data encryption and provider secrets.
- [ ] KMS or managed key controls are documented for encryption keys.
- [ ] TLS is enabled and externally verified.
- [ ] `/live`, `/ready` and `/metrics` checks are validated from the deployment.
- [ ] Rollback was tested or rehearsed with redacted evidence.
- [ ] Cloud logs and screenshots are redacted before private storage.

Completion boundary: local Docker Compose, prod-like config and dry-run deployment validation remain foundation only.
