# Provider Proof Runbook

This runbook prepares a redacted external provider proof. It must not commit provider keys, provider traces, raw prompts, resume text, JD text, RAG chunks or interview answers.

## Dry Run

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py --dry-run --output /tmp/careeragent-v35-provider-proof-dry-run.json
```

Expected boundary:

- `provider_mode` is `not_verified`.
- `production_quality_candidate_signal` is `false`.
- No secret-like value appears in the JSON.

## Real External Run

Load provider config from a private shell, CI secret store or cloud secret manager. Then write the proof to ignored private outputs:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py \
  --provider openai_compatible \
  --embedding-model provider-embedding-model-name \
  --llm-model provider-llm-model-name \
  --timeout-retry-validation-passed \
  --rag-grounded-answer-sample-passed \
  --llm-judge-sample-passed \
  --output evidence/private_outputs/provider_proof.real.json
```

Only set the three `--*-passed` flags after the corresponding external evidence has been reviewed. The script does not prove timeout/retry, grounded RAG or LLM judge quality by itself.

## Acceptance Boundary

The provider proof can support candidate review only when it reports:

- `provider_mode=provider_verified`
- embedding and LLM validation passed
- schema validation passed
- timeout/retry evidence attached
- grounded RAG and LLM judge sample evidence attached
- secret leak check passed
- `production_quality_candidate_signal=true`

Offline, deterministic, local, mocked or dry-run output cannot satisfy this boundary.
