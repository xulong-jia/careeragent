# CareerAgent 校招求职平台

CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。项目目标是把用户画像、简历版本、JD 理解、匹配评分、项目优化、面试准备、学习计划、投递管理、RAG 知识库、Agent Workflow、Bad Case 和评测体系组织成可运行、可追踪、可复查的工程链路。

CareerAgent 不是简历润色器，也不是 ChatGPT 套壳。本仓库当前已在 SQLite + SQLAlchemy 基础上支持 Profile Center MVP、Resume / JD / Match Report 持久化、Resume Version 历史管理、真实 PDF / DOCX / Markdown / txt 文本提取、deterministic resume parser / risk-check、deterministic Project Optimization、Interview Center 题目生成、答案提交、deterministic scoring 前端工作流和 Dashboard training stats、deterministic RAG knowledge base、deterministic Agent Workflow workbench、人工 Quality Review / Bad Case 闭环、手动 Application Management / 投递 tracking MVP，以及 deterministic Evaluation MVP。当前仍不接入真实 LLM reviewer、不做 LLM judge、不做多模型评测、不做大型 Evaluation Center、不做自动投递。

## 技术栈

- Backend: FastAPI, Pydantic, Uvicorn, SQLAlchemy, Alembic, SQLite
- Frontend: React, TypeScript, Vite
- Test: pytest, Vite build
- Deployment: Docker Compose 本地开发骨架
- Later phases: PostgreSQL, pgvector 或 FAISS, OCR / richer document parsing, LLM provider, controlled tool-calling Agent, richer regression evaluation

## 当前能力

- Profile Center：创建、查询、更新用户求职画像，查看 completeness / readiness summary。
- v0.8 Resume + Profile Foundation：PDF / DOCX / Markdown / txt 文本层提取、deterministic resume parser / risk-check、confirmed resume version 保存，以及 Profile CRUD / readiness summary。
- v0.9 Project Optimization：保存、查询和更新项目事实，支持可选绑定 profile / resume version；Project Rewrite backend 和 ProjectOptimizationPage 已接入 deterministic rewrite，展示 matched_points、missing_points、evidence_required、rewritten_bullets、forbidden_changes 和 risk_flags。
- v1.0 Interview Center 10A/10B/10C/10D：新增 `interview_questions` / `interview_answers` 表、deterministic question generation / list API、answer submit / list API、deterministic scoring API、InterviewCenterPage 和 Dashboard interview training stats；本阶段不做 Study Plan 写入或 LLM judge。
- Resume / JD / Match：上传 synthetic resume、解析 PDF / DOCX / Markdown / txt、创建 JD、运行 deterministic match report。
- Resume Versions：查询、clone、archive；Resume Center 已支持 parse、risk-check 和保存 confirmed structured resume version。
- RAG Knowledge Base：document、chunk/index、lexical search、deterministic answer。
- Agent Runs：deterministic `job_application_preparation` state machine。
- Application Tracking：手动投递 tracking、状态筛选、stats。
- Quality Review / Bad Case：人工记录 bad case，并可更新状态。
- Deterministic Evaluation：运行 `synthetic_smoke_v1`，保存 runs / cases / results。
- Dashboard：集中展示 Profile readiness、Resume、JD、Match、Project count / latest project status、RAG、Agent、Application、Bad Case、Evaluation 统计。

当前明确不做：

- 不做自动投递。
- 不接招聘网站。
- 不接真实 LLM judge。
- 不接真实 LLM parser、LLM reviewer 或 LLM Agent。
- 不做 OCR；PDF / DOCX 当前只做文本层提取。
- 不自动写回 Resume Version，不编造项目经历、数字、公司、技术栈、上线状态或业务规模。
- 不做多模型评测平台。
- 不做生产级多用户权限。
- 不切 PostgreSQL / pgvector。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。

## 目录结构

```text
backend/       FastAPI 应用、API 路由、配置与错误处理
frontend/      React + TypeScript + Vite 工作台 UI
docs/          架构、API、数据库、RAG、Agent、评测等文档
evals/         后续评测数据集、期望输出和评测脚本
scripts/       本地开发、检查和辅助脚本
local_data/    本地上传、向量索引、导出、日志和缓存，不进入 Git
```

## 本地运行

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/health
```

### 前端

```bash
cd frontend
npm install
cp .env.example .env.local  # 可选；默认 VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

默认访问：

```text
http://localhost:5173
```

### Docker Compose

```bash
docker compose build
docker compose up
```

Docker Compose 只用于本地开发启动前后端服务。后端容器启动时会执行 `alembic upgrade head`，SQLite 数据通过 bind mount 保存到 `backend/local_data/careeragent.db`。当前阶段不接入 LLM、embedding、vector store，不挂载真实简历、真实 JD、真实文档、投递记录或面试复盘。

## 环境变量

复制 `.env.example` 为 `.env` 后再按需填写本地配置。当前默认使用本地 SQLite，不需要任何真实 API Key。

```bash
cp .env.example .env
```

仓库只提交 `.env.example`，不会提交 `.env`。

关键变量：

- `DATABASE_URL=sqlite:///./local_data/careeragent.db`：从 `backend/` 启动时写入 `backend/local_data/careeragent.db`。
- `VITE_API_BASE_URL=http://localhost:8000`：前端 API base URL。
- `OPENAI_API_KEY=`：当前 deterministic MVP 不依赖，保持空即可。

## Demo Flow

本地后端启动并完成 migration 后，可以运行 synthetic seed script：

```bash
python3 scripts/seed_demo_data.py
```

如果 API 地址不同：

```bash
CAREERAGENT_API_BASE_URL=http://localhost:8000 python3 scripts/seed_demo_data.py
```

脚本只通过公开 HTTP API 创建 synthetic demo data，包括 resume、JD、match、RAG document、Agent run、Application、Bad Case 和 Evaluation run。Project Optimization 仍建议在前端手动创建 synthetic project facts 并运行 rewrite。

手动演示建议顺序：

1. Dashboard 查看总览。
2. Resume Center 上传 synthetic resume，运行 Parse，编辑 structured JSON，执行 Risk Check，并保存 confirmed version。
3. Profile Center 创建 synthetic profile 并查看 readiness。
4. Dashboard 查看 profile readiness、resume parse status 和 risk flags count。
5. JD Center 创建 synthetic JD。
6. Project Optimization 创建 synthetic project facts，输入 JD ID 运行 deterministic rewrite。
7. Match Report 运行匹配。
8. Interview Center 输入 JD ID 和 Resume Version ID 生成题目，提交 synthetic answer，并运行 deterministic scoring；回到 Dashboard 查看 Interview Training stats。
9. Knowledge Base 创建文档、index、search、answer。
10. Agent Runs 运行 deterministic workflow。
11. Applications 创建手动投递记录。
12. Quality Review 创建 Bad Case。
13. Evaluation 运行 `synthetic_smoke_v1`。

完整流程见 [docs/demo-script.md](docs/demo-script.md)。

## 文档索引

- 当前架构：[docs/current-architecture.md](docs/current-architecture.md)
- API Reference：[docs/api-reference.md](docs/api-reference.md)
- Database Schema：[docs/database-schema.md](docs/database-schema.md)
- Safety / Privacy Checklist：[docs/safety-privacy-checklist.md](docs/safety-privacy-checklist.md)
- Demo Script：[docs/demo-script.md](docs/demo-script.md)
- Final Acceptance Report：[docs/final-acceptance-report.md](docs/final-acceptance-report.md)
- v0.7 Release Notes：[docs/release-notes-v0.7.md](docs/release-notes-v0.7.md)
- v0.8 Release Notes：[docs/release-notes-v0.8.md](docs/release-notes-v0.8.md)
- v0.9 Release Notes：[docs/release-notes-v0.9.md](docs/release-notes-v0.9.md)
- v1.0 Release Notes：[docs/release-notes-v1.0.md](docs/release-notes-v1.0.md)

## 当前阶段完成内容

阶段 0 已完成：

- 创建基础目录：`backend/`、`frontend/`、`docs/`、`evals/`、`scripts/`、`local_data/`、`docs/screenshots/`
- 创建根目录文件：`README.md`、`.gitignore`、`.env.example`、`docker-compose.yml`
- 后端初始化：FastAPI 应用、`GET /health`、基础配置、统一错误响应结构
- 前端初始化：React + TypeScript + Vite、Dashboard、Resume Center、JD Center、Match Report、简单导航
- 安全规则：忽略 `.env`、`local_data/`、uploads、vector_index、exports、logs、cache、私有数据目录和本地构建产物
- 不包含真实 LLM API 调用、真实 RAG embedding/vector store、真实 LLM Agent、真实 API Key 或隐私数据

阶段 1A / 1B / 1C 已完成：

- 阶段一 Resume 占位接口：上传校验、列表、详情。
- 阶段一 JD 占位接口：创建、列表、详情、deterministic profile。
- 阶段一 Match 占位接口：运行、列表、详情、deterministic rule score。
- 阶段一前端内存闭环：上传 Resume、创建 JD、运行 Match、展示报告。
- 内存 Mock Store：后端重启后数据会丢失。
- 契约加固：统一成功/错误响应、基础错误路径测试、服务层拆分。
- 最小文本提取：`.md`、`.markdown`、`.txt` 真实读取 UTF-8 文本。
- Parser placeholder：`.pdf`、`.docx` 返回明确 placeholder、extraction status、method 和 warnings，不假装真实解析成功。
- 安全边界：不保存真实上传文件到 Git，不调用真实 LLM/RAG/Agent。

阶段 2A / 2B / 2C / 2D / 2E / 2F / 2G 已完成：

- 2A：完成阶段二持久化与版本管理设计文档。
- 2B：新增 SQLite + SQLAlchemy + Alembic 基础设施、ORM skeleton、初始 migration 和 DB health check。
- 2C：Resume / JD 主路径已切换为 SQLite 持久化，创建 Resume 时生成 initial resume version，创建 JD 时生成 job profile。
- 2D：新增 Resume Version 后端 API，支持版本历史、详情、clone 和 archive；archive 是软归档，不删除历史内容。
- 2E：Match Report 主路径已切换为 SQLite 持久化，报告绑定 `resume_version_id + jd_id`，`GET /api/matches` 返回 DB 历史报告。
- 2F：前端展示 DB-backed Resume / JD / Match 历史；Resume Center 支持 versions 查看、clone 和 archive；Match Report 支持历史查看。
- 2G：补充阶段二验收文档、安全检查说明和 README 收口说明。
- 当前复杂 diff、多版本对比图表、同一 JD 多版本对比页面仍未实现，留到后续阶段。

阶段二验收文档：[docs/phase-2-acceptance.md](docs/phase-2-acceptance.md)

阶段 3A / 3B / 3C / 3D / 3E / 3F / 3G 已完成：

- 3A：完成 RAG 知识库设计文档与边界确认。
- 3B：新增 `rag_documents` / `rag_chunks` ORM models、Alembic migration、schema skeleton 和 DB smoke tests。
- 3C：新增 RAG document create / list / detail、deterministic chunking / indexing backend 和 chunks list API。
- 3D：新增 deterministic lexical retrieval 和 `POST /api/rag/search`，返回 sources / score / snippet / metadata。
- 3E：新增 deterministic RAG answer 和 `POST /api/rag/answer`，有来源时 grounded，无来源时返回 uncertainty。
- 3F：新增 KnowledgeBasePage 最小 UI，支持创建 document、index、查看 chunks、search 和 answer with citations。
- 3G：补充阶段三 RAG 验收文档、synthetic test set 示例、安全检查说明和 README 收口说明。
- 当前不包含真实 LLM、embedding、vector store、复杂 RAG evaluation dashboard、Study Plan 正式集成或真实 LLM Agent；Interview Center 目前已完成 10A/10B 后端题目生成、答案提交、deterministic scoring、10C 前端页面接入和 10D Dashboard interview training stats。

阶段三设计文档：[docs/rag-design.md](docs/rag-design.md)

阶段三验收文档：[docs/phase-3-rag-acceptance.md](docs/phase-3-rag-acceptance.md)

阶段 4A / 4B / 4C / 4D / 4E / 4F 已完成：

- 4A：完成 Agent Workflow 设计文档与边界确认。
- 4B：新增 `agent_runs` / `agent_steps` ORM models、Alembic migration、schema skeleton 和 DB infrastructure tests。
- 4C：新增 deterministic workflow runner、fixed workflow `job_application_preparation`、step execution、`need_more_info`、failed behavior 和 step timeline persistence。
- 4D：新增 Agent Runs API，支持 create run、list runs、run detail 和 steps timeline。
- 4E：新增 AgentRunsPage 最小 UI，支持创建 deterministic workflow run、查看 runs list、run detail 和 steps timeline。
- 4F：补充阶段四验收文档、安全检查说明和 README 收口说明。
- 当前 Agent Workflow 是 deterministic state machine，不是真实 LLM Agent，不是自由聊天 Agent，不自动投递。

阶段四设计文档：[docs/agent-workflow-design.md](docs/agent-workflow-design.md)

阶段四验收文档：[docs/phase-4-agent-workflow-acceptance.md](docs/phase-4-agent-workflow-acceptance.md)

Quality Review / Bad Case 原型已完成：

- 完成 Quality Review / Bad Case 设计文档与边界确认。
- 新增 `bad_cases` ORM model、Alembic migration、schema skeleton 和 DB infrastructure tests。
- 新增 Bad Case repository / service / API 和 tests，支持 create、list、filter、detail、patch。
- 新增 QualityReviewPage 最小 UI，支持人工创建、筛选、查看和更新 bad case。
- 新增 MarkBadCasePanel，并在 Match / Knowledge Base / Agent Runs 页面加入轻量 Mark as bad case 入口。
- 补充 Quality Review 验收文档、安全检查说明和 README 收口说明。
- 当前 Quality Review 是人工 review record，不是真实 LLM reviewer，不做自动评估、不做自动投递、不做 Evaluation Center。

Quality Review 设计文档：[docs/quality-review-design.md](docs/quality-review-design.md)

Quality Review 验收文档：[docs/phase-5-quality-review-acceptance.md](docs/phase-5-quality-review-acceptance.md)

阶段五：Application Management / 手动投递管理与 Dashboard MVP 已完成：

- 新增 `applications` ORM model、Alembic migration、schema、repository、service、API 和 tests。
- 新增 ApplicationTrackerPage，支持手动创建投递记录、列表、详情、按状态筛选、状态更新和统计摘要。
- Dashboard 已接入 application stats，展示投递总数、面试中数量、Offer、Rejected 和 Active 数量。
- 投递记录可选绑定 `jd_id`、`resume_version_id`、`match_report_id`；绑定对象存在时会校验 refs。
- 当前只做手动 tracking，不自动投递、不接招聘网站、不接真实 LLM，不保存简历原文或 JD 原文到投递 API 响应。

投递管理设计文档：[docs/application-management-design.md](docs/application-management-design.md)

阶段六：Deterministic Evaluation / 评测体系 MVP 已完成：

- 新增 `evaluation_runs` / `evaluation_cases` / `evaluation_results` ORM models、Alembic migration、schema、repository、service、API 和 tests。
- 新增内置 `synthetic_smoke_v1`，覆盖 Match、RAG、Agent、Application 和 Bad Case 的确定性 contract 检查。
- 新增 EvaluationPage，支持查看 stats、运行 synthetic smoke evaluation、查看 runs、metrics、results 和 cases。
- Evaluation Case 可选关联 `bad_case_id`，也支持从已有 Bad Case 创建可追踪 evaluation case。
- Dashboard 已接入 evaluation stats，展示 run 数、最新 pass rate 和失败结果数量。
- 当前评测目标是回归和质量追踪，不是给模型能力打最终分；不接真实 LLM judge，不做多模型对比，不做大型评测平台。

评测体系设计文档：[docs/evaluation-design.md](docs/evaluation-design.md)

v1.0 Interview Center 10A/10B/10C/10D 题目生成、答案提交、答案评分、前端页面和 Dashboard training stats 已完成：

- 新增 `interview_questions` / `interview_answers` ORM models 和 Alembic migration。
- 新增 `POST /api/interviews/questions/generate`，基于 JD profile、structured resume、可选 project facts 和 project rewrite 结果生成 deterministic interview questions。
- 新增 `GET /api/interviews/questions`，支持按 `jd_id`、`resume_version_id`、`project_id`、`question_type` 和 `difficulty` 筛选。
- 每个问题保存 `source_refs`，只包含 `source_type`、`source_id`、`field`、`label` 和短 `preview`，不返回 Resume/JD full raw_text。
- 新增 `POST /api/interviews/answers`、`GET /api/interviews/answers` 和 `POST /api/interviews/answers/{answer_id}/score`。
- Answer API 默认只返回 `answer_text_preview`；完整 `answer_text` 仅保存在本地 DB，用于 deterministic scoring。
- Scoring 输出 `structure`、`technical_depth`、`business_understanding`、`evidence`、`clarity`、`risk_control`、`overall_average`、`feedback` 和 `weakness_tags`。
- 新增 InterviewCenterPage，支持生成 questions、筛选 / 选择 question、提交 answer preview-first response、查看 answer list，并对 selected answer 运行 deterministic scoring。
- 新增 `GET /api/interviews/stats` 和 Dashboard Interview Training stats，展示 question count、answer count、scored answer count、latest average score 和 latest weakness tags。
- v1.0 final handoff 已补充 release notes、验收说明和安全边界。Study Plan 写入、RAG completion、Agent full workflow 和 LLM judge 留到后续阶段。

## API

当前开放的工作台 API：

```text
GET /health
GET /api/db/health
POST /api/profiles
GET /api/profiles
GET /api/profiles/{profile_id}
PATCH /api/profiles/{profile_id}
GET /api/profiles/{profile_id}/summary
POST /api/projects
GET /api/projects
GET /api/projects/{project_id}
PATCH /api/projects/{project_id}
POST /api/projects/{project_id}/rewrite
GET /api/project-rewrites/{rewrite_id}
POST /api/resumes/upload
POST /api/resumes/{resume_id}/parse
POST /api/resumes/{resume_id}/risk-check
POST /api/resumes/{resume_id}/versions
GET /api/resumes
GET /api/resumes/{resume_id}
GET /api/resumes/{resume_id}/versions
GET /api/resume-versions/{version_id}
POST /api/resume-versions/{version_id}/clone
PATCH /api/resume-versions/{version_id}/archive
POST /api/jobs
GET /api/jobs
GET /api/jobs/{jd_id}
POST /api/matches/run
GET /api/matches
GET /api/matches?jd_id={jd_id}
GET /api/matches?resume_version_id={resume_version_id}
GET /api/matches/{match_report_id}
POST /api/interviews/questions/generate
GET /api/interviews/questions
POST /api/interviews/answers
GET /api/interviews/answers
POST /api/interviews/answers/{answer_id}/score
GET /api/interviews/stats
POST /api/rag/documents
GET /api/rag/documents
GET /api/rag/documents/{doc_id}
POST /api/rag/documents/{doc_id}/index
GET /api/rag/chunks
POST /api/rag/search
POST /api/rag/answer
POST /api/agents/runs
GET /api/agents/runs
GET /api/agents/runs/{run_id}
GET /api/agents/runs/{run_id}/steps
POST /api/applications
GET /api/applications
GET /api/applications?status={status}
GET /api/applications?company={company}
GET /api/applications?role_category={role_category}
GET /api/applications?resume_version_id={resume_version_id}
GET /api/applications?jd_id={jd_id}
GET /api/applications/{application_id}
PATCH /api/applications/{application_id}
GET /api/applications/stats
POST /api/evaluations/runs
GET /api/evaluations/runs
GET /api/evaluations/runs/{run_id}
GET /api/evaluations/runs/{run_id}/results
GET /api/evaluations/cases
POST /api/evaluations/cases
POST /api/evaluations/cases/from-bad-case/{case_id}
GET /api/evaluations/stats
POST /api/evaluations/bad-cases
GET /api/evaluations/bad-cases
GET /api/evaluations/bad-cases/{bad_case_id}
PATCH /api/evaluations/bad-cases/{bad_case_id}
```

成功响应结构：

```json
{
  "data": {
    "status": "ok",
    "service": "CareerAgent API",
    "environment": "development"
  },
  "request_id": "..."
}
```

错误响应结构：

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found.",
    "details": {}
  },
  "request_id": "..."
}
```

### 手动跑通 v0.9 Project Optimization

1. 启动后端和前端。
2. 打开 `http://localhost:5173`。
3. 进入 Resume Center，上传 `.pdf`、`.docx`、`.md`、`.markdown` 或 `.txt` synthetic resume，确认 raw text preview 展示真实提取文本。
4. 点击 `Parse selected resume`，编辑 structured resume JSON，点击 `Run risk check`，再填写 version name / target role 并保存 confirmed version。
5. 进入 Profile Center，创建 synthetic profile，确认 readiness summary 展示 completeness。
6. 回到 Dashboard，确认 profile readiness、resume parse status 和 risk flags count 已展示。
7. 进入 JD Center，填写 company、job title、location 和 raw JD text，创建 JD。
8. 进入 Project Optimization，创建 synthetic project facts，输入 JD ID，运行 deterministic rewrite，查看 matched points、missing points、evidence required、rewritten bullets、forbidden changes 和 risk flags。
9. 进入 Match Report，点击 `Run Match`。
10. 查看总分、维度分、evidence、gaps 和 rewrite priorities。

PDF / DOCX / Markdown / txt 返回结果会包含：

- `extraction_status`: `extracted`
- `extraction_method`: `pymupdf_text`、`python_docx_text`、`utf8_md_decode`、`utf8_markdown_decode` 或 `utf8_txt_decode`
- `raw_text_preview`: 真实读取到的文本预览

PDF / DOCX 只做文本层提取，不做 OCR。扫描版 PDF、图片简历或复杂版式可能无法完整抽取文本。

当前阶段说明：

- Profile Center：支持 profiles 表、Profile API、ProfilePage 和 Dashboard readiness summary；当前不做认证、多用户权限或自动从简历生成画像。
- Project Optimization：支持 `projects` / `project_rewrites` 表、Project CRUD API、deterministic Project Rewrite API、ProjectOptimizationPage 和 Dashboard project readiness 摘要，用于保存项目事实并展示基于现有 facts 的 rewrite suggestions；当前不接真实 LLM，不自动写回 Resume Version，不编造项目经历、数字、公司、技术栈、上线状态或业务规模。
- Deterministic：结构化简历解析、risk-check、JD 解析和匹配评分仍是 deterministic 规则，不调用真实 LLM。
- Risk-check：当前只做可确定规则检测，不是事实审计，不自动修改简历。
- SQLite 持久化：Resume / JD 数据默认保存到 `DATABASE_URL` 指定位置，默认 `local_data/careeragent.db`。
- Match Report 持久化：报告默认绑定 `resume_version_id + jd_id`，并保存到 SQLite。
- 版本管理：Resume Version 已支持历史查询、详情、clone 和 archive；archive 是软归档，不删除历史内容。
- 前端展示：Resume Center 可查看 versions、clone、archive、parse、risk-check 和保存 confirmed version；Match Report 可查看 DB 历史和详情。
- 版本边界：复杂版本 diff / compare UI、同一 JD 多版本对比页面仍未实现，留到后续阶段。
- 无真实 LLM：没有 OpenAI、DeepSeek、Qwen 或其他模型调用。
- RAG 知识库：支持 document 管理、deterministic chunking/indexing、lexical search、deterministic answer with citations 和 KnowledgeBasePage。
- RAG 边界：没有真实 embedding、FAISS、pgvector、vector store、真实 LLM answer、reranker 或 RAG evaluation dashboard。
- Agent Workflow：支持 deterministic `job_application_preparation` workflow、Agent Runs API 和 AgentRunsPage。
- Agent 边界：没有真实 LLM Agent、自由聊天 Agent 或 true tool-calling Agent；Agent Workflow 当前不自动创建投递记录、不自动投递，也不接招聘网站或 Evaluation Center。
- Quality Review：支持 `bad_cases` 持久化、Bad Case API、QualityReviewPage 和 Mark as bad case 入口。
- Quality Review 边界：当前是人工 review record，不是真实 LLM reviewer，不做自动评估、不做自动投递、不做 Evaluation Center。
- Application Management：支持手动投递 tracking、application stats 和 ApplicationTrackerPage。
- Interview Center：支持 question generation、answer submit/list、deterministic scoring、InterviewCenterPage 和 Dashboard interview training stats；不接真实 LLM judge，不自动写入 Study Plan。
- Application 边界：不自动投递、不接招聘网站、不保存完整投递材料、不自动状态流转。
- Evaluation：支持 deterministic `synthetic_smoke_v1`、evaluation runs / cases / results 持久化、EvaluationPage 和 Bad Case 可选关联。
- Evaluation 边界：不接真实 LLM judge，不做多模型对比，不做大型评测平台，不把评测结果当作模型能力最终评分。

## 安全与隐私

- 不提交 `.env`、真实 API Key 或任何私密凭据。
- 不提交真实简历、真实 JD、投递记录、面试复盘、上传文件、向量索引、导出文件、日志和缓存。
- `local_data/` 仅用于本地运行数据，并已加入 `.gitignore`。
- 开发执行手册只作为上下文使用，不复制、不移动、不提交到仓库。
- RAG 测试和验收只使用 synthetic data；前端默认展示 preview / snippet，不默认展示完整 raw_text 或完整 chunk text。
- Resume / JD raw_text 仍保存在本地 DB，用于 parse、risk-check、match 和 deterministic profile extraction；默认 API response 和 UI 只返回 / 展示 `raw_text_preview`，不暴露完整 raw_text。
- Agent step payload 只保存 IDs、refs 和 short metadata，不保存完整 resume raw_text、JD raw_text 或 RAG chunk text。
- AgentRunsPage 使用 safe JSON render helper 过滤敏感字段，避免展示隐私原文。
- Bad Case 只保存 `source_type` / `source_id` 和问题摘要，不自动复制 Resume / JD / RAG chunk / Agent refs 原文。
- Application API 只保存投递状态、refs、日期和摘要备注，不复制 Resume raw_text、JD raw_text 或 Match 源对象全文。
- Profile API 只保存目标岗位、地点、行业、技能结构、偏好和可选 resume version ref，不复制 Resume raw_text。
- Profile 不应保存身份证、详细住址、政治、健康等敏感身份信息；当前无认证系统，`user_id` 默认 `default`。
- Project facts 只应保存用户确认的 synthetic 或可公开复述项目事实，不应粘贴真实公司私密信息、敏感商业数据或大段内部材料。
- Project Rewrite 只基于已有 project facts 生成建议；不自动写回 Resume Version，不编造公司、用户量、收益、准确率、上线状态、业务规模或技术栈。
- Interview Question generation 只基于 JD profile、structured resume、project facts 和 project rewrite refs；不读取或返回 Resume/JD full raw_text，不诱导编造上线、收益、用户量、准确率或公司经历。
- Interview Answer submit / scoring 只默认返回 `answer_text_preview`、scores、feedback 和 `weakness_tags`；完整 `answer_text` 仅保存在本地 DB 用于 deterministic scoring，不进入默认 API payload、Dashboard 或 stats。Dashboard interview stats 只读取聚合计数、latest average score 和 latest weakness tags，不展示完整回答原文。
- Evaluation Case 只保存 synthetic payload、结构化 refs 或摘要字段；从 Bad Case 创建 case 时不复制源对象 raw_text。

## v1.0 验收结果

2026-06-25 在 `main` 执行：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：216 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `docker compose config`：通过。
- `python3 -m py_compile scripts/seed_demo_data.py`：通过。
- `git diff --check`：通过。
- `docker compose build`：未完成，原因是本机 Docker daemon/socket 不可用，不是代码构建失败；`docker compose config` 已通过。

## 自查命令

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose config
PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
git status --short --branch
git diff --check
```

## 后续阶段规划

1. 阶段一：最小可运行闭环，跑通简历上传、JD 输入、解析、匹配评分和报告展示。
2. 阶段二：数据持久化与版本管理，引入数据库、简历版本、JD 历史和匹配报告历史。
   - 设计文档：[docs/phase-2-persistence-design.md](docs/phase-2-persistence-design.md)
   - 验收文档：[docs/phase-2-acceptance.md](docs/phase-2-acceptance.md)
   - Release notes：[docs/release-notes-v0.2.0-persistence.md](docs/release-notes-v0.2.0-persistence.md)
3. 阶段三：RAG 知识库，建立 RAG document、chunk、metadata、lexical search、deterministic answer 和来源引用。
   - 设计文档：[docs/rag-design.md](docs/rag-design.md)
   - 验收文档：[docs/phase-3-rag-acceptance.md](docs/phase-3-rag-acceptance.md)
   - Release notes：[docs/release-notes-v0.3.0-rag.md](docs/release-notes-v0.3.0-rag.md)
4. 阶段四：Agent Workflow，用 deterministic state machine 串联 Resume / JD / Match / RAG，并提供 Agent Runs API 和 AgentRunsPage。
   - 设计文档：[docs/agent-workflow-design.md](docs/agent-workflow-design.md)
   - 验收文档：[docs/phase-4-agent-workflow-acceptance.md](docs/phase-4-agent-workflow-acceptance.md)
   - Release notes：[docs/release-notes-v0.4.0-agent-workflow.md](docs/release-notes-v0.4.0-agent-workflow.md)
5. 阶段五：Application Management / 手动投递管理与 Dashboard，当前已具备 MVP，可绑定 JD、简历版本、Match Report、状态、下一步日期和摘要备注；该阶段只做手动 tracking，不做自动投递，不接招聘网站，不自动提交申请。
   - 设计文档：[docs/application-management-design.md](docs/application-management-design.md)
6. 阶段六：评测体系与 Bad Case，当前已具备 deterministic evaluation MVP，支持 evaluation runs / cases / results、内置 smoke set、Bad Case 可选关联和 EvaluationPage；后续可继续沉淀 regression set、失败样例回归和更完整指标。
   - 设计文档：[docs/evaluation-design.md](docs/evaluation-design.md)
   - Quality Review 设计文档：[docs/quality-review-design.md](docs/quality-review-design.md)
   - Quality Review 验收文档：[docs/phase-5-quality-review-acceptance.md](docs/phase-5-quality-review-acceptance.md)
   - Quality Review release notes：[docs/release-notes-v0.5.0-quality-review.md](docs/release-notes-v0.5.0-quality-review.md)
7. 阶段七：工程化交付，补齐 Docker、文档、演示材料、安全说明和最终验收记录。
