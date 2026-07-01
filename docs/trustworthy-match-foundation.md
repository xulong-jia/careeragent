# CareerAgent Phase 2.4 Trustworthy Match Foundation

阶段 2.4 把 Match Scoring 和 Project Rewrite 从简单 overlap / rewrite demo 升级为 trustworthy foundation。它仍不是 production-ready，也不代表核心求职判断能力已完成。

## Match Scoring

`POST /api/matches/run` 现在输出六维评分：

- `skill_match`
- `project_relevance`
- `business_understanding`
- `expression_quality`
- `education_fit`
- `risk_control`

每个维度都写入 `evidence`，包含 `dimension`、`jd_requirement`、`resume_signal`、`score_impact`、`source` 和 `confidence`。总分来自维度权重和风险扣分：

- skill_match: 0.25
- project_relevance: 0.30
- business_understanding: 0.15
- expression_quality: 0.10
- education_fit: 0.10
- risk_control: 0.10

`score_breakdown` 记录权重、weighted score、risk penalty、matched / missing required skills、project-supported required skills 和 `foundation_only=true`。`scoring_method=deterministic_trustworthy_match_v1` 明确该路径仍是 deterministic foundation。

## Risk Deduction

Match risk flags 支持：

- `unsupported_metric`
- `fabricated_skill`
- `overclaim`
- `weak_evidence`
- `missing_evidence`
- `project_jd_mismatch`
- `timeline_conflict`

风险会影响 `risk_control` 和 `total_score`，并进入 `gaps`、`rewrite_priorities` 和 `score_breakdown.risk_deductions`。

## Match Compare

新增 `POST /api/matches/compare`：

- 同一 JD 比较多个 resume versions：传 `jd_id` + `resume_version_ids`。
- 同一 resume version 比较多个 JDs：传 `resume_version_id` + `jd_ids`。

返回 `compare_mode`、按 `total_score` 降序排序的 items、rank、score delta、main strengths/gaps、risk flags 和 dimension scores。当前 compare 会为每个组合真实调用并持久化 match report。

## Project Rewrite

`POST /api/projects/{project_id}/rewrite` 现在要求每条 rewritten bullet 都带：

- `before`
- `after`
- `reason`
- `evidence_required`
- `forbidden_changes`
- `matched_jd_requirements`
- `missing_points`
- `risk_level`
- `confidence`

整体 rewrite response 继续包含 `matched_points`、`missing_points`、`evidence_required`、`forbidden_changes`、`risk_flags`、`rewrite_strategy`，并新增 `rewrite_method` 和 `confidence`。`rewrite_strategy` 与 `rewrite_method` 均为 `deterministic_trustworthy_project_rewrite_v1`。

Project Rewrite 只使用用户保存的 project facts、JD profile、可选 resume/match/profile refs，不新增未证实的公司、用户量、收益、准确率、上线状态、业务规模、技术栈、团队规模或部署状态。如果没有原始 bullet，但存在 tech stack/evidence 等项目事实，会生成 `before=""` 的保守草稿，并强制写入 evidence_required 和至少 medium risk。

## Evaluation

`service_level` dataset 已扩展：

- Match: 9 cases，覆盖强/弱匹配、缺项目证据、业务理解缺失、教育 fit、unsupported metric、同一 JD 多简历比较。
- Project Rewrite: 6 cases，覆盖强匹配、缺 required skill、unsupported metric、learning-to-business overclaim、空原 bullet 和防编造技术。

Match metrics:

- `dimension_score_present_rate`
- `evidence_dimension_coverage`
- `strength_keyword_hit_rate`
- `gap_keyword_hit_rate`
- `score_in_expected_range`
- `risk_flag_hit_rate`
- `rewrite_priority_hit_rate`
- `scoring_method_present`
- `confidence_present`
- `case_pass`

Project Rewrite metrics:

- `before_after_present`
- `evidence_required_present`
- `forbidden_changes_present`
- `risk_level_present`
- `matched_requirement_hit_rate`
- `missing_point_hit_rate`
- `risk_flag_hit_rate`
- `bullet_keyword_hit_rate`
- `fabrication_guard_pass`
- `case_pass`

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module match --output-dir /tmp/careeragent-evals-match
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module project_rewrite --output-dir /tmp/careeragent-evals-project-rewrite
```

## Remaining Gaps

- Scoring is still deterministic and must not be treated as human-equivalent judgment.
- No large real human agreement benchmark yet.
- No calibrated LLM reviewer, no ranking stability benchmark across broad real samples.
- Project Rewrite suggestions still require human confirmation before use.
- Phase 2.5 Agent Workflow now orchestrates Match/Rewrite through resumable fixed workflows, but this does not change Match/Rewrite production-readiness status.
- v3.0 adds redacted errors/logging, readiness, audit foundation, privacy deletion proof, token revoke, RBAC gate and sensitive field encryption, but Match/Rewrite remain deterministic trustworthy foundation and still require human confirmation.
