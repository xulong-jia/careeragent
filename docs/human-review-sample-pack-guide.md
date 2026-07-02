# Human Review Sample Pack Guide

This guide prepares a blank, anonymized reviewer pack for external reviewers. It does not create human review proof and must not contain reviewer scores, raw resumes, raw JDs, provider traces, API keys or private user data.

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
  --format xlsx \
  --output evidence/private_outputs/human_review_sample_pack.$(date +%Y%m%d-%H%M%S).xlsx
```

Use `--format csv` when a machine-only CSV is needed. The reviewer-friendly `.xlsx` includes the `Human Review` sheet, frozen header row, filters, readable widths, wrapped long text, highlighted reviewer-entry columns and dropdown validation for booleans/decisions.

The committed template at `evidence/templates/human_review_sample_pack.template.csv` is only a placeholder. It is not real review evidence.

## Reviewer Instructions

Reviewers should read `task_type_label`, `input_summary`, `model_output_summary` and `review_instruction`.

Reviewers must not edit `review_batch_id`, `dataset_name`, `sampling_method`, `reviewer_role`, `privacy_sanitized`, `item_id`, `task_type`, `anonymized_input_ref` or `model_output_ref`.

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

Score guide:

- `1.0` = good
- `0.8` = minor issue
- `0.5` = major issue
- `0.0` = fail

Scores may use decimals from `0.0` to `1.0`. `decision` and `adjudication_decision` must be one of `pass`, `minor_issue`, `major_issue` or `fail`. Boolean fields must be `true` or `false`.

## Privacy Boundary

The reviewer packet must expose only anonymized refs. Reviewers must not receive API keys, provider traces, real resumes, real JDs, interview answers, emails, phone numbers, names, private company identifiers or raw RAG chunks through this CSV.

After reviewers complete the `.xlsx`, store the returned file outside Git. Export the `Human Review` sheet to CSV or JSONL before importing it with `scripts/import_human_review_batch.py`.
