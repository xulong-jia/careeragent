# CareerAgent 当前架构说明

本文档描述当前仓库真实实现状态。历史阶段文档保留当时阶段边界；如果历史文档写“暂不做某模块”，以本文档和 README 的当前状态为准。

## 1. 当前定位

CareerAgent 是面向校招和留学生回国求职场景的 AI 求职工作台原型。它不是自动投递工具，不接招聘网站，不做真实 LLM Agent，也不把 evaluation 结果当作模型能力最终评分。

当前系统是本地 SQLite-backed deterministic prototype：

- 后端：FastAPI + Pydantic + SQLAlchemy + Alembic + SQLite。
- 前端：React + TypeScript + Vite。
- 数据：默认本地 SQLite，`local_data/` 不进入 Git。
- AI 边界：当前 Resume/JD/Match/Project/RAG/Agent/Evaluation 均为 deterministic 规则或状态机，不调用真实 LLM。

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

FastAPI app 在 `backend/app/main.py` 注册 Health、DB、Profile、Project、Project Rewrite、Interview、Study Plan、Resume、Resume Version、JD、Match、RAG、Agent、Application 和 Evaluation routers。

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

前端 API 封装在 `frontend/src/api/`，通过 `requestJson` 统一解析后端响应。

## 5. 数据库和持久化

当前使用 SQLite + Alembic。核心表包括：

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

当前不接真实 OpenAI、DeepSeek、Qwen 或其他 LLM provider。

- Profile：manual CRUD + readiness summary，不自动从简历生成画像。
- Project：manual project facts CRUD + deterministic rewrite backend + ProjectOptimizationPage，可选绑定 profile / resume version，不自动生成项目事实，不接真实 LLM。
- Interview：v1.0 10A/10B/10C/10D 提供 deterministic question generation / list、answer submit / list、scoring API、stats API、InterviewCenterPage 和 Dashboard training stats，基于 JD profile、structured resume、可选 project facts、project rewrite refs、可选 grounded RAG answer run refs、question expected_points/source_refs 和本地 DB answer，不做 LLM judge。
- Study Plan：v1.1 11A/11B/11C/11D 提供 `study_plans` 表、`POST /api/study-plans/generate`、list/detail、task status update、stats API、frontend API wrapper、StudyPlanPage 和 Dashboard study stats，基于 Profile target_roles / skill_map、Match gaps / rewrite_priorities、Project Rewrite missing_points / evidence_required、Interview weakness_tags、可选 grounded RAG answer run refs 和 request weakness_tags 生成 deterministic phases/tasks/resources/deliverables/acceptance criteria；v1.3 Agent Workflow 可调用 generation，但不做真实 LLM、外部学习平台、日历提醒或自动修改简历/项目/面试答案。
- Resume：PDF / DOCX / Markdown / txt 文本提取 + deterministic parser / risk-check，不调用真实 LLM。
- JD：deterministic skill extraction / role category inference。
- Match：deterministic scoring。
- RAG：deterministic chunking + lexical retrieval + deterministic grounded answer。v1.2 RAG Completion deterministic MVP 已完成，覆盖 contract tightening、grounded answer persistence、KnowledgeBasePage answer history UI、Dashboard RAG stats 和 optional downstream refs，answer response 在保留 `sources` 的同时补齐 `citations`、`source_refs`、`evidence_summary`、safe `retrieval_debug` 和可选 `answer_run_id`；默认不接真实 LLM、embedding 或 vector DB。
- Agent：v1.3 deterministic workflow baseline，固定 `job_application_preparation` state machine 串联 Resume Version、JD、Match、可选 RAG search、RAG context summary、Project Rewrite、Interview Questions、Study Plan 和 Application linkage；不是自由工具调用 Agent，不自动投递。
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
| 阶段三 | RAG lexical prototype 已完成；v1.2 RAG Completion deterministic MVP 已完成 |
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
| 阶段七 | 当前补齐 Docker、README、docs、demo script 和安全清单 |

## 8. 当前不做

- 不做自动投递。
- 不接招聘网站。
- 不接真实 LLM judge。
- 不做多模型评测平台。
- 不做生产级多用户权限。
- 不切 PostgreSQL / pgvector。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。
