# CareerAgent 阶段四：Agent Workflow 设计

## 1. 阶段四目标

阶段四目标是建立可审计、可追踪、可恢复的 Agent Workflow 基础设施。阶段四初期不是自由 Agent，也不是自动投递系统，而是通过 deterministic state machine 串联已有 Resume / JD / Match / RAG 能力。

阶段四应支持：

- 建立可审计、可追踪、可恢复的 Agent Workflow 基础设施。
- 通过 deterministic state machine 串联 Resume / JD / Match / RAG。
- 记录 `agent_runs` 和 `agent_steps`。
- 支持 step timeline。
- 支持 `need_more_info` 缺槽追问。
- 支持 workflow status / step status / error tracking。
- 初期不接真实 LLM Agent。
- 初期不做自由聊天智能体。
- 初期不做自动投递。

## 2. 非目标

阶段四初期不做：

- 不接真实 LLM Agent。
- 不接 OpenAI / DeepSeek / Qwen。
- 不做自由聊天机器人。
- 不做自动投递。
- 不做投递管理。
- 不做 Bad Case 页面。
- 不做正式 Evaluation Center。
- 不做复杂工具调用编排。
- 不把完整 resume raw_text / JD raw_text / RAG chunk text 写入 agent step payload。
- 不做未经约束的 prompt/tool execution。

## 3. Agent 数据模型设计

阶段 4A 只做设计，不新增表。阶段 4B 才新增 ORM models 和 Alembic migration。

### agent_runs

用途：记录一次 workflow run 的主状态、输入引用、输出引用、缺槽信息和错误信息。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| user_id | string | 阶段四仍可使用 `default` |
| workflow_name | string | 例如 `job_application_preparation` |
| status | string | pending / running / completed / failed / need_more_info |
| input_refs | json | 输入 ID / refs / short metadata |
| output_refs | json | 输出 ID / refs / short metadata |
| missing_slots | json nullable | 缺槽列表 |
| questions | json nullable | 面向用户的追问列表 |
| error_code | string nullable | run 级错误码 |
| error_message | string nullable | run 级错误信息，不包含隐私原文 |
| created_at | datetime | 创建时间 |
| started_at | datetime nullable | 开始时间 |
| finished_at | datetime nullable | 结束时间 |
| duration_ms | integer nullable | 总耗时 |

说明：

- status 可选值：`pending` / `running` / `completed` / `failed` / `need_more_info`。
- `input_refs` / `output_refs` 只保存 ID / refs / short metadata。
- 不保存完整 resume raw_text、JD raw_text、RAG chunk text 或其他隐私文本。

### agent_steps

用途：记录一个 `agent_run` 中每个 deterministic step 的执行状态、输入输出引用、错误和耗时，用于 timeline、审计和失败排查。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| run_id | string / uuid | 外键，指向 `agent_runs.id` |
| step_name | string | 例如 `validate_inputs` |
| step_order | integer | 同一 run 内递增 |
| status | string | pending / running / completed / failed / skipped / need_more_info |
| input_refs | json | step 输入 refs |
| output_refs | json | step 输出 refs |
| error_code | string nullable | step 错误码 |
| error_message | string nullable | step 错误信息，不包含隐私原文 |
| created_at | datetime | 创建时间 |
| started_at | datetime nullable | 开始时间 |
| finished_at | datetime nullable | 结束时间 |
| duration_ms | integer nullable | step 耗时 |

说明：

- step status 可选值：`pending` / `running` / `completed` / `failed` / `skipped` / `need_more_info`。
- `run_id` 外键指向 `agent_runs.id`。
- 建议索引：`run_id`、`status`。
- 建议 unique：`run_id + step_order`。
- 不保存完整隐私文本。

Alembic migration 策略：

- 阶段 4B 才新增 migration。
- 阶段 4A 不新增 migration。

## 4. 最小 Workflow 设计

阶段四最小 workflow：

```text
job_application_preparation
```

输入：

- `resume_id` 或 `resume_version_id`
- `jd_id`
- `use_rag` optional
- `rag_query` optional

步骤：

1. `validate_inputs`
2. `load_resume_version`
3. `load_job_profile`
4. `run_match_report`
5. `optional rag_search`
6. `build_final_summary`

说明：

- 初期 deterministic。
- 不接 LLM。
- 不生成虚假经历。
- `final_summary` 只基于 refs / existing reports / search sources。
- `run_match_report` 应调用已有 Match service，不重写匹配逻辑。
- `optional rag_search` 应调用已有 RAG service，不重写检索逻辑。

## 5. Step Contract

最小 step record：

- `step_name`
- `step_order`
- `status`
- `input_refs`
- `output_refs`
- `error`
- `duration_ms`
- `created_at`
- `started_at`
- `finished_at`

规则：

- `input_refs` / `output_refs` 必须只保存 refs，不保存完整 raw text。
- `error` 只保存 code / message，不保存隐私原文。
- 每个 step 应可查看、可复查、可用于排查失败。
- Step output 应保留可追踪引用，例如 `resume_version_id`、`jd_id`、`match_report_id`、RAG `doc_id` / `chunk_id`。

## 6. 缺槽追问 need_more_info 设计

触发场景：

- 缺少 `resume_id` / `resume_version_id`。
- 缺少 `jd_id`。
- 指定 resume 不存在。
- 指定 resume_version 不存在。
- 指定 JD 不存在。
- resume 没有 active/latest version。
- `use_rag=true` 但缺少 `rag_query`，可选。

`missing_slots` 格式：

```json
[
  {"name": "jd_id", "reason": "A job description is required."}
]
```

`questions` 格式：

```json
[
  {"slot": "jd_id", "question": "请选择一个 JD 后再运行 workflow。"}
]
```

说明：

- 阶段四初期可以只检测缺少 Resume / JD / Resume Version。
- `POST /api/agents/runs/{run_id}/resume` 留到后续。
- 初期不做复杂交互恢复。

## 7. API Contract 草案

所有接口继续使用统一 response wrapper：

```json
{
  "data": {},
  "request_id": "..."
}
```

错误响应继续使用统一结构：

```json
{
  "error": {
    "code": "need_more_info",
    "message": "More information is required.",
    "details": {}
  },
  "request_id": "..."
}
```

### POST /api/agents/runs

输入：

- `workflow_name`
- `resume_id` optional
- `resume_version_id` optional
- `jd_id` optional
- `use_rag` optional
- `rag_query` optional

输出：

- `AgentRunRecord`
- steps summary

### GET /api/agents/runs

输出：

- run list

### GET /api/agents/runs/{run_id}

输出：

- run detail

### GET /api/agents/runs/{run_id}/steps

输出：

- step timeline

### POST /api/agents/runs/{run_id}/resume

说明：

- 留到后续。
- 不在 4B / 4C 初期实现。

错误码建议：

- `agent_workflow_not_supported`
- `agent_run_not_found`
- `agent_step_failed`
- `need_more_info`
- `resume_not_found`
- `resume_version_not_found`
- `job_not_found`

说明：

- 所有接口使用统一 response wrapper。
- 阶段四初期建议同步执行 deterministic workflow，便于测试和调试。

## 8. Repository / Service / Agent 层边界

阶段四后续建议新增文件，但阶段 4A 不实现：

- `backend/app/models/agent.py`
- `backend/app/schemas/agents.py`
- `backend/app/repositories/agent_repository.py`
- `backend/app/services/agent_service.py`
- `backend/app/agents/state.py`
- `backend/app/agents/steps.py`
- `backend/app/agents/workflows.py`
- `backend/app/agents/runner.py`
- `backend/app/api/agents.py`

职责说明：

- API route：HTTP request / response / dependency injection。
- service：workflow 校验、runner orchestration、API result mapping。
- repository：`agent_runs` / `agent_steps` DB persistence/query。
- runner：按 workflow definition 执行 steps，更新 run / step 状态。
- steps：deterministic step implementation。
- workflows：定义 workflow metadata、required slots、step order。
- route 不写复杂业务逻辑。

## 9. 与现有模块集成策略

Agent Workflow 调用已有模块，不重写已有业务逻辑：

- Resume Version repository / service：读取 latest active version 或指定 version。
- Job repository / service：读取 JD 和 job_profile。
- Match service：生成并持久化 match report。
- RAG service：执行 search / answer。
- Agent 不重写 Match / RAG 逻辑，只做 orchestration。
- Step output 保存 `match_report_id`、`resume_version_id`、`jd_id`、RAG source refs 等，不复制隐私全文。

集成边界：

- Agent step 可引用上游输出 ID，但不复制完整 raw text。
- Agent final summary 可以保存 deterministic short summary 和 refs。
- RAG answer 若被使用，仍必须保留 sources / chunk refs。

## 10. Deterministic Runner 策略

- 初期不接真实 LLM。
- runner 使用固定 workflow definition。
- 每个 step 执行前写 `running`。
- 成功后写 `completed`。
- 失败后写 `failed`，并记录 `error_code` / `error_message`。
- 缺槽时 run status = `need_more_info`。
- step `duration_ms` 需要记录。
- final output deterministic，不做无来源生成。

建议执行原则：

- 每个 step 开始和结束都更新 DB。
- step 失败后后续 step 标记 `skipped` 或保持 `pending`，具体策略在 4C 确认。
- runner 只调 service/repository，不直接读写隐私原文到 step payload。

## 11. 测试策略

阶段四测试应覆盖：

- create agent run success。
- missing resume / JD returns `need_more_info`。
- successful workflow creates `agent_steps`。
- failed step records error。
- run final status correct。
- steps ordered correctly。
- `input_refs` / `output_refs` persisted。
- no raw_text / JD raw_text / chunk text copied into step payload。
- existing backend tests still pass。
- frontend build still pass。
- docker compose config pass。
- alembic upgrade pass。
- DB health pass。

## 12. 安全与隐私策略

- `input_refs` / `output_refs` 只保存 ID。
- 不保存完整 resume raw_text。
- 不保存完整 JD raw_text。
- 不保存完整 RAG chunk text。
- error 不输出隐私原文。
- logs 不输出隐私原文。
- 不提交真实数据。
- 不接真实 LLM Agent。
- 后续如接 LLM，必须先设计 prompt boundary、tool boundary 和 source contract。
- 禁止自动投递。

## 13. 阶段四子阶段拆分

- 4A：Agent Workflow 设计文档与边界确认。
- 4B：`agent_runs` / `agent_steps` models + Alembic migration。
- 4C：deterministic workflow runner + step execution。
- 4D：Agent Runs API + tests。
- 4E：AgentRunsPage 最小 UI。
- 4F：阶段四验收文档、安全检查、README 更新。

## 14. 风险与规避

- 过早接真实 LLM Agent 导致不可控：先做 deterministic state machine，真实 LLM 留到后续专门阶段。
- Agent 自由生成导致编造：final output 必须基于 refs / existing reports / search sources。
- step payload 泄露隐私：只保存 IDs、refs、short metadata，不保存完整 raw text。
- workflow 失败后状态混乱：runner 明确 run/step 状态流转，并记录 error / duration。
- 上游模块结果错误传播：step output 保留 upstream refs，便于复查来源。
- Agent 和 RAG / Match 逻辑边界混乱：Agent 只 orchestrate，不重写 Match / RAG。
- 前端过早复杂化：先完成 models、runner、API，再做最小 AgentRunsPage。
- 自动投递越界：阶段四明确不做自动投递，不做投递管理。

## 15. 阶段 4B 最小开发计划

阶段 4B 只应该做：

- 新增 `agent_runs` / `agent_steps` ORM models。
- 新增 Alembic migration。
- 新增 schemas skeleton。
- 新增 DB smoke tests。
- 不实现 runner。
- 不实现 API。
- 不做前端。
- 不接 LLM。
