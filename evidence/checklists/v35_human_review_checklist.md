# v3.5 Human Review Checklist

- [ ] Review dataset is anonymized and approved for reviewer access.
- [ ] At least two independent reviewers are used for comparable cases.
- [ ] Rubric version is recorded and stable for the batch.
- [ ] Reviewer identifiers are redacted by `scripts/import_human_review_proof.py`.
- [ ] Agreement rate meets the production candidate threshold.
- [ ] Disagreements requiring adjudication are counted.
- [ ] Privacy review passes for all included rows.
- [ ] Raw reviewer notes and private case text stay outside Git.

Completion boundary: internal sample rows, single-reviewer checks or synthetic-only review do not certify production quality.
