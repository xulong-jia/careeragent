# v3.5 External Provider Checklist

- [ ] Provider keys are loaded only from private runtime env or secret manager.
- [ ] `scripts/check_provider_proof_readiness.py` reports `readiness_status=ready` without printing secrets.
- [ ] `scripts/run_external_provider_proof.py` ran with real provider config outside Git.
- [ ] Embedding probe passed against the intended production embedding model.
- [ ] LLM structured output probe passed against the intended production LLM model.
- [ ] Proof output reports `provider_mode=external_verified`, not `dry_run`, `fake` or `not_verified`.
- [ ] Timeout/retry behavior was validated by the runner and redacted evidence.
- [ ] Grounded RAG answer sample probe passed with source refs and no raw private text committed.
- [ ] LLM judge advisory probe passed with schema validation.
- [ ] Output JSON was stored under `evidence/private_outputs/` or `/tmp`, not tracked by Git.
- [ ] Secret scan passed on the generated proof.

Completion boundary: dry-run, offline, local deterministic, mocked or synthetic provider output is not external provider proof.
