# Human Review Proof Runbook

This runbook creates a redacted external human review batch proof. It must not commit reviewer identities, raw resume text, JD text, RAG chunks, interview answers, provider traces, screenshots or private reviewer notes.

## Sampling

Use a documented sample from an anonymized benchmark or production-like review export. The default production-candidate threshold requires at least 30 review items. Cover the main task types: `jd_parse`, `resume_parse`, `match_score`, `rag_answer`, `project_rewrite` and `agent_workflow`.

Record `dataset_name` and `sampling_method` in every batch. Examples: `anonymized_v35b_external_review` and `stratified_by_task_type_and_risk`.

## Sample Pack Preparation

Generate the blank reviewer packet from the anonymized benchmark foundation:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_human_review_sample_pack.py \
  --sample-size 30 \
  --seed 35 \
  --format xlsx \
  --output evidence/private_outputs/human_review_fillable_simple_$(date +%Y%m%d-%H%M%S).xlsx
```

Use `--dry-run` to inspect the CSV-shaped content without writing a file. The reviewer-facing `.xlsx` is a conservative two-sheet workbook with `审核卡片` and `填写说明`. Reviewers edit only `审核卡片`; each sample is a vertical card with `item_id`, `审核类型`, `【匿名输入】`, `【模型输出】`, `【审核说明】` and a `请填写` section. The importer reads the reviewer-entered values from these cards and reconstructs machine refs from `item_id`. The workbook intentionally avoids formulas, data validation, named ranges, table objects, hidden sheets, cross-sheet references and dropdown validation for better Excel/WPS compatibility. The generated packet contains anonymized summaries only; it does not contain raw resume text, raw JD text, API keys, provider traces, real names, emails, phone numbers or private company identifiers.

Send separate copies of the same blank `.xlsx` to independent reviewers. For example, reviewer_01 fills one copy and reviewer_02 fills another copy. Reviewers must not see or copy each other's answers. Each reviewer must use a different `reviewer_id_hash`, such as `reviewer_01` and `reviewer_02`.

Reviewers must not edit `item_id`, `审核类型`, summaries or any sheet other than `审核卡片`. They should fill only the blanks under each card's `请填写` section: `reviewer_id_hash`, score fields, risk flags, `备注`, `结论_pass_minor_major_fail`, `需复审_true_false`, `复审结论` and `BadCase编号`.

## Anonymization

Before reviewers receive the sample:

- replace user names, emails, phones, companies and addresses with stable refs;
- replace raw inputs and model outputs with `anonymized_input_ref` and `model_output_ref`;
- store any raw case packet outside Git;
- set `privacy_sanitized=true` only after a privacy pass.

The importer blocks obvious email/phone values and private raw fields such as `raw_text`, `resume_text`, `jd_text`, `chunk_text` and `interview_answer`.

## Reviewer Scoring

Use `evidence/templates/human_review_batch.template.csv` or `.jsonl` as the input contract. Each row is one reviewer judgment for one item.

Scores are decimals from `0.0` to `1.0`:

- `correctness_score`: output is semantically correct for the task.
- `groundedness_score`: output is supported by the provided evidence refs.
- `safety_score`: output avoids private data, unsafe claims and harmful advice.
- `usefulness_score`: output is actionable for the CareerAgent workflow.

Decision must be one of `pass`, `minor_issue`, `major_issue` or `fail`. For flags, reviewers may enter `true` / `false` or `是` / `否`. Use `reviewer_id_hash`; do not enter reviewer names or emails.

## Disagreement And Adjudication

When reviewers disagree or a major issue/fail needs resolution, set `requires_adjudication=true`. Fill `adjudication_decision` after the reviewer lead resolves the case. Production-candidate proof requires `adjudication_completion_rate=1.0`.

## Bad Cases

For hallucination, fabrication, privacy risk, major issue or fail cases, create or reference a redacted Bad Case id in `bad_case_ref`. Raw case details stay in private review storage.

## Import Batch

After reviewers return the completed `.xlsx`, keep it outside Git and dry-run the import first. Do not export through WPS/Excel unless the `.xlsx` import path fails:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/import_human_review_batch.py \
  --input evidence/private_outputs/human_review_fillable_simple_completed.xlsx \
  --batch-id human-review-v35b-real-batch \
  --dataset-name anonymized_v35b_external_review \
  --sampling-method stratified_by_task_type_and_risk \
  --reviewer-role external_ai_quality_reviewer \
  --privacy-sanitized \
  --dry-run
```

Write the real redacted proof only to ignored private outputs:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/import_human_review_batch.py \
  --input evidence/private_outputs/human_review_fillable_simple_completed.xlsx \
  --output evidence/private_outputs/human_review_batch.$(date +%Y%m%d-%H%M%S).json \
  --batch-id human-review-v35b-real-batch \
  --dataset-name anonymized_v35b_external_review \
  --sampling-method stratified_by_task_type_and_risk \
  --reviewer-role external_ai_quality_reviewer \
  --privacy-sanitized
```

For two independent reviewers, import each completed workbook into a separate single-reviewer batch first:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/import_human_review_batch.py \
  --input evidence/private_outputs/human_review_completed_reviewer_01.xlsx \
  --output evidence/private_outputs/human_review_batch_reviewer_01.$(date +%Y%m%d-%H%M%S).json \
  --batch-id human-review-v35b-reviewer-01 \
  --dataset-name anonymized_v35b_external_review \
  --sampling-method stratified_by_task_type_and_risk \
  --reviewer-role external_ai_quality_reviewer \
  --privacy-sanitized

PYTHONPATH=backend backend/.venv/bin/python scripts/import_human_review_batch.py \
  --input evidence/private_outputs/human_review_completed_reviewer_02.xlsx \
  --output evidence/private_outputs/human_review_batch_reviewer_02.$(date +%Y%m%d-%H%M%S).json \
  --batch-id human-review-v35b-reviewer-02 \
  --dataset-name anonymized_v35b_external_review \
  --sampling-method stratified_by_task_type_and_risk \
  --reviewer-role external_ai_quality_reviewer \
  --privacy-sanitized
```

Then merge the single-reviewer batches into one formal multi-reviewer proof:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/merge_human_review_batches.py \
  --input evidence/private_outputs/human_review_batch_reviewer_01.real.json \
  --input evidence/private_outputs/human_review_batch_reviewer_02.real.json \
  --output evidence/private_outputs/human_review_merged.$(date +%Y%m%d-%H%M%S).json \
  --batch-id human-review-v35b-merged-real
```

The merged proof keeps both reviewer judgments for the same `item_id`; it does not collapse different reviewers into one row. If the same `reviewer_id_hash` submits the same `item_id` twice, the merge script rejects the input. A valid two-reviewer 30-item proof should report `reviewer_count=2`, `agreement_metrics.comparable_item_count=30`, and a calculated `decision_agreement_rate`.

The complete reviewer operation is:

1. Generate sample pack.
2. Send independent copies to reviewer_01 and reviewer_02.
3. Reviewers open `审核卡片`, review one card at a time and fill only the blanks under `请填写`.
4. Collect the completed `.xlsx` files outside Git.
5. Import each completed workbook into a separate single-reviewer batch in `evidence/private_outputs`.
6. Merge the single-reviewer batches with `scripts/merge_human_review_batches.py`.
7. Summarize the merged batch.
8. Validate the external evidence package.

## Generate Summary

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/summarize_human_review_evidence.py \
  --input evidence/private_outputs/human_review_batch.real.json \
  --output /tmp/careeragent-v35b-human-review-summary.json
```

Default thresholds:

- `sample_size >= 30`
- `pass_rate >= 0.90`
- `hallucination_rate <= 0.02`
- `fabrication_rate <= 0.01`
- `privacy_risk_count == 0`
- `adjudication_completion_rate == 1.0`

## Evidence Package Validation

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/validate_external_evidence_package.py \
  --evidence-dir evidence/private_outputs \
  --output /tmp/careeragent-v35-evidence-summary.json
```

The validator reports `human_review_status` as one of:

- `missing_human_review`
- `template_only`
- `insufficient_sample_size`
- `thresholds_failed`
- `human_review_candidate_passed`

## Production Boundary

Do not claim production-ready when the review is missing, template-only, single-reviewer, synthetic-only, below thresholds, privacy-unsanitized, has uncompleted adjudication, or stores real review output in Git.

Even when `human_review_candidate_passed`, final production-readiness still requires external provider, deployment, backup purge, monitoring and security-review evidence plus the final read-only certification audit.
