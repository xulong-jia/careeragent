# v3.5 Human Review Checklist

- [ ] Review dataset is anonymized and approved for reviewer access.
- [ ] At least two independent reviewers are used for comparable cases.
- [ ] `dataset_name`, `sampling_method` and reviewer roles are recorded.
- [ ] Reviewer identifiers are already hashed or redacted before import.
- [ ] `scripts/import_human_review_batch.py --dry-run` passes without writing private output.
- [ ] Item-level correctness, groundedness, safety and usefulness scores are present.
- [ ] Hallucination, fabrication and privacy risk flags are present.
- [ ] Disagreements requiring adjudication are counted and completed.
- [ ] Privacy review passes for all included rows and `privacy_sanitized=true`.
- [ ] `scripts/summarize_human_review_evidence.py` reports thresholds passing.
- [ ] `scripts/validate_external_evidence_package.py` reports `human_review_candidate_passed`.
- [ ] Raw reviewer notes and private case text stay outside Git.

Completion boundary: internal sample rows, single-reviewer checks or synthetic-only review do not certify production quality.
