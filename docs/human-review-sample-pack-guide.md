# Human Review Sample Pack Guide

This guide prepares a blank, anonymized CSV for external reviewers. It does not create human review proof and must not contain reviewer scores, raw resumes, raw JDs, provider traces, API keys or private user data.

## Generate A Pack

Dry-run first:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_human_review_sample_pack.py \
  --sample-size 30 \
  --seed 35 \
  --dry-run
```

Write the real reviewer packet only to ignored private outputs:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_human_review_sample_pack.py \
  --sample-size 30 \
  --seed 35 \
  --output evidence/private_outputs/human_review_sample_pack.$(date +%Y%m%d-%H%M%S).csv
```

The committed template at `evidence/templates/human_review_sample_pack.template.csv` is only a placeholder. It is not real review evidence.

## Reviewer Instructions

Reviewers must not edit `item_id`, `task_type`, `anonymized_input_ref` or `model_output_ref`.

Reviewers fill only:

- `reviewer_id_hash`
- `correctness_score`
- `groundedness_score`
- `safety_score`
- `usefulness_score`
- `privacy_risk_flag`
- `hallucination_flag`
- `fabrication_flag`
- `reviewer_comment`
- `decision`
- `requires_adjudication`
- `adjudication_decision`
- `bad_case_ref`

Scores use decimals from `0.0` to `1.0`. `decision` must be one of `pass`, `minor_issue`, `major_issue` or `fail`.

## Privacy Boundary

The reviewer packet must expose only anonymized refs. Reviewers must not receive API keys, provider traces, real resumes, real JDs, interview answers, emails, phone numbers, names, private company identifiers or raw RAG chunks through this CSV.

After reviewers complete the CSV, store the returned file outside Git and import it with `scripts/import_human_review_batch.py`.
