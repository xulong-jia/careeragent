# Provider Proof Runbook

This runbook prepares a redacted external provider proof. It must not commit provider keys, provider traces, raw prompts, resume text, JD text, RAG chunks or interview answers.

## Dry Run

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py --dry-run --output /tmp/careeragent-v35-provider-proof-dry-run.json
```

Expected boundary:

- `provider_mode` is `dry_run`.
- `production_quality_candidate_signal` is `false`.
- No secret-like value appears in the JSON.

## Required Private Environment

Prepare these values only in a private shell, CI secret store or cloud secret manager:

```bash
export AI_PROVIDER_MODE=provider_verified
export LLM_PROVIDER=openai_compatible
export LLM_BASE_URL=...
export LLM_MODEL=...
export LLM_API_KEY=...
export EMBEDDING_PROVIDER=openai_compatible
export EMBEDDING_BASE_URL=...
export EMBEDDING_MODEL=...
export EMBEDDING_API_KEY=...
export DATA_ENCRYPTION_KEY=...
export AUTH_JWT_SECRET=...
```

The checker does not call the provider and does not print keys:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/check_provider_proof_readiness.py
```

`readiness_status=ready` means the private environment is shaped correctly. It is not provider proof.

## Real External Run

Write the proof to ignored private outputs:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_external_provider_proof.py \
  --provider openai_compatible \
  --llm-base-url "$LLM_BASE_URL" \
  --llm-model "$LLM_MODEL" \
  --embedding-base-url "$EMBEDDING_BASE_URL" \
  --embedding-model "$EMBEDDING_MODEL" \
  --output evidence/private_outputs/provider_proof.$(date +%Y%m%d-%H%M%S).json \
  --redact \
  --fail-on-not-verified
```

The runner validates LLM reachability, embedding reachability and dimension, LLM structured JSON schema output, a synthetic grounded RAG answer with citation, an advisory LLM judge schema output, timeout configuration and secret leakage. It maps localhost proof to `provider_mode=fake`; fake proof is test-only and cannot support production readiness.

## Failure Diagnosis

- `readiness_status=missing_required_env`: export the missing variables.
- `readiness_status=unsafe_config`: replace placeholder/dev secrets or localhost URLs.
- `provider_mode=not_verified`: inspect the redacted `source_provider_probe` status and provider endpoint configuration.
- `rag_grounded_answer_sample_passed=false`: the LLM did not return cited grounded JSON for the safe sample.
- `llm_judge_sample_passed=false`: the LLM judge advisory schema failed.
- `secret_leak_check_passed=false`: delete the output from private storage and rotate any exposed secret.

Do not commit proof output, provider keys, raw prompts, provider traces or screenshots.

## AI Quality Certification Input

Pass the private proof path to AI quality certification:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_ai_quality_certification.py \
  --eval-dir /tmp/careeragent-v35a-anonymized \
  --provider-proof evidence/private_outputs/provider_proof.real.json \
  --output-dir /tmp/careeragent-ai-quality-v35a
```

If `provider_mode != external_verified`, the report must keep `production_quality_candidate=false` and list blockers.

After provider proof, proceed to human review proof with `docs/human-review-proof-runbook.md`.

## Acceptance Boundary

The provider proof can support candidate review only when it reports:

- `provider_mode=external_verified`
- embedding and LLM validation passed
- schema validation passed
- timeout/retry validation passed
- grounded RAG and LLM judge sample probes passed
- secret leak check passed
- `production_quality_candidate_signal=true`

Offline, deterministic, local, mocked or dry-run output cannot satisfy this boundary.
