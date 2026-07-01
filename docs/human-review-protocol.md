# CareerAgent Human Review and LLM Judge Protocol

This protocol is a production-quality evaluation foundation. It is not evidence that external review has already been completed.

## Human Review Schema

Required fields:

- `reviewer_id`
- `review_role`
- `review_timestamp`
- `rubric_version`
- `module`
- `case_id`
- `human_score`
- `human_label`
- `confidence`
- `disagreement_reason`
- `accepted_output`
- `rejected_output`
- `correction_note`
- `privacy_review_passed`

The utilities in `backend/app/evaluation/ai_quality.py` parse records and compute two-reviewer agreement, disagreement cases and average confidence.

## Rubric

| Module | Review focus |
| --- | --- |
| JD parser | Required/preferred skills, role category, responsibilities, hidden requirements and evidence |
| Resume parser | Section extraction, skill categories, project facts, risk flags and evidence |
| RAG answer | Groundedness, citation coverage, no-evidence refusal and unsupported claim risk |
| Match scoring | Ranking consistency, evidence completeness, gap identification and score range |
| Project rewrite | Factuality, no fabricated metrics, forbidden changes and evidence requirement clarity |
| Agent workflow | Correct status, missing slots, resume/retry/cancel behavior and privacy-safe payload |

Two-reviewer agreement below 0.8 must block production-quality candidate claims until adjudicated.

## LLM Judge Protocol

LLM judge records are optional and advisory. Required metrics:

- `groundedness_score`
- `factuality_score`
- `completeness_score`
- `hallucination_flag`
- `evidence_alignment_score`

Judge output must reference evidence/source refs. A judge result without evidence should be downgraded or refused. It must never replace human review.

## Fixtures

Sample fixtures live in:

- `evals/datasets/anonymized_benchmark/human_review_sample.jsonl`
- `evals/datasets/anonymized_benchmark/llm_judge_sample.jsonl`

They are safe samples for protocol validation, not proof of completed external review.
