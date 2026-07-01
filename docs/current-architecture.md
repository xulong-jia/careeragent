# CareerAgent 当前架构说明

本文档描述当前仓库真实实现状态。历史阶段文档保留当时阶段边界；如果历史文档写“暂不做某模块”，以本文档和 README 的当前状态为准。

阶段 2.1 口径：当前版本是 production hardening + real evaluation foundation，不是 production-ready。deterministic、mock、synthetic、prototype、本地可演示或骨架完整模块只能算 foundation / partial / risky。生产缺口基线见 `docs/production-gap-baseline.md`，质量门禁见 `docs/quality-gates.md`，评测基础见 `docs/real-evaluation-foundation.md`。

## 1. 当前定位

CareerAgent 是面向校招和留学生回国求职场景的 AI 求职工作台原型。它不是自动投递工具，不接招聘网站，不做真实 LLM Agent，也不把 evaluation 结果当作模型能力最终评分。

当前系统是本地 SQLite-backed deterministic prototype，P1 已补上生产化基础安全层：

- 后端：FastAPI + Pydantic + SQLAlchemy + Alembic + SQLite。
- 前端：React + TypeScript + Vite。
- 数据：默认本地 SQLite，`local_data/` 不进入 Git。
- Auth / Workspace：P1 新增 email/password 注册登录、PBKDF2 password hash、HS256 bearer token、workspace membership 和 request-scoped owner filter；除 health、register、login 外，工作台 API 默认要求 bearer token。
- AI 边界：当前 Resume/JD/Match/Project/RAG/Agent/Evaluation 默认均为 deterministic 规则或状态机；v1.6 新增 opt-in provider readiness，但默认不调用真实 LLM 或外部 embedding API。
- Privacy / Governance：v1.5C 提供本地 prototype 级 redaction、preview 收敛、删除/归档 API 和版本元数据追踪；P1 新增 privacy export、delete-all 和 audit-log baseline。不等同生产级合规删除、备份擦除、SLA、SIEM 或法务合规体系。
- Deployment readiness：v1.6 补齐 provider config、health visibility、Docker/env placeholders 和部署文档；P1 补 PostgreSQL driver readiness。阶段 2.0 要求 Docker Compose 不接受空 `AUTH_JWT_SECRET`，本地可用 dev-only secret，production 必须注入强随机 secret，但默认运行仍是本地 deterministic。

## 2. 目录结构

```text
backend/app/api/            FastAPI routes
backend/app/schemas/        Pydantic request/response schemas
backend/app/services/       业务逻辑和 deterministic runner
backend/app/repositories/   SQLAlchemy persistence access
backend/app/models/         ORM models
backend/app/rag/            chunking / lexical retrieval / deterministic answering
backend/app/ai/             provider interfaces, deterministic fallback, schema validation
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

FastAPI app 在 `backend/app/main.py` 注册 Health、Auth、DB、Profile、Project、Project Rewrite、Interview、Study Plan、Resume、Resume Version、JD、Match、RAG、Agent、Application、Evaluation 和 Privacy routers。`GET /health`、`POST /api/auth/register`、`POST /api/auth/login` 是公开入口；其余工作台 routers 通过 `require_active_user` 依赖设置当前 `user_id` / `workspace_id`。

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
- Project Optimization
- Interview Center
- Study Plan Center
- Knowledge Base
- Agent Runs
- Applications
- Evaluation
- Quality Review

InterviewCenterPage 已实现；v1.0 10A/10B/10C/10D 已接入后端 tables、question generation / list、answer submit / list、deterministic scoring API 和 Dashboard stats。

Study Plan Center 当前处于 v1.1 11A/11B/11C/11D：后端 `study_plans` 表、deterministic generate API、list/detail、task status update 和 stats API 已完成，StudyPlanPage 和 Dashboard study stats 已接入。

前端 API 封装在 `frontend/src/api/`，通过 `requestJson` 统一解析后端响应。P1 后 `frontend/src/api/client.ts` 统一注入 bearer token，收到 401 会清理 token 并触发 auth-expired 事件；`App.tsx` 在未登录时展示 `AuthPage`，登录后再加载工作台数据。

## 5. 数据库和持久化

当前使用 SQLite + Alembic。核心表包括：

- `users`
- `workspaces`
- `workspace_memberships`
- `audit_logs`
- `resumes`
- `resume_versions`
- `profiles`
- `projects`
- `project_rewrites`
- `interview_questions`
- `interview_answers`
- `study_plans`
- `job_descriptions`
- `job_profiles`
- `match_reports`
- `rag_documents`
- `rag_chunks`
- `rag_answer_runs`
- `agent_runs`
- `agent_steps`
- `applications`
- `application_status_history`
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

默认不接真实 OpenAI、DeepSeek、Qwen 或其他 LLM/embedding provider。v1.6 新增 `backend/app/ai` provider interface 和 OpenAI-compatible HTTP skeleton，只有显式配置 `ENABLE_REAL_LLM=true` 或 `ENABLE_REAL_EMBEDDING=true` 且提供对应 base URL / API key / model 时才尝试外部调用。

- Profile：manual CRUD + readiness summary，不自动从简历生成画像。
- Project：manual project facts CRUD + deterministic rewrite backend + ProjectOptimizationPage，可选绑定 profile / resume version，不自动生成项目事实，不接真实 LLM。
- Interview：v1.0 10A/10B/10C/10D 提供 deterministic question generation / list、answer submit / list、scoring API、stats API、InterviewCenterPage 和 Dashboard training stats，基于 JD profile、structured resume、可选 project facts、project rewrite refs、可选 grounded RAG answer run refs、question expected_points/source_refs 和本地 DB answer，不做 LLM judge。
- Study Plan：v1.1 11A/11B/11C/11D 提供 `study_plans` 表、`POST /api/study-plans/generate`、list/detail、task status update、stats API、frontend API wrapper、StudyPlanPage 和 Dashboard study stats，基于 Profile target_roles / skill_map、Match gaps / rewrite_priorities、Project Rewrite missing_points / evidence_required、Interview weakness_tags、可选 grounded RAG answer run refs 和 request weakness_tags 生成 deterministic phases/tasks/resources/deliverables/acceptance criteria；v1.3 Agent Workflow 可调用 generation，但不做真实 LLM、外部学习平台、日历提醒或自动修改简历/项目/面试答案。
- Resume：PDF / DOCX / Markdown / txt 文本提取 + deterministic parser / risk-check，不调用真实 LLM。
- JD：deterministic skill extraction / role category inference。
- Match：deterministic scoring。
- RAG：chunking + lexical/vector/hybrid local retrieval + DB-persisted chunk vectors + deterministic grounded answer。v1.2 RAG Completion deterministic MVP 已完成，覆盖 contract tightening、grounded answer persistence、KnowledgeBasePage answer history UI、Dashboard RAG stats 和 optional downstream refs；阶段 2.2 增加 local bag-of-words embedding、embedding metadata persistence、score threshold 和 provider metadata。默认 retrieval mode 仍为 lexical，不接真实 LLM、外部 semantic embedding 或 production vector DB。
- Agent：v1.3 deterministic workflow baseline，固定 `job_application_preparation` state machine 串联 Resume Version、JD、Match、可选 RAG search、RAG context summary、Project Rewrite、Interview Questions、Study Plan 和 Application linkage；不是自由工具调用 Agent，不自动投递。
- Evaluation：v1.5B deterministic smoke/regression foundation，包含 7 模块 smoke set、Bad Case regression linkage 和文件化 eval runner，不是 LLM judge；v1.5C 在 API run_config 和 fileized metrics 中加入 prompt/schema/retrieval/model/code/evaluation version metadata；阶段 2.1 新增 `service_level` 脱敏样例集，runner 真实调用当前 service/retriever/parser/agent 路径并输出 metrics、failed cases、actual outputs 和 run config。
- Privacy / Data Governance：v1.5C 新增 `app.core.privacy` redaction helpers、`app.core.versioning` constants、Resume/JD/Application/RAG delete/archive endpoints、默认列表隐藏 deleted/archived 数据，以及前端确认式删除/归档入口。P1 增加当前 user/workspace scope 的 privacy export、delete-all 和 audit-log baseline。Resume/JD/RAG 默认响应只展示短 preview；Agent step/final summary、Bad Case、Evaluation 和 Application 只保存 refs、summary、counts 或 version metadata，不保存大段原文。

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
4. P1 后 profile create/list/detail/summary 按当前认证上下文写入和过滤 `user_id` / `workspace_id`；历史本地数据可能仍带默认 owner。

Profile 不从简历自动生成，也不保存身份证、详细住址、政治、健康等敏感身份信息。

### Project Optimization v0.9 9A / 9B / 9C / 9D / 9E

Project Optimization 当前链路：

1. `projects` 表保存用户手动确认的项目事实。
2. Project API 支持 create / list / detail / patch。
3. Project 可选绑定 `profile_id` 和 `resume_version_id`，绑定对象传入时会校验存在。
4. 保存字段包括项目名称、角色、周期、背景、技术栈、职责、结果和 evidence。
5. `POST /api/projects/{project_id}/rewrite` 针对 JD profile 运行 deterministic rewrite。
6. `project_rewrites` 表保存 `matched_points`、`missing_points`、`evidence_required`、`rewritten_bullets`、`forbidden_changes`、`risk_flags` 和 `rewrite_strategy`。
7. `GET /api/project-rewrites/{rewrite_id}` 查询已保存 rewrite 结果。
8. ProjectOptimizationPage 接入 Project CRUD 和 Project Rewrite API，支持创建 / 更新项目事实、选择项目、输入 JD ID、运行 rewrite、展示 matched / missing / evidence / rewritten bullets / forbidden changes / risk flags。
9. Dashboard 展示 project count、active project count、latest project name/status，并提供 Project Optimization 入口。
10. v0.9 final handoff 文档记录 release notes、验收结果、安全边界和后续不做范围。

当前 Project Rewrite 是规则版，不接真实 LLM，不自动写入 Resume Version，不编造项目经历、指标、公司、技术栈、上线状态或业务规模；risk flags 覆盖 unsupported metric、fabricated skill、missing evidence、overclaim 和 learning-to-business overclaim。ProjectOptimizationPage 只展示建议，不自动修改简历版本或项目事实。

### Interview Center v1.0 10A/10B/10C/10D

Interview 10A/10B/10C/10D 当前链路：

1. `interview_questions` 表保存生成的面试题，绑定 `jd_id` 和 `resume_version_id`，可选绑定 `project_id` / `project_rewrite_id`。
2. `interview_answers` 表保存用户提交的完整 `answer_text`、`answer_text_preview`、scores、feedback 和 `weakness_tags`。
3. `POST /api/interviews/questions/generate` 使用 deterministic rules 读取 JD profile、structured resume、可选 project facts、project rewrite JSON 和 v1.2 12D 可选 `rag_answer_run_ids`，生成并持久化 questions。
4. `GET /api/interviews/questions` 支持按 `jd_id`、`resume_version_id`、`project_id`、`question_type` 和 `difficulty` 筛选。
5. 每个 question 包含 `expected_points` 和 `source_refs`；`source_refs` 只保存 source type/id/field/label/preview，不保存 Resume/JD full raw_text、RAG full chunk text 或完整 answer。只有 grounded RAG answer runs 会补充 source_refs；ungrounded runs 只返回 warning。
6. `POST /api/interviews/answers` 保存回答，默认 response 只返回 `answer_text_preview`。
7. `GET /api/interviews/answers` 支持按 `question_id`、`jd_id`、`resume_version_id` 和 `project_id` 查询回答。
8. `POST /api/interviews/answers/{answer_id}/score` 使用 deterministic rules 生成 `structure`、`technical_depth`、`business_understanding`、`evidence`、`clarity`、`risk_control`、`overall_average`、feedback 和 `weakness_tags`。
9. InterviewCenterPage 通过 `frontend/src/api/interviews.ts` 调用真实后端 API，支持生成 questions、筛选和选择 question、提交 answer、查看 answer preview、刷新 answer list，并对 selected answer 运行 deterministic scoring。
10. `GET /api/interviews/stats` 基于 `interview_questions` / `interview_answers` 返回 Dashboard training stats：question count、answer count、scored answer count、latest average score、latest weakness tags、by question type 和 by difficulty。
11. Dashboard 展示独立 Interview Training stats，不复用 Application Tracking 的 interview status。

当前 Interview 10A/10B/10C/10D 不接真实 LLM，不接 embedding/vector DB，不自动写入 Study Plan，不自动修改 Resume Version。v1.2 12D 只允许可选引用 grounded RAG answer runs 作为 preview-first 来源补充，不做自动写入或深度 RAG workflow。Scoring 是规则版，不是 LLM judge；默认 API response、InterviewCenterPage 列表和 Dashboard stats 不返回完整 `answer_text`、Resume raw_text 或 JD raw_text。

### Study Plan Center v1.1 11A/11B/11C/11D

Study Plan 11A/11B/11C/11D 当前链路：

1. `study_plans` 表保存生成的学习计划，支持可选关联 `match_report_id`、`profile_id` 和 `project_rewrite_id`。
2. `POST /api/study-plans/generate` 使用 deterministic rules 读取 Profile、MatchReport、ProjectRewrite、InterviewAnswer weakness tags、v1.2 12D 可选 `rag_answer_run_ids` 和 request weakness tags。
3. `target_role` 可由 request 直接提供；未提供时可从 profile `target_roles` 推断；仍无法确定时报 `study_plan_target_role_required`。
4. `phases` JSON 保存 phase/task 结构；每个 task 有稳定 `task_id`、source_gap、priority、status、acceptance_criteria、evidence_required 和 source_refs。
5. `resources` 在没有真实 RAG resource 时使用 `manual_resource_needed` placeholder，不编造课程链接。
6. `source_refs` 只保存 source type/id/field/label/preview，不保存 Resume/JD full raw_text、完整 `answer_text` 或 RAG full chunk text；grounded RAG answer runs 可生成学习/证据复核任务，ungrounded runs 只记录 uncertainty ref，不作为强来源。
7. `GET /api/study-plans` 和 `GET /api/study-plans/{study_plan_id}` 提供 backend list/detail。
8. `PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}` 更新 `phases[*].tasks[*].status` 并刷新 `updated_at`，不自动修改 plan status。
9. `GET /api/study-plans/stats` 基于 `study_plans.phases` 聚合 plan count 和 task status count，不返回 source_refs 细节或隐私原文。
10. StudyPlanPage 通过 `frontend/src/api/studyPlans.ts` 调用真实后端 API，支持 generate、list/filter、detail、phase/task 展示、source_refs preview 展示和 task status update。
11. Dashboard 通过 `getStudyPlanStats` 读取 stats，展示 Study Plans、Active Study Plans、Pending Tasks、Blocked Tasks、Done Tasks、Latest Study Target 和 In Progress Tasks；stats API 失败时 Dashboard 使用 0 / empty state，不影响其他模块数据。

Study Plan 模块自身仍不接真实 LLM，不接 embedding/vector DB，不接外部学习平台或日历提醒，不自动修改简历、项目、面试答案或投递状态。v1.2 12D 支持 optional grounded RAG answer run refs；v1.3 Agent Workflow 可以调用 Study Plan generation，但不会自动写回简历、项目、面试答案或投递状态。

### Agent Workflow v1.3

Agent Workflow 当前链路：

1. `POST /api/agents/runs` 创建 `job_application_preparation` run。
2. `validate_inputs` 校验 resume / resume version、JD、可选 project refs、可选 application ref、RAG query 和 RAG answer run refs。
3. `load_resume_version` 和 `load_job_profile` 读取已有 DB-backed refs。
4. `run_match_report` 调用已有 Match service，生成并保存 match report。
5. `rag_search` 仅在 `use_rag=true` 时执行 legacy deterministic lexical search；未启用时 step 标记 skipped。
6. `summarize_rag_context` 汇总 `rag_search` refs、source counts、usable refs 和 warnings，不读取或保存 document raw text / full chunk text。
7. `run_project_rewrites` 使用传入 `project_ids`，或按 `resume_version_id` 自动发现 active projects；没有项目时 skipped。
8. `generate_interview_questions` 调用 Interview Center，最多生成 6 个 deterministic questions，可携带 grounded RAG answer run refs。
9. `generate_study_plan` 调用 Study Plan Center，基于 match report、首个 project rewrite 和可选 grounded RAG answer run refs 生成 plan。
10. `create_or_link_application` 创建 draft application，或绑定已有 application；如果 `create_application=false` 且未传 `application_id`，则跳过。
11. `build_final_summary` 汇总 `match_report_id`、`project_rewrite_ids`、`interview_question_ids`、`study_plan_id`、`application_id`、summarized RAG context 和 deterministic next actions。

`applications.agent_run_id` 将投递 tracking record 与 workflow run 连接。Application 仍由用户手动维护状态，workflow 不自动投递、不接招聘网站、不自动提交材料、不自动状态流转。

AgentRunsPage 支持输入 project IDs、existing application ID、create application 开关、RAG query 和 RAG Answer Run IDs，展示 run detail、step timeline 和 final summary。ApplicationTrackerPage 支持查看和筛选 `agent_run_id`。Dashboard 展示 latest agent run score/status 和 linked application 摘要。

### Application Operations v1.4

Application Management 当前处于 v1.4 Product Operations Hardening：

1. `applications` 保存手动投递 tracking record，service 层要求每条记录绑定有效 `jd_id` 和 `resume_version_id`。
2. `match_report_id` 和 `agent_run_id` 是可选 linkage；传入时会校验对象存在和归属关系。
3. 运营字段包括 company、role title/category、status、apply date、next step date、source URL、location、priority、notes、interview notes、reflection、interview question IDs、last contact date 和 tags。
4. `application_status_history` 保存状态流转：create 写初始 status，status patch 且状态变化时写 history，非状态字段更新不重复写入。
5. `POST /api/applications/{application_id}/reflection` 只维护投递复盘摘要、面试反馈、失败原因、准备缺口、下一步行动和 weakness tags；不自动写 Bad Case，也不自动生成 Study Plan。
6. ApplicationTrackerPage 支持 Application Board、filters、detail edit、status history 和 reflection。Dashboard 展示 total、active、interview、offer、rejected、upcoming、overdue、conversion 和 latest application。

Application 仍是手动运营记录，不自动投递、不接招聘网站、不保存完整投递材料、不自动状态流转。RAG v1.2 contract 和 Agent v1.3 workflow 不因 v1.4 回退。

### Quality / Evaluation v1.5B

v1.5B 当前链路：

1. Bad Case 保存人工问题摘要、root cause、fix strategy、tags、lifecycle status 和 source refs。
2. `POST /api/bad-cases/{bad_case_id}/add-to-eval` 将 Bad Case 幂等加入默认 `regression` dataset，生成 `source_type=bad_case` 的 evaluation case。
3. Evaluation runner 支持 `jd_parser`、`resume_parser`、`match`、`rag`、`agent`、`application`、`bad_case` 七个 deterministic modules。
4. `synthetic_smoke_v1` 覆盖全部模块；`evals/datasets/smoke` 和 `evals/expected/smoke` 提供文件化 smoke fixtures。
5. `scripts/run_evals.py` 可在本地生成 ignored `evals/results` 下的 summary、metrics 和 failed cases。
6. Linked regression case pass 会将 Bad Case 标记为 `verified` 并写入 run/case refs；fail 不会编造验证结果。
7. QualityReviewPage 展示 bad case stats 和 regression linkage；EvaluationPage 展示 dataset registry、run_config、failed cases 和 result detail。

该链路仍不接真实 LLM、不做 LLM judge、不接 embedding/vector DB、不自动投递、不自动修改 Resume/Project/Application，也不保存 raw_text 或 full chunk text。

### Privacy / Security / Governance v1.5C

v1.5C 在不新增真实 LLM、embedding/vector DB、自动投递或生产级权限系统的前提下，补齐本地 prototype 的治理基线：

1. `app.core.privacy` 提供 `safe_preview`、`redact_text`、`redact_mapping`，用于 mask email、phone、API key/token/secret，并避免日志输出大段 raw text。
2. `app.core.versioning` 集中维护 prompt/schema/retrieval/model/evaluation 版本常量。
3. RAG retrieval debug、Agent final summary、Evaluation run_config 和 fileized eval metrics 记录版本 metadata。
4. Resume/JD/Application/RAG document 新增 delete/archive API；默认列表不展示 deleted/archived 记录。
5. Resume/JD/RAG response preview 收敛为短 preview；前端页面提供确认式删除/归档入口和隐私提示。

这些能力仍不等于生产级合规删除、备份擦除或完整审计日志系统。P1 已补认证和基础 workspace data isolation，但仍不是完整生产级 RBAC/SSO/SIEM/retention 体系。

### Production AI / Deployment Readiness v1.6

v1.6 在不改变默认 deterministic 行为的前提下，补齐生产化 AI 接入和部署准备的边界：

1. `backend/app/ai/llm_provider.py` 定义 deterministic provider 和 OpenAI-compatible HTTP provider skeleton；外部 provider 只有显式启用并配置 key/model/base URL 时才可用。
2. `backend/app/ai/embedding_provider.py` 提供 local bag-of-words embedding、embedding id 生成和 OpenAI-compatible embedding skeleton；默认不调用外部 embedding API。
3. `backend/app/ai/validators.py` 使用 Pydantic schema 校验结构化 AI 输出，避免无约束自然语言直接进入业务对象。
4. `/health` 暴露 `ai_provider_mode`、`llm_provider`、`embedding_provider`、`vector_store`、`rag_retrieval_mode` 和 real provider enable flags，但不返回 API key 或 secret。
5. RAG search / answer 支持 `retrieval_mode=lexical|vector|hybrid` alias 和 `score_threshold`；当前 vector/hybrid 使用 DB-persisted local vectors，不依赖 FAISS、pgvector 或外部 vector store。
6. `docker-compose.yml` 和 `.env.example` 提供 provider/vector 配置 placeholder；默认 compose 仍可 keyless deterministic 启动。
7. 新增 `docs/ai-providers.md`、`docs/deployment.md` 和 `docs/release-notes-v1.6.md`，明确 provider opt-in、部署检查、安全边界和未完成项。

v1.6 不是完整生产 AI 平台：未接真实招聘网站、未自动投递、未启用自由 Agent、未强制 PostgreSQL/pgvector、未完成云 secret manager、集中审计或生产监控；认证和基础 workspace isolation 已在后续 P1 checkpoint 补齐。

### P1 Production Foundation: Auth / Workspace / Data Isolation

P1 在不新增真实 LLM/RAG/Agent/投递业务能力的前提下补齐生产化基础：

1. Auth：`/api/auth/register` 创建 user、default workspace 和 membership；`/api/auth/login` 返回 bearer token；`/api/auth/me` 返回当前 user/workspace；`/api/auth/logout` 为 stateless success。
2. Route protection：除 health、register、login 外，工作台 API 默认要求 `Authorization: Bearer <token>`；无 token、无效 token、过期 token 或 inactive user 返回 401。
3. Workspace scope：token payload 带 `workspace_id`，`app.core.tenant` 用 request-scoped context 暴露当前 user/workspace；repository/service 对 owned data 使用 `user_id` / `workspace_id` 过滤。
4. Schema：新增 `users`、`workspaces`、`workspace_memberships`、`audit_logs`；核心业务表新增 `workspace_id`，此前缺少 owner 的 result/evaluation tables 补 `user_id` 和 `workspace_id`。
5. Privacy：新增 `/api/privacy/export`、`DELETE /api/privacy/delete-all`、`/api/privacy/audit-log`，只作用于当前 user/workspace。delete-all 写入 audit log，并返回删除计数，不输出 raw private payload。
6. Frontend：未登录时展示 auth 页面；登录后进入工作台；401 会清理本地 token 并回到登录态。

P1 是 foundation checkpoint，不声明完整 production-ready：仍缺生产级 RBAC/SSO、refresh token/rotation、MFA、centralized audit/SIEM、backup erasure proof、retention policy、managed PostgreSQL rollout、cloud secret manager 和 production observability。

### Dashboard readiness

Dashboard 当前展示：

- latest profile readiness level 和 completeness score。
- latest resume parse status 和 risk flags count。
- project count、active project count、latest project name/status。
- interview training question count、answer count、scored answer count、latest average score 和 latest weakness tags。
- study plan count、active plan count、pending / blocked / done / in progress task count 和 latest study target。
- RAG document count、indexed document count、chunk count、grounded/ungrounded answer count、latest answer preview 和 latest uncertainty。
- Agent run count、latest agent run status/score 和 linked application 摘要。
- Application total、active、interview、offer、rejected、upcoming、overdue、conversion 和 latest application。
- 原有 Resume、JD、Match、Bad Case、Evaluation 统计。

## 7. 阶段完成状态

| 阶段 | 当前状态 |
| --- | --- |
| 阶段一 | Resume / JD / Match 最小闭环已完成 |
| 阶段二 | SQLite + SQLAlchemy + Alembic 持久化与 Resume Version 已完成 |
| 阶段三 / 2.2 | RAG lexical prototype 已完成；v1.2 RAG Completion deterministic MVP 已完成；2.2 补充 local vector embedding persistence 和 lexical/vector/hybrid retrieval foundation |
| 阶段四 | Agent deterministic workflow prototype 已完成 |
| 阶段五 | Application Tracking + Dashboard MVP 已完成 |
| 阶段六 | Deterministic Evaluation MVP + Bad Case 关联已完成 |
| v0.8 Resume/Profile Foundation | Resume parser / risk-check APIs + Profile Center MVP 已完成 |
| v0.9 Project Optimization 9A / 9B / 9C / 9D / 9E | Project facts backend、deterministic rewrite backend、ProjectOptimizationPage、Dashboard/docs/tests 收口和 final handoff 已完成 |
| v1.0 Interview Center 10A/10B/10C/10D | Backend interview tables、deterministic question generation、question list、answer submit/list、answer scoring API、InterviewCenterPage、stats API 和 Dashboard training stats 已完成；Study Plan 写入、RAG completion 与 LLM judge 未实现 |
| v1.1 Study Plan Center 11A/11B/11C/11D | Backend `study_plans` table、deterministic generate API、list/detail、task status update、stats API、StudyPlanPage 和 Dashboard study stats 已完成；v1.1 阶段未做 RAG refs、外部学习平台和日历提醒，v1.2 12D 已补 optional grounded RAG answer run refs，v1.3 Agent Workflow 可调用 generation |
| v1.2 RAG Completion 12A | RAG grounded answer contract tightening 已完成，标准化 citations/source_refs/retrieval_debug/evidence_summary；仍为 deterministic lexical retrieval，不接真实 LLM、embedding/vector DB |
| v1.2 RAG Completion 12B | 新增 `rag_answer_runs` 持久化、answer run list/detail API 和更强 retrieval/privacy tests；answer runs 只保存 grounded contract、短 snippet/preview 和 safe debug，不保存 raw_text/full chunk text |
| v1.2 RAG Completion 12C | KnowledgeBasePage 接入 answer history list/detail、grounded/uncertainty/retrieval_mode filters、citations/source_refs/retrieval_debug 展示；仍不展示 raw_text/full chunk text，不做 RAG evaluation dashboard |
| v1.2 RAG Completion 12D | 新增 `GET /api/rag/stats`、Dashboard RAG stats，并为 Interview / Study Plan generation 增加可选 `rag_answer_run_ids`；仅 grounded answer runs 作为 preview-first refs 补充，ungrounded runs 不作为强来源 |
| v1.2 RAG Completion 12E | 新增 release notes，并完成 README、architecture、API reference、database schema、demo script 和 final acceptance report 最终口径收口；不创建 tag |
| v1.3 Agent Workflow Baseline + Application Linkage | `job_application_preparation` 扩展为 11 步 deterministic workflow，串联 Match、RAG context summary、Project Rewrite、Interview、Study Plan 和 Application draft/linkage；AgentRunsPage、ApplicationTrackerPage、Dashboard 和 docs 已接入 `agent_run_id` 与 `final_summary` |
| v1.4 Product Operations / Application Management Hardening | Application tracking 已补强 JD/Resume 强绑定、status history、reflection、Application Board、enhanced stats 和 Dashboard operations overview；不自动投递、不接招聘网站、不接真实 LLM |
| v1.5B Bad Case + Evaluation Regression Foundation | Bad Case lifecycle / regression linkage、7 模块 deterministic evaluation、fileized smoke fixtures、run_evals script、QualityReviewPage / EvaluationPage 增强已完成；不接真实 LLM judge 或多模型评测 |
| v1.5C Privacy / Security / Data Governance | Redaction utilities、delete/archive APIs、short safe previews、version metadata tracking、frontend governance controls 和 privacy regression tests 已完成；不声明生产级合规删除或多用户安全 |
| v1.6 + 2.2 Production AI / RAG Foundation | Provider abstraction、deterministic LLM fallback、OpenAI-compatible skeleton、structured output validation、local vector embedding persistence、lexical/vector/hybrid retrieval、health/config visibility、Docker/env placeholders 和部署文档已完成；默认不调用真实外部 provider |
| P1 Production Foundation | Token auth、workspace membership、route protection、owned data isolation、privacy export/delete/audit baseline、frontend auth gate 和 PostgreSQL driver readiness 已完成；不声明完整 production-ready |
| 阶段七 | 当前补齐 Docker、README、docs、demo script、安全清单和 provider/deployment readiness |

## 8. 当前不做

- 默认不调用真实 LLM 或外部 embedding provider；真实 provider 需要显式 opt-in 配置。
- 不做自动投递。
- 不接招聘网站。
- 不接真实 LLM judge。
- 不做多模型评测平台。
- 不声明完整生产级多租户权限体系；P1 只完成基础 token auth、workspace scope 和 owner filtering。
- 不强制切 PostgreSQL / pgvector；当前 vector/hybrid retrieval 是本地 deterministic baseline。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。
