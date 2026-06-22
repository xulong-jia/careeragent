# CareerAgent 阶段五：Quality Review / Bad Case 设计

## 阶段状态

- 5A：Quality Review / Bad Case 设计文档与边界确认已完成。
- 5B：`bad_cases` DB model、Alembic migration 和 schema skeleton 已完成。
- 5C：Bad Case repository / service / API 和 tests 已完成。
- 5D：QualityReviewPage 最小 UI 已完成。
- 5E：Match / RAG / Agent 页面轻量 Mark as bad case 入口已完成。
- 5F：阶段五验收、安全检查和 README 收口已补充。

本设计文档保留阶段五边界：当前只做人工 review record，不接真实 LLM reviewer，不做自动评估，不做自动投递，不做正式 Evaluation Center。

## 1. 阶段五目标

阶段五目标是建立质量复查和 bad case 闭环，让 CareerAgent 不只能够生成 Match Report、RAG Answer 和 Agent Run，也能够记录这些结果的问题、风险和改进线索。

本阶段重点包括：

- 建立质量复查和 bad case 闭环。
- 对 Match Report、RAG Answer、Agent Run 等结果进行人工质量记录。
- 支持人工标注 bad case。
- 支持记录问题类型、严重程度、状态、改进建议。
- 支持后续通过 bad case 反向改进 Match / RAG / Agent Workflow。
- 当前阶段优先做人工 review record，不做自动评估。
- 当前阶段不接真实 LLM。
- 当前阶段不做自动投递。
- 当前阶段不做正式 Evaluation Center。

当前优先做 Quality Review 的原因：

- 项目已有 Resume / JD / Match / RAG / Agent Workflow 主链路。
- 当前缺少质量评估与错误复盘闭环。
- 先做质量闭环，再考虑真实 LLM 或投递管理更安全。

## 2. 非目标

阶段五初期明确不做：

- 不接真实 LLM。
- 不接 OpenAI / DeepSeek / Qwen。
- 不做自动评估。
- 不做自由聊天 Agent。
- 不做自动投递。
- 不做投递管理。
- 不做正式 Evaluation Center。
- 不做复杂 dashboard 图表。
- 不做批量 benchmark。
- 不做复杂统计报表。
- 不保存完整 resume raw_text。
- 不保存完整 JD raw_text。
- 不保存完整 RAG chunk text。
- 不保存投递记录或面试复盘原文。
- 不做未经约束的 prompt / tool execution。

## 3. 数据模型设计

阶段五设计三类对象，但分阶段实现。5B 只落地 `bad_cases`，`evaluation_runs` 和 `evaluation_items` 先作为后续扩展设计保留。

### bad_cases

说明：阶段五第一优先级，5B 先实现。

用途：

- 记录具体错误案例、质量问题、隐私风险或 UI 问题。

建议字段：

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string | 主键，沿用项目中的 string id 风格。 |
| user_id | string | 默认 `default`，暂不做登录 / 权限系统。 |
| source_type | string | 来源类型。 |
| source_id | string | 来源对象 ID。 |
| category | string | bad case 分类。 |
| severity | string | 严重程度。 |
| title | string | 短标题。 |
| description | text | 问题摘要，不保存隐私原文。 |
| expected_behavior | text nullable | 期望行为摘要。 |
| actual_behavior | text nullable | 实际行为摘要。 |
| suggested_fix | text nullable | 改进建议。 |
| status | string | 默认 `open`。 |
| created_at | datetime | 创建时间。 |
| resolved_at | datetime nullable | 关闭或修复时间。 |

设计说明：

- `source_type` 可指向 `match_report` / `rag_answer` / `agent_run` / `agent_step` / `resume_version` / `job_description` / `other`。
- `source_id` 只保存 ID，不复制源对象全文。
- `description` / `expected_behavior` / `actual_behavior` / `suggested_fix` 只保存问题摘要，不保存原文。
- `status` 用 string，不用复杂 enum。
- 5B 只实现 `bad_cases` 表。

### evaluation_runs

说明：先设计，暂不在 5B 实现。

用途：

- 一次评估批次或人工 review session。

建议字段：

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string | 主键。 |
| user_id | string | 默认 `default`。 |
| target_type | string | 被评估对象类型。 |
| target_id | string | 被评估对象 ID。 |
| status | string | run 状态。 |
| summary | text nullable | 本次评估摘要。 |
| metrics_json | JSON | 轻量指标记录。 |
| created_at | datetime | 创建时间。 |
| finished_at | datetime nullable | 完成时间。 |

### evaluation_items

说明：先设计，暂不在 5B 实现。

用途：

- evaluation run 下的单条检查项。

建议字段：

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string | 主键。 |
| evaluation_run_id | string | 所属 evaluation run。 |
| item_type | string | 检查项类型。 |
| target_type | string | 被检查对象类型。 |
| target_id | string | 被检查对象 ID。 |
| status | string | 检查项状态。 |
| score | integer nullable | 可选人工分数。 |
| labels_json | JSON | 标签集合。 |
| notes | text nullable | 人工备注摘要。 |
| created_at | datetime | 创建时间。 |

明确结论：

- 5B 只落地 `bad_cases`。
- `evaluation_runs` / `evaluation_items` 等 Bad Case 主路径稳定后再考虑。

## 4. Bad Case 分类设计

建议 category：

- `match_score_inaccurate`
- `missing_skill_extraction`
- `irrelevant_rag_source`
- `unsupported_answer`
- `hallucination_risk`
- `agent_step_failed`
- `need_more_info_wrong`
- `privacy_risk`
- `ui_confusing`
- `data_persistence_issue`
- `other`

Severity：

- `low`
- `medium`
- `high`
- `critical`

Status：

- `open`
- `reviewing`
- `fixed`
- `wont_fix`

设计说明：

- `critical` 主要用于隐私泄漏、错误自动行为、不可恢复数据问题。
- bad case 是 review record，不是最终质量评分。
- 不把主观评价伪装成客观评分。

## 5. 质量评估对象范围

阶段五最小支持：

- Match Report。
- RAG Answer。
- Agent Run。

后续可扩展：

- RAG Search Result。
- Agent Step。
- Resume Version。
- JD Profile。
- UI flow。
- Data persistence issue。

初期用 `source_type + source_id` 手动关联，不直接嵌入源对象全文。不在 Match / RAG / Agent 页面立即加一键入口，相关入口留到 5E。

## 6. API Contract 草案

5C 再实现 API。本节只定义草案。

### POST /api/evaluations/bad-cases

用途：

- 创建 bad case。

输入建议：

- `source_type`
- `source_id`
- `category`
- `severity`
- `title`
- `description`
- `expected_behavior`
- `actual_behavior`
- `suggested_fix`

输出：

- `BadCaseRecord`

### GET /api/evaluations/bad-cases

用途：

- 查询 bad case list。

Filters：

- `source_type`
- `source_id`
- `category`
- `severity`
- `status`
- `limit`

输出：

- `ListResponse[BadCaseRecord]`

### GET /api/evaluations/bad-cases/{bad_case_id}

用途：

- 查看 bad case detail。

输出：

- `BadCaseRecord`

### PATCH /api/evaluations/bad-cases/{bad_case_id}

用途：

- 更新 `status`、`severity`、`suggested_fix`、`notes` 等安全字段。

输出：

- `BadCaseRecord`

API 边界：

- 5C 再实现 API。
- 所有 response 不返回源对象原文。
- 不做 Evaluation Run API 初版实现。
- Evaluation Run API 只在设计中保留。

## 7. 前端页面草案

建议页面：

```text
QualityReviewPage
```

最小功能：

- 安全提示区：只记录问题摘要，不粘贴真实简历 / JD / RAG 原文 / API Key。
- 创建 bad case。
- bad case list。
- bad case detail。
- 按 `source_type` / `severity` / `status` 筛选。
- 修改 `status`。
- Dashboard 增加 Quality Review 入口。

阶段边界：

- 5D 再实现页面。
- 初期不做复杂图表。
- 初期不做 Evaluation Center。
- 初期不做批量 benchmark。
- 初期不做自动评估按钮。

## 8. 与现有模块集成策略

与现有模块的关联方式：

- Match Report：`source_type = match_report`，`source_id = match_report_id`。
- RAG Answer：`source_type = rag_answer` 或 `rag_document` / `rag_search`，`source_id` 记录对应 ID 或人工引用。
- Agent Run：`source_type = agent_run`，`source_id = agent_run_id`。
- Agent Step：后续可 `source_type = agent_step`。
- Resume Version：后续可 `source_type = resume_version`。
- JD Profile：后续可 `source_type = job_profile`。

初期策略：

- 5C / 5D 先支持手动输入 `source_type` / `source_id`。
- 5E 再在 Match / RAG / Agent 页面加 “Mark as bad case” 轻量入口。
- 不改动现有主流程。

## 9. 隐私与安全策略

阶段五必须保持数据最小化：

- bad case description 不应粘贴完整 resume raw_text。
- 不保存完整 JD raw_text。
- 不保存完整 RAG chunk text。
- 不保存 API Key。
- 不保存投递记录或面试复盘原文。
- `source_id` 只保存 ID。
- `description` / `notes` 只写问题摘要。
- 前端提示用户不要输入隐私原文。
- 后端 schema 不设置 `raw_text` / `chunk_text` 字段。
- tests 需要验证 `bad_cases` 表不包含 `raw_text` / `jd_raw_text` / `chunk_text`。
- 后续如引入 LLM 自动评估，必须先单独设计 prompt boundary、data minimization、source contract 和 redaction 策略。

## 10. 测试策略

阶段五测试建议：

DB infrastructure tests：

- `bad_cases` table exists。
- ORM create bad case。
- `category` / `severity` / `status` persisted。
- no `raw_text` / `jd_raw_text` / `chunk_text` columns。

API tests：

- create bad case。
- list bad cases。
- filter by `source_type` / `severity` / `status`。
- get detail。
- patch status。
- missing bad case returns 404。
- response 不包含源对象原文。

Frontend build：

- QualityReviewPage build 通过。

Safety tests：

- synthetic data only。
- no API key。
- no real resume / JD。

## 11. 阶段五子阶段拆分

推荐拆分：

- 5A：Quality Review / Bad Case 设计文档与边界确认。
- 5B：bad_cases DB model + Alembic migration + schema skeleton。
- 5C：Bad Case repository / service / API + tests。
- 5D：QualityReviewPage 最小 UI。
- 5E：Match / RAG / Agent 页面轻量 Mark as bad case 入口。
- 5F：阶段五验收文档、安全检查、README 更新。
- Release notes + tag：`v0.5.0-quality-review`。

说明：

- `evaluation_runs` / `evaluation_items` 先设计，不在 5B 实现。
- 如果后续需要，再作为 5G 或 v0.5.x 扩展。

## 12. 风险与规避

| 风险 | 规避策略 |
| --- | --- |
| bad case 中误保存隐私原文 | schema 不提供 raw_text 字段；前端给出安全提示；测试检查表字段和 response 不含原文。 |
| 过早做 LLM 自动评估导致不可控 | 阶段五初期只做人工 review record；LLM 自动评估必须先单独设计安全边界。 |
| evaluation schema 设计过重 | 5B 只实现 `bad_cases`；`evaluation_runs` / `evaluation_items` 暂缓。 |
| 前端页面过早复杂化 | 5D 只做 create / list / detail / filter / status update，不做图表和复杂 dashboard。 |
| 与 Match / RAG / Agent 边界混乱 | 通过 `source_type + source_id` 轻量引用，不嵌入源对象全文，不改现有主流程。 |
| 自动投递风险 | 阶段五不做投递管理、不做自动投递、不保存投递记录原文。 |
| 把主观评价当作客观评分 | bad case 是 review record，不是最终质量分；如有 score 必须标注为人工判断。 |
| `source_type` / `source_id` 随意填写导致追踪困难 | 先定义允许的 `source_type` 列表；API 层做基础校验；后续在页面提供选择器。 |

## 13. 阶段 5B 最小开发计划

5B 只应该做：

- 新增 BadCase ORM model。
- 新增 Alembic migration 创建 `bad_cases` 表。
- 新增 `BadCaseRecord` schema skeleton。
- 新增 DB infrastructure tests。
- 不实现 API。
- 不实现 service。
- 不实现 repository。
- 不改前端。
- 不接 LLM。
- 不做 Evaluation Run / Item 表。

建议文件：

- `backend/app/models/evaluation.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/evaluations.py`
- `backend/alembic/versions/20260621_0005_create_bad_cases.py`
- `backend/tests/test_bad_case_db_infrastructure.py`

命名建议：

- 推荐使用 `backend/app/models/evaluation.py`，因为阶段五后续可能扩展 `evaluation_runs` 和 `evaluation_items`。
- 5B 文件中只定义 `BadCase`，不提前实现 `EvaluationRun` / `EvaluationItem`。
