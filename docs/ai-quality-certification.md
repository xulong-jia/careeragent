# CareerAgent AI Quality Certification Foundation

This document defines the v3.4 rework evidence for AI quality certification. It does not claim production AI quality by itself.

## Provider Proof

Use:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_ai_providers.py --output /tmp/careeragent-provider-proof.json
```

With no provider secrets, the script returns `provider_mode=offline`. With real OpenAI-compatible or Qwen-compatible LLM and embedding config, it validates:

- LLM structured output schema;
- embedding vector dimension and non-zero response;
- timeout-safe provider path;
- masked base URL and key handling;
- `private_data_used=false`.

Use `--require-provider` only in a private production-like proof run. Never commit real provider proof containing prompts, responses, keys or private data.

## Anonymized Benchmark

`evals/datasets/anonymized_benchmark/` contains 155 manually curated anonymized real-world-style cases:

- 50 JD parser cases;
- 30 resume parser cases;
- 15 RAG retrieval cases;
- 15 RAG answer cases;
- 15 match cases;
- 15 project rewrite cases;
- 15 agent workflow cases.

Every case carries `case_id`, `source_type`, `anonymization_note`, `expected_output`, `difficulty`, `reviewer_required` and `privacy_check_passed`.

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset anonymized_benchmark --output-dir /tmp/careeragent-anonymized-eval
```

## Certification Report

Generate:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_ai_quality_certification.py \
  --eval-dir /tmp/careeragent-anonymized-eval \
  --provider-proof /tmp/careeragent-provider-proof.json \
  --output-dir /tmp/careeragent-ai-quality-report
```

`production_quality_candidate` is true only when provider proof is `provider_verified`, benchmark pass rate is high, human agreement is acceptable and judge hallucination rate is within threshold.

## Remaining Limits

- The committed dataset is privacy-safe and manually curated; it is not a dump of real user data.
- External provider runs, external human reviewers and private benchmark artifacts must remain outside Git.
- LLM judge is advisory and cannot override human review.
