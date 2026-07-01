# CareerAgent Phase 2.3 Real Parser Foundation

阶段 2.3 把 JD Parser 和 Resume Parser 从 mock / rule-based baseline 升级为 parser production foundation。它不是 full production parser，也不声明 production-ready。

## What Changed

- JD Parser 输出 `role_category`、required/preferred skills、responsibilities、business scenarios、hidden requirements、interview focus、risk level、summary、`parse_confidence`、`evidence`、`warnings` 和 `parser_metadata`。
- Resume Parser 输出 basic info、education、projects、experience、skills categories、certificates、awards、parser risk flags、`parse_confidence`、`evidence`、`warnings` 和 `parser_metadata`。
- Parser 输出通过 Pydantic schema validation 后进入 API / DB JSON。
- 默认路径仍是 local deterministic parser foundation，测试不依赖 API key、外部网络或真实 LLM。
- Optional LLM path 复用 `backend/app/ai/llm_provider.py`，显式开启真实 provider 后才会调用 OpenAI-compatible endpoint；失败或缺配置会在 metadata/warnings 中记录 fallback。
- `job_profiles` 新增 parser metadata columns；`structured_resume` 继续使用 JSON 兼容扩展。

## JD Parser

JD Parser 当前支持：

- `job_title`、`company`、`location`
- `role_category`
- `required_skills` / `preferred_skills`
- `responsibilities`
- `business_scenarios`
- `hidden_requirements`
- `interview_focus`
- `risk_level`
- `summary`
- `parse_confidence`
- `evidence`
- `warnings`
- `parser_metadata`

Role category 覆盖 2.3 要求的 LLM Application Engineer、Python Backend Developer、AI Application Engineer、Frontend / Fullstack Developer、Data Analyst / Data Engineer、Data Platform Engineer、Computer Vision Engineer、Bank IT Graduate Program、Enterprise Digitalization Role 和 Other。

`jd_service_004` 已从旧的 Python Backend Developer 误判修正为 Data Platform Engineer。required/preferred 区分优先使用 must/required/need/responsibilities 和 preferred/nice to have/bonus/plus 等 cue，避免把加分项全部当必备项。

## Resume Parser

Resume Parser 当前支持：

- `basic_info`
- `education`
- `projects`
- `experience`
- skill categories: programming、backend、frontend、ai、database、tools
- `certificates`
- `awards`
- `risk_flags`
- `parse_confidence`
- `evidence`
- `warnings`
- `parser_metadata`

技能抽取优先使用 Skills section。没有明确 Skills section 时才从全文 fallback，并写入 `skills_inferred_without_skill_section` warning，降低过度抽取风险。Parser 会生成 foundation-level risk flags：`unsupported_metric`、`fabricated_skill`、`timeline_conflict`、`overclaim`、`missing_evidence`、`parse_low_confidence`、`ambiguous_section`。

上传简历后，parser risk flags 会写入 initial resume version；人工确认版本仍通过现有 risk-check 生成风险报告后保存。

## Provider Boundary

默认测试路径：

```text
LLM_PROVIDER=deterministic
ENABLE_REAL_LLM=false
```

Optional LLM path：

```text
ENABLE_REAL_LLM=true
LLM_PROVIDER=openai_compatible
LLM_API_BASE_URL=https://provider.example/v1
LLM_API_KEY=<runtime secret only>
LLM_MODEL=<model>
```

LLM provider 有 timeout、one retry、JSON schema validation 和 controlled fallback。测试使用 fake provider / deterministic fallback，不访问外部网络，不提交真实 key。

## Evaluation

`service_level` parser cases 已扩展：

| Module | Cases | Key Metrics |
| --- | ---: | --- |
| JD Parser | 12 | `role_category_match`, `required_skill_hit_rate`, `preferred_skill_hit_rate`, `responsibility_hit_rate`, `hidden_requirement_hit_rate`, `evidence_coverage`, `confidence_present`, `warning_expected_match`, `case_pass` |
| Resume Parser | 8 | `section_hit_rate`, `skill_hit_rate`, `project_hit_rate`, `education_hit_rate`, `risk_flag_hit_rate`, `evidence_coverage`, `confidence_present`, `case_pass` |

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module jd_parser --output-dir /tmp/careeragent-evals-jd-parser
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module resume_parser --output-dir /tmp/careeragent-evals-resume-parser
```

## Remaining Gaps

- Not OCR: scanned PDF / image resume parsing is still unsupported.
- Not large benchmark: current cases are de-identified foundation fixtures, not broad production quality measurement.
- Not default production LLM parser: real provider path is opt-in and must be calibrated separately.
- Complex bilingual PDFs, tables, unusual layouts, and noisy resumes still need larger evaluation.
- `raw_text` remains plaintext and is still a production privacy/security blocker.
- Match scoring and Project Rewrite have 2.4 trustworthy foundation, and Agent Workflow has 2.5 production foundation, but all still require larger validation and production hardening.

Next phase: Final Production Readiness Audit.
