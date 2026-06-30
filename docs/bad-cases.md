# CareerAgent v1.5B Bad Cases

This document is the stable entrypoint for Bad Case lifecycle and regression linkage. The detailed historical design remains in `docs/quality-review-design.md`.

## Lifecycle

Bad Case status supports:

- `open`
- `reviewing`
- `fixed`
- `verified`
- `wont_fix`

v1.5B fields include:

- `root_cause`
- `fix_strategy`
- `tags`
- `added_to_eval_set`
- `verified_at`
- `regression_evaluation_run_id`
- `regression_evaluation_case_id`

## Regression Linkage

`POST /api/bad-cases/{bad_case_id}/add-to-eval` creates or reuses a `source_type=bad_case` evaluation case in the default `regression` dataset and marks the Bad Case as added to the eval set.

When a linked regression case passes, the Bad Case can be marked `verified` with the latest evaluation run/case refs. When it fails, it remains unverified and `failed_case_ids` can trace the case.

## Privacy Boundary

Bad Cases store source refs and summaries. Do not store resume raw text, JD raw text, full RAG chunk text, full interview answers, credentials, private application materials, or other sensitive original content.
