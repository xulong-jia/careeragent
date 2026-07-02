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
  --output evidence/private_outputs/human_review_fillable_simple_$(date +%Y%m%d-%H%M%S).xlsx
```

Use `--format csv` when a machine-only CSV is needed. The reviewer-facing `.xlsx` is the simplified workbook and contains:

- `审核卡片`: the only sheet reviewers should edit.
- `填写说明`: reviewer instructions.

The `审核卡片` sheet is a vertical questionnaire: each review item is a card with `item_id`, `审核类型`, `【匿名输入】`, `【模型输出】`, `【审核说明】` and a `请填写` section. It intentionally avoids formulas, data validation, named ranges, table objects, hidden sheets, cross-sheet references and dropdown validation for better Excel/WPS compatibility.

The committed template at `evidence/templates/human_review_sample_pack.template.csv` is only a placeholder. It is not real review evidence.

## Reviewer Instructions

Reviewers should open `审核卡片` and read each card's `审核类型`, `【匿名输入】`, `【模型输出】` and `【审核说明】`.

Reviewers must not edit `item_id` or any sheet other than `审核卡片`.

## What Reviewers Should Use

Reviewers judge each card only from the simplified workbook:

- `【匿名输入】`: the safe anonymized review context, such as job title/responsibilities/skills, candidate sections/projects, JD/resume match context, RAG question plus citation summary, project rewrite constraints or Agent workflow state.
- `【模型输出】`: the model/system output to audit, such as parsed fields, extracted resume sections, match score and evidence, grounded answer status, rewrite factuality signals or workflow next action.
- `【审核说明】`: the task-specific rubric for deciding correctness, groundedness, safety, usefulness, flags and final decision.

Reviewers do not need source code, API keys, databases, provider traces, real resumes, real JDs or real user data. If a card does not contain enough anonymized context to judge quality, reviewers should mark it for review instead of guessing.

Reviewers fill only the right-side blanks under `请填写` in each `审核卡片` card:

- `reviewer_id_hash`
- `正确性_0到1`
- `有依据_0到1`
- `安全性_0到1`
- `有用性_0到1`
- `隐私风险_true_false`
- `幻觉_true_false`
- `编造_true_false`
- `结论_pass_minor_major_fail`
- `需复审_true_false`
- `备注`
- `复审结论`
- `BadCase编号`

Score guide:

- `1.0` = good
- `0.8` = minor issue
- `0.5` = major issue
- `0.0` = fail

Scores may use decimals from `0.0` to `1.0`. `结论` and `复审结论` must be one of `pass`, `minor_issue`, `major_issue` or `fail`. Flag fields must be explicitly set to `true` or `false`; `TRUE/FALSE` and `是/否` are also accepted. Blanks are rejected during import.

## Privacy Boundary

The reviewer packet must expose only anonymized refs and summaries. Reviewers must not receive API keys, provider traces, real resumes, real JDs, interview answers, emails, phone numbers, names, private company identifiers or raw RAG chunks through this workbook.

After reviewers complete the `.xlsx`, store the returned file outside Git. `scripts/import_human_review_batch.py` can import the simplified `.xlsx` directly; it reads reviewer-entered values from `审核卡片` and reconstructs machine refs from `item_id`.
