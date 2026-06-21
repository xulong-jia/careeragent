# CareerAgent v0.4.0-agent-workflow Release Notes

## 1. 版本定位

- CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。
- v0.4.0-agent-workflow 是阶段四 Agent Workflow 完成节点。
- 本版本在 v0.3.0-rag 的 DB-backed persistence + deterministic RAG knowledge base 基础上，新增 deterministic Agent Workflow workbench。
- 当前 Agent Workflow 是 deterministic state machine，不是真实 LLM Agent。
- 当前不接 OpenAI / DeepSeek / Qwen。
- 当前不做自动投递。

## 2. 已继承的 v0.2.0-persistence 能力

- SQLite + SQLAlchemy + Alembic 数据库基础设施。
- Resume 持久化。
- Resume Version 管理。
- JD 持久化。
- Job Profile 持久化。
- Match Report 持久化。
- 前端持久化 Resume / JD / Match 工作台。
- v0.2.0-persistence tag 已存在。

## 3. 已继承的 v0.3.0-rag 能力

- RAG documents / chunks 数据表。
- deterministic chunking / indexing。
- chunks list。
- lexical search。
- search sources / score / snippet / metadata。
- deterministic answer with citations。
- no-source behavior。
- KnowledgeBasePage 最小 UI。
- v0.3.0-rag tag 已存在。

## 4. 阶段四新增能力

- Agent Workflow 设计文档。
- agent_runs / agent_steps 数据表。
- AgentRun / AgentStep ORM models。
- Alembic migration 0004。
- Agent schema skeleton。
- Agent repository。
- Agent service。
- deterministic workflow runner。
- fixed workflow: job_application_preparation。
- step timeline DB persistence。
- need_more_info 缺槽追问。
- failed / completed / skipped 状态追踪。
- Agent Runs API。
- AgentRunsPage 最小 UI。
- safe JSON render helper。
- 阶段四验收文档。

## 5. Agent Workflow 设计

当前固定 workflow 为：

```text
job_application_preparation
```

步骤顺序：

1. validate_inputs
2. load_resume_version
3. load_job_profile
4. run_match_report
5. rag_search
6. build_final_summary

行为说明：

- `use_rag=false` 时 `rag_search` step 为 `skipped`。
- `use_rag=true` 且缺少 `rag_query` 时返回 `need_more_info`。
- missing resume / JD 时返回 `need_more_info`。
- failed step 会记录 `error_code` / `error_message`。
- successful run 会生成 deterministic `final_summary`。
- `final_summary` 不调用 LLM、不编造经历。

## 6. Agent Runs API 清单

- `POST /api/agents/runs`：同步执行 deterministic workflow run。
- `GET /api/agents/runs`：查询 run list，支持基础过滤。
- `GET /api/agents/runs/{run_id}`：查询 run detail。
- `GET /api/agents/runs/{run_id}/steps`：查询 run steps timeline。

API 行为：

- `completed` / `need_more_info` / `failed` 都是 run 业务状态。
- unsupported workflow 返回 `400 agent_workflow_not_supported`。
- missing run 返回 `404 agent_run_not_found`。
- API response 不返回 `raw_text` / JD `raw_text` / chunk text。

## 7. AgentRunsPage 能力

- 可创建 deterministic workflow run。
- 可查看 runs list。
- 可查看 run detail。
- 可查看 steps timeline。
- 支持 `completed` / `need_more_info` / `failed` / `skipped` / `pending` / `running` 状态。
- 支持 loading / empty / error state。
- Dashboard 和 sidebar 已有 Agent Runs 入口。
- safe JSON render helper 会隐藏敏感字段。
- 页面不展示完整 resume `raw_text`、JD `raw_text` 或 RAG chunk text。

## 8. 当前不包含的能力

- 真实 LLM Agent。
- OpenAI / DeepSeek / Qwen API。
- 自由聊天 Agent。
- true tool-calling Agent。
- 自动投递。
- 投递管理。
- Bad Case 页面。
- Evaluation Center。
- 复杂异步任务队列。
- run resume endpoint。
- 复杂 Agent memory。
- 多 workflow 编排。
- 自动申请职位。
- 未经约束的 prompt / tool execution。

## 9. 安全与隐私说明

- 不提交 `.env`。
- 不提交 `local_data/`。
- 不提交 SQLite 数据库文件。
- 不提交 `vector_index/`。
- 不提交真实简历、真实 JD、真实文档、投递记录、面试复盘。
- 不提交 API Key。
- 不提交 `CareerAgent_最终版项目开发执行手册.md`。
- Agent step payload 只保存 IDs / refs / short metadata。
- Agent API response 不返回 `raw_text` / JD `raw_text` / chunk text。
- AgentRunsPage safe JSON helper 过滤 `raw_text` / `jd_raw_text` / `chunk_text` / `full_text` / `snippet` / `api_key` / `secret` / `token`。
- Agent Workflow 不调用 LLM。
- Agent Workflow 不自动投递。
- 测试使用 synthetic data。

## 10. 验收状态

- 阶段一总验收通过。
- 阶段二总验收通过。
- 阶段三总验收通过。
- 阶段四总验收通过。
- 后端 pytest 通过：99 passed, 1 warning。
- 前端 build 通过。
- docker compose config 通过。
- Alembic upgrade 通过。
- DB health 通过。
- 安全扫描通过。
- StarletteDeprecationWarning 为现有依赖 warning，不影响验收。

## 11. 后续阶段

- 下一阶段不要直接开发，应先做方案确认。
- 后续如接真实 LLM Agent，必须先设计 prompt boundary、tool boundary、source contract 和隐私保护策略。
- 自动投递、投递管理、Bad Case、Evaluation Center 都应作为后续独立阶段设计，不应混入当前版本。
- v0.4.0-agent-workflow release notes 完成后，建议单独创建并 push tag：`v0.4.0-agent-workflow`。
