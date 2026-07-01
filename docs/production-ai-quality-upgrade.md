# CareerAgent v3.2 Production AI Quality Upgrade

v3.2 upgrades CareerAgent from local AI foundation toward production AI quality
foundation. It does not certify production-ready AI.

## What Changed

- Embedding provider metadata now records provider/model/dim/version,
  provider config id, vector source, semantic flag, input hash, and created_at.
- Added `LocalSemanticEmbeddingProvider` as an offline semantic-provider-shaped
  test/foundation path, plus OpenAI-compatible embedding retry support.
- RAG search supports a reranker contract through `RAG_RERANKER_MODE=none|local_score|provider`.
- `POST /api/rag/answer` accepts `answer_mode=deterministic_summary|llm_grounded`.
  `llm_grounded` uses a schema-validated provider output contract, grounded
  citations, prompt/model metadata, fallback metadata, and no-evidence refusal.
- Resume parse supports `parser_mode=deterministic|llm_parser` on the parse API.
  The LLM parser path remains opt-in and schema-validated.
- Resume parser metadata now records OCR unsupported status plus table/bilingual
  layout foundation signals and warnings.
- Added synthetic 100-case `benchmark` dataset covering parser, RAG retrieval,
  RAG answer, match, project rewrite, and agent workflow.
- Added human-review/calibration utilities for human agreement, score stability,
  bad-case candidate conversion, and bad-case regression trend.
- v3.3 frontend exposes retrieval mode and answer mode selectors in Knowledge
  Base and routes RAG answer refs through selectors in Interview, Study Plan and
  Agent flows. This is UX/productization only; it does not certify real provider
  quality.

## Commands

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --output-dir /tmp/careeragent-evals-benchmark-v32
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --module rag --output-dir /tmp/careeragent-evals-benchmark-rag-v32
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --module parser --output-dir /tmp/careeragent-evals-benchmark-parser-v32
```

The benchmark writes `summary.md`, `metrics.json`, `failed_cases.json`,
`actual_outputs.json`, `run_config.json`, and `human_review_summary.json`.

## Metrics Added

- RAG retrieval: `recall_at_k`, `mrr`, `precision_at_k`,
  `citation_coverage`, `source_type_match`, `no_evidence_refusal_accuracy`,
  `reranker_improvement_rate`.
- RAG answer: `groundedness`, `unsupported_claim_rate`,
  `citation_required_pass_rate`, `refusal_accuracy`, `answer_schema_pass_rate`.
- Match: `score_in_expected_range`, `ranking_consistency`,
  `evidence_completeness`, `gap_identification_precision`, `human_agreement`,
  `stability_delta`.
- Human review: reviewed count, mean absolute score delta, disagreement rate,
  human agreement rate, ranking consistency, score distribution, dimension
  disagreement.
- Bad-case trend: candidate count, reopened count, regression pass rate, and
  privacy-safe bad-case candidates.

## Runtime Boundary

Defaults remain offline:

```text
ENABLE_REAL_LLM=false
ENABLE_REAL_EMBEDDING=false
EMBEDDING_PROVIDER=local
RAG_RERANKER_MODE=none
RAG_ANSWER_MODE=deterministic_summary
```

Real provider paths require runtime secrets only. Do not commit `.env`, API keys,
provider traces, real resumes, real JDs, interview answers, RAG chunk text, or
eval outputs from private data.

## Still Not Production-Ready

- `LocalSemanticEmbeddingProvider` and benchmark fixtures are synthetic
  foundations, not proof of real semantic quality.
- No real anonymized production-sized JD/resume/RAG/match/agent dataset is
  committed.
- No LLM judge or formal human-review protocol is enabled as production gate.
- pgvector deployment exists from v3.1, but application-level pgvector semantic
  retrieval remains a production path to validate under real providers.
- OCR remains unsupported; v3.2 only adds explicit OCR provider boundary and
  layout signals.
- v3.3 frontend productization foundation is now present, but mocked E2E is not
  browser certification. v3.4 final read-only production readiness
  certification is still required before any production-ready tag.
