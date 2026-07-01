# Human Review Proof Runbook

This runbook imports human review results into a redacted proof summary. Raw reviewer identity, private case text and private correction notes must remain outside Git.

## Input Template

Use `evidence/templates/human_review_input.template.csv` as the column contract. Required fields include reviewer id, rubric version, module, case id, human score, label, confidence, accepted/rejected flags, correction note and privacy review result.

## Import

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/import_human_review_proof.py \
  --input /tmp/careeragent-v35-human-review-input.csv \
  --output evidence/private_outputs/human_review_proof.real.json \
  --batch-id human-review-v3.5-real-batch
```

The importer redacts reviewer ids, counts cases/modules, computes comparable-case agreement and records adjudication requirements.

## Summary Only

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/summarize_human_review.py \
  --input /tmp/careeragent-v35-human-review-input.csv \
  --output /tmp/careeragent-v35-human-review-summary.json
```

## Acceptance Boundary

For production-ready candidate review, human review evidence must have at least two reviewers, meaningful case coverage, agreement at or above the project threshold, and `privacy_review_passed=true`.

Single-reviewer checks, internal smoke samples and synthetic-only review do not certify production AI quality.
