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

FastAPI app 在 `backend/app/main.py` 注册 Health、DB、Resume、Resume Version、JD、Match、RAG、Agent、Application 和 Evaluation routers。

业务代码遵循：

- API 层只做路由和依赖注入。
- Service 层做校验和业务流程。
- Repository 层做 DB 读写。
- Model 层定义 SQLAlchemy tables。

## 4. 前端结构

前端是单页工作台，没有路由库，使用 `App.tsx` 内部状态切换页面。当前页面包括：

- Dashboard
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

- Resume：读取 txt/markdown；PDF/DOCX 是 parser placeholder。
- JD：deterministic skill extraction / role category inference。
- Match：deterministic scoring。
- RAG：deterministic chunking + lexical retrieval + deterministic answer。
- Agent：deterministic state machine，不是自由工具调用 Agent。
- Evaluation：deterministic smoke set，不是 LLM judge。

## 7. 阶段完成状态

| 阶段 | 当前状态 |
| --- | --- |
| 阶段一 | Resume / JD / Match 最小闭环已完成 |
| 阶段二 | SQLite + SQLAlchemy + Alembic 持久化与 Resume Version 已完成 |
| 阶段三 | RAG lexical prototype 已完成 |
| 阶段四 | Agent deterministic workflow prototype 已完成 |
| 阶段五 | Application Tracking + Dashboard MVP 已完成 |
| 阶段六 | Deterministic Evaluation MVP + Bad Case 关联已完成 |
| 阶段七 | 当前补齐 Docker、README、docs、demo script 和安全清单 |

## 8. 当前不做

- 不做自动投递。
- 不接招聘网站。
- 不接真实 LLM judge。
- 不做多模型评测平台。
- 不做生产级多用户权限。
- 不切 PostgreSQL / pgvector。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。
