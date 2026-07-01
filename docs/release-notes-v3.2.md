# CareerAgent v3.2 Release Notes

Status: production AI quality foundation candidate, not production-ready.

## Added

- Semantic embedding provider metadata and offline `local_semantic` provider path.
- RAG reranker contract with `none`, `local_score`, and provider-score modes.
- Optional `llm_grounded` RAG answer mode with schema validation, citation checks,
  prompt/model metadata, fallback metadata, and no-evidence refusal.
- Optional `llm_parser` resume parse mode plus OCR/table/bilingual resume
  foundation metadata.
- 100-case synthetic benchmark dataset and runner support.
- Human review, match calibration, score stability, and bad-case regression trend
  evaluation helpers.

## Quality Gates

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest -p no:cacheprovider backend/tests
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset synthetic --output-dir /tmp/careeragent-evals-synthetic-v32
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --output-dir /tmp/careeragent-evals-service-v32
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --output-dir /tmp/careeragent-evals-benchmark-v32
```

## Boundary

v3.2 does not enable real provider network calls by default and does not use real
private data. Passing the synthetic benchmark is not production-readiness
certification. v3.3 frontend productization and v3.4 final read-only audit remain
required.
