# v3.5 External Provider Checklist

- [ ] Provider keys are loaded only from private runtime env or secret manager.
- [ ] `scripts/run_external_provider_proof.py` ran with real provider config outside Git.
- [ ] Embedding probe passed against the intended production embedding model.
- [ ] LLM structured output probe passed against the intended production LLM model.
- [ ] Timeout and retry behavior was validated with redacted evidence.
- [ ] Grounded RAG answer sample was validated with source refs and no raw private text committed.
- [ ] LLM judge sample was validated with a documented rubric.
- [ ] Output JSON was stored under `evidence/private_outputs/` or `/tmp`, not tracked by Git.
- [ ] Secret scan passed on the generated proof.

Completion boundary: dry-run, offline, local deterministic, mocked or synthetic provider output is not external provider proof.
