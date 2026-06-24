# CareerAgent 当前架构说明

本文档描述当前仓库真实实现状态。历史阶段文档保留当时阶段边界；如果历史文档写“暂不做某模块”，以本文档和 README 的当前状态为准。

## 1. 当前定位

CareerAgent 是面向校招和留学生回国求职场景的 AI 求职工作台原型。它不是自动投递工具，不接招聘网站，不做真实 LLM Agent，也不把 evaluation 结果当作模型能力最终评分。

当前系统是本地 SQLite-backed deterministic prototype：

- 后端：FastAPI + Pydantic + SQLAlchemy + Alembic + SQLite。
- 前端：React + TypeScript + Vite。
- 数据：默认本地 SQLite，`local_data/` 不进入 Git。
- AI 边界：当前 Resume/JD/Match/RAG/Agent/Evaluation 均为 deterministic 规则或状态机，不调用真实 LLM。

## 2. 目录结构

```text
backend/app/api/            FastAPI routes
backend/app/schemas/        Pydantic request/response schemas
backend/app/services/       业务逻辑和 deterministic runner
backend/app/repositories/   SQLAlchemy persistence access
backend/app/models/         ORM models
backend/app/rag/            chunking / lexical retrieval / deterministic answering
backend/app/agents/         deterministic workflow runner and steps
backend/alembic/versions/   database migrations
frontend/src/api/           React API client wrappers
frontend/src/pages/         Workbench pages
docs/                       Architecture, API, database, demo and safety docs
scripts/                    Local helper scripts
```

## 3. 后端结构

后端使用统一响应结构：

- 成功：`{"data": ..., "request_id": "..."}`
- 失败：`{"error": {"code": "...", "message": "...", "details": {...}}, "request_id": "..."}`

FastAPI app 在 `backend/app/main.py` 注册 Health、DB、Profile、Project、Project Rewrite、Resume、Resume Version、JD、Match、RAG、Agent、Application 和 Evaluation routers。

业务代码遵循：

- API 层只做路由和依赖注入。
- Service 层做校验和业务流程。
- Repository 层做 DB 读写。
- Model 层定义 SQLAlchemy tables。

## 4. 前端结构

前端是单页工作台，没有路由库，使用 `App.tsx` 内部状态切换页面。当前页面包括：

- Dashboard
- Profile Center
- Resume Center
- JD Center
- Match Report
- Knowledge Base
- Agent Runs
- Applications
- Evaluation
- Quality Review

前端 API 封装在 `frontend/src/api/`，通过 `requestJson` 统一解析后端响应。

## 5. 数据库和持久化

当前使用 SQLite + Alembic。核心表包括：

- `resumes`
- `resume_versions`
- `profiles`
- `projects`
- `project_rewrites`
- `job_descriptions`
- `job_profiles`
- `match_reports`
- `rag_documents`
- `rag_chunks`
- `agent_runs`
- `agent_steps`
- `applications`
- `bad_cases`
- `evaluation_runs`
- `evaluation_cases`
- `evaluation_results`

默认本地运行时使用：

```text
sqlite:///./local_data/careeragent.db
```

当从 `backend/` 目录启动后端时，该路径对应 `backend/local_data/careeragent.db`。

## 6. Deterministic AI 边界

当前不接真实 OpenAI、DeepSeek、Qwen 或其他 LLM provider。

- Profile：manual CRUD + readiness summary，不自动从简历生成画像。
- Project：manual project facts CRUD + deterministic rewrite backend，可选绑定 profile / resume version，不自动生成项目事实，不接真实 LLM。
- Resume：PDF / DOCX / Markdown / txt 文本提取 + deterministic parser / risk-check，不调用真实 LLM。
- JD：deterministic skill extraction / role category inference。
- Match：deterministic scoring。
- RAG：deterministic chunking + lexical retrieval + deterministic answer。
- Agent：deterministic state machine，不是自由工具调用 Agent。
- Evaluation：deterministic smoke set，不是 LLM judge。

### Resume Center v0.8

Resume Center 当前链路：

1. `POST /api/resumes/upload` 上传 `.pdf` / `.docx` / `.md` / `.markdown` / `.txt` synthetic resume。
2. `text_extraction_service` 对 Markdown / txt 做 UTF-8 文本读取，对 PDF 使用 PyMuPDF 文本层提取，对 DOCX 使用 python-docx 文本层提取。
3. `POST /api/resumes/{resume_id}/parse` 运行 deterministic parser，返回候选 `structured_resume`，不写入 confirmed version。
4. 前端 ResumeCenterPage 允许人工编辑 structured JSON。
5. `POST /api/resumes/{resume_id}/risk-check` 对当前 structured JSON 做确定性规则检测，返回 `risk_flags` 和 `risk_report`，不自动修改简历。
6. `POST /api/resumes/{resume_id}/versions` 保存人工确认后的 confirmed version。

当前不做 OCR，不处理扫描版 PDF 图片文字，不调用 LLM parser，也不做事实审计。

### Profile Center v0.8

Profile Center 当前链路：

1. `profiles` 表保存求职目标、目标行业、目标地点、技能结构、偏好和可选 `source_resume_version_id`。
2. Profile API 支持 create / list / detail / patch / summary。
3. ProfilePage 支持创建、选择、更新 profile，并展示 completeness / readiness summary。
4. 当前没有认证系统，`user_id` 固定为 `default`，不提供多用户权限隔离。

Profile 不从简历自动生成，也不保存身份证、详细住址、政治、健康等敏感身份信息。

### Project Optimization Backend v0.9 9A / 9B

Project optimization backend 当前链路：

1. `projects` 表保存用户手动确认的项目事实。
2. Project API 支持 create / list / detail / patch。
3. Project 可选绑定 `profile_id` 和 `resume_version_id`，绑定对象传入时会校验存在。
4. 保存字段包括项目名称、角色、周期、背景、技术栈、职责、结果和 evidence。
5. `POST /api/projects/{project_id}/rewrite` 针对 JD profile 运行 deterministic rewrite。
6. `project_rewrites` 表保存 `matched_points`、`missing_points`、`evidence_required`、`rewritten_bullets`、`forbidden_changes`、`risk_flags` 和 `rewrite_strategy`。
7. `GET /api/project-rewrites/{rewrite_id}` 查询已保存 rewrite 结果。

当前 Project Rewrite 是规则版，不接真实 LLM，不自动写入 Resume Version，不编造项目经历、指标、公司、技术栈、上线状态或业务规模；risk flags 覆盖 unsupported metric、fabricated skill、missing evidence、overclaim 和 learning-to-business overclaim。ProjectOptimizationPage 尚未实现。

### Dashboard readiness

Dashboard 当前展示：

- latest profile readiness level 和 completeness score。
- latest resume parse status 和 risk flags count。
- 原有 Resume、JD、Match、RAG、Agent、Application、Bad Case、Evaluation 统计。

## 7. 阶段完成状态

| 阶段 | 当前状态 |
| --- | --- |
| 阶段一 | Resume / JD / Match 最小闭环已完成 |
| 阶段二 | SQLite + SQLAlchemy + Alembic 持久化与 Resume Version 已完成 |
| 阶段三 | RAG lexical prototype 已完成 |
| 阶段四 | Agent deterministic workflow prototype 已完成 |
| 阶段五 | Application Tracking + Dashboard MVP 已完成 |
| 阶段六 | Deterministic Evaluation MVP + Bad Case 关联已完成 |
| v0.8 Resume/Profile Foundation | Resume parser / risk-check APIs + Profile Center MVP 已完成 |
| v0.9 Project Optimization 9A / 9B | Project facts backend 和 deterministic rewrite backend 已完成，前端页面未实现 |
| 阶段七 | 当前补齐 Docker、README、docs、demo script 和安全清单 |

## 8. 当前不做

- 不做自动投递。
- 不接招聘网站。
- 不接真实 LLM judge。
- 不做多模型评测平台。
- 不做生产级多用户权限。
- 不切 PostgreSQL / pgvector。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。
