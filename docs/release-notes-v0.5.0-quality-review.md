# CareerAgent v0.5.0-quality-review Release Notes

## 1. 版本定位

- CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。
- `v0.5.0-quality-review` 是阶段五 Quality Review / Bad Case 完成节点。
- 本版本在 `v0.4.0-agent-workflow` 的 DB-backed persistence + RAG + deterministic Agent Workflow 基础上，新增人工质量复查和 bad case 闭环。
- 当前 Quality Review 是人工 review record，不是真实 LLM reviewer。
- 当前不接 OpenAI / DeepSeek / Qwen。
- 当前不做自动评估。
- 当前不做自动投递。

## 2. 已继承的 v0.2.0-persistence 能力

- SQLite + SQLAlchemy + Alembic 数据库基础设施
- Resume 持久化
- Resume Version 管理
- JD 持久化
- Job Profile 持久化
- Match Report 持久化
- 前端持久化 Resume / JD / Match 工作台
- `v0.2.0-persistence` tag 已存在

## 3. 已继承的 v0.3.0-rag 能力

- RAG documents / chunks 数据表
- deterministic chunking / indexing
- chunks list
- lexical search
- search sources / score / snippet / metadata
- deterministic answer with citations
- no-source behavior
- KnowledgeBasePage 最小 UI
- `v0.3.0-rag` tag 已存在

## 4. 已继承的 v0.4.0-agent-workflow 能力

- `agent_runs` / `agent_steps` 数据表
- deterministic workflow runner
- fixed workflow: `job_application_preparation`
- `need_more_info` 缺槽追问
- failed / completed / skipped 状态追踪
- Agent Runs API
- AgentRunsPage 最小 UI
- safe JSON render helper
- `v0.4.0-agent-workflow` tag 已存在

## 5. 阶段五新增能力

- Quality Review / Bad Case 设计文档
- `bad_cases` 数据表
- BadCase ORM model
- Alembic migration 0005
- BadCase schema skeleton
- Bad Case repository
- Bad Case service
- Bad Case API
- allowed values validation
- extra sensitive fields rejected
- QualityReviewPage 最小 UI
- Dashboard / navigation Quality Review 入口
- MarkBadCasePanel 可复用组件
- Match 页面 Mark as bad case 入口
- KnowledgeBasePage Mark as bad case 入口
- AgentRunsPage Mark as bad case 入口
- 阶段五验收文档

## 6. Bad Case API 清单

- `POST /api/evaluations/bad-cases`：创建 bad case。
- `GET /api/evaluations/bad-cases`：查询 bad case 列表。
- `GET /api/evaluations/bad-cases/{bad_case_id}`：查询单个 bad case 详情。
- `PATCH /api/evaluations/bad-cases/{bad_case_id}`：更新 bad case 状态和摘要字段。

说明：

- 支持 create / list / filter / detail / patch。
- list 支持 source_type / source_id / category / severity / status filters。
- `status=fixed` / `status=wont_fix` 自动设置 `resolved_at`。
- `status=open` / `status=reviewing` 会清空 `resolved_at`。
- invalid source_type / category / severity / status 返回 400 `bad_case_invalid_field`。
- missing bad case 返回 404 `bad_case_not_found`。
- request schema 使用 `extra="forbid"` 拒绝额外敏感字段。
- API response 不返回源对象全文。

## 7. QualityReviewPage 能力

- 可创建 bad case。
- 可查看 bad case list。
- 可使用 filters。
- 可查看 bad case detail。
- 可 patch status / severity / suggested_fix / title / description / category。
- Dashboard 和 sidebar 已有 Quality Review 入口。
- 页面提示用户只记录问题摘要，不粘贴完整原文。
- 页面不展示 raw_text / JD raw_text / RAG chunk text / API Key。

## 8. Mark as bad case 入口能力

- MarkBadCasePanel 是可复用组件。
- Match 页面可从 Match Report 创建 bad case。
- KnowledgeBasePage 可从 selected document / answer result 创建 bad case。
- AgentRunsPage 可从 Agent Run 创建 bad case。
- MarkBadCasePanel 自动填 source_type / source_id。
- description 默认空。
- expected_behavior / actual_behavior / suggested_fix 由用户手写摘要。
- 不自动复制 Resume / JD / RAG chunk / Agent refs 原文。
- 创建成功后提示可在 Quality Review 页面查看。

## 9. 当前不包含的能力

- 自动评估
- 真实 LLM reviewer
- OpenAI / DeepSeek / Qwen API
- evaluation_runs / evaluation_items
- 复杂 Evaluation Center
- 批量 benchmark
- 复杂评分 dashboard
- 自动投递
- 投递管理
- 自动申请职位
- 未经约束的 prompt / tool execution

## 10. 安全与隐私说明

- 不提交 `.env`
- 不提交 `local_data/`
- 不提交 SQLite 数据库文件
- 不提交 `vector_index/`
- 不提交真实简历、真实 JD、真实文档、投递记录、面试复盘
- 不提交 API Key
- 不提交 `CareerAgent_最终版项目开发执行手册.md`
- `bad_cases` 表不包含 raw_text / jd_raw_text / chunk_text / full_text / resume_text / job_text
- Bad Case API response 不返回源对象全文
- QualityReviewPage 不提示用户粘贴原文
- MarkBadCasePanel 不自动复制原文
- 当前不接 LLM
- 当前不做自动评估
- 当前不做自动投递
- 测试使用 synthetic data

## 11. 验收状态

- 阶段一总验收通过
- 阶段二总验收通过
- 阶段三总验收通过
- 阶段四总验收通过
- 阶段五总验收通过
- 后端 pytest 通过：114 passed, 1 warning
- 前端 build 通过
- docker compose config 通过
- Alembic upgrade 通过
- DB health 通过
- 安全扫描通过
- Node 20.17.0 低于 Vite 建议 20.19+ 是当前本地环境 warning，但 build 成功，不影响验收
- StarletteDeprecationWarning 为现有依赖 warning，不影响验收

## 12. 后续阶段

- 下一阶段不要直接开发，应先做方案确认。
- 若后续进入投递管理 / application management，需要先做数据模型、隐私边界和手动确认流程设计。
- 若后续接真实 LLM reviewer，必须先设计 prompt boundary、source contract、data minimization 和 redaction 策略。
- 自动投递、投递管理、自动评估、Evaluation Center 都应作为后续独立阶段设计，不应混入当前版本。
- `v0.5.0-quality-review` release notes 完成后，建议单独创建并 push tag：`v0.5.0-quality-review`。
