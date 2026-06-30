# CareerAgent Final Acceptance Report

本报告记录 v1.5B Bad Case + Evaluation Regression Foundation 后的当前项目状态。结论基于当前仓库真实代码、测试和文档，不代表生产就绪系统，也不表示任何 v1.5 tag 已完成。

## 1. 验收结论

v1.1.0 `study-plan-center` 已完成 deterministic Study Plan Center MVP；v1.2.0 RAG Completion deterministic MVP 已完成 12A/12B/12C/12D/12E 的 contract tightening、answer run persistence、answer history UI、Dashboard RAG stats、optional downstream refs 和 final handoff 文档；v1.3.0 Agent Workflow Baseline + Application Linkage 已完成 deterministic end-to-end workflow orchestration、Application `agent_run_id` linkage、frontend display 和 docs/tests 收口；v1.4 Product Operations / Application Management Hardening 已完成 JD/Resume 强绑定、status history、reflection、Application Board 和 enhanced stats；v1.5B 已完成 Bad Case lifecycle / regression linkage、7 模块 deterministic evaluation、fileized smoke fixtures 和 frontend review/evaluation visibility。v1.0.0 `interview-center` 仍作为已完成的稳定里程碑保留在本报告中。

已完成范围：

- 10A Interview questions backend：新增 `interview_questions` / `interview_answers` 表、question generation schema / repository / service / API，支持 deterministic question generation 和 question list。
- 10B Interview answers backend：新增 answer submit / list / score API，保存本地 `answer_text`，默认 response 只返回 `answer_text_preview`，输出 deterministic scores、feedback 和 `weakness_tags`。
- 10C InterviewCenterPage：前端接入 question generation/list、answer submit/list 和 score workflow，展示 scores、feedback 和 `weakness_tags`。
- 10D Dashboard / docs / tests 收口：新增 `GET /api/interviews/stats`，Dashboard 展示独立 Interview Training stats，新增 stats API 测试。
- 10E final handoff：补齐 v1.0 final acceptance、release notes、安全边界和后续不做范围。
- 11A Study Plan backend：新增 `study_plans` 表、deterministic generate service 和 `POST /api/study-plans/generate`。
- 11B task status / stats：新增 list/detail、task status update 和 stats API。
- 11C StudyPlanPage：新增前端 API wrapper、TypeScript types、StudyPlanPage、导航和路由。
- 11D Dashboard study stats：Dashboard 接入 `GET /api/study-plans/stats`。
- 11E final handoff：补齐 v1.1 release notes、最终验收口径和文档一致性。
- 12A RAG contract tightening：补齐 grounded answer contract，返回 evidence summary、citations、source_refs 和 safe retrieval_debug。
- 12B RAG answer persistence：新增 `rag_answer_runs`，`POST /api/rag/answer` 默认保存 answer run，并新增 answer run list/detail API。
- 12C KnowledgeBasePage answer history：前端支持 answer run filters、list/detail、citations/source_refs preview 和 retrieval_debug 展示。
- 12D Dashboard RAG stats + optional refs：新增 `GET /api/rag/stats`，Dashboard 展示 RAG stats，Interview / Study Plan generation 支持可选 grounded RAG answer run refs。
- 12E final handoff：新增 `docs/release-notes-v1.2.md`，并完成 README、architecture、API reference、database schema、demo script 和 final acceptance report 最终口径收口。
- v1.3 Agent Workflow baseline：`job_application_preparation` 扩展为 11 步 deterministic workflow，串联 Match、RAG context summary、Project Rewrite、Interview Questions、Study Plan 和 Application create/link。
- v1.3 Application linkage：新增 `applications.agent_run_id`、migration、schema/repository/service/API 支持和 refs 校验。
- v1.3 frontend/docs/tests：AgentRunsPage 展示 final summary，ApplicationTrackerPage 支持 `agent_run_id` 创建/筛选/展示，Dashboard 展示 latest agent run score/status 和 linked application 摘要，新增 release notes 和文档收口。
- v1.4 Application operations：新增运营字段、`application_status_history`、reflection endpoint、status-history endpoint、enhanced stats 和 frontend Application Board / detail edit / reflection / Dashboard operations overview。
- v1.5B Quality/Evaluation regression：扩展 `bad_cases` lifecycle 字段，新增 direct `/api/bad-cases` stats/add-to-eval，扩展 7 模块 deterministic evaluation、datasets endpoint、failed_case_ids、run_config version metadata、regression pass/fail linkage、fileized smoke fixtures 和 `scripts/run_evals.py`。

## 2. 当前模块状态

| 模块 | 当前状态 |
| --- | --- |
| Resume Center | 已完成 v0.8 foundation MVP：文本层提取、deterministic parser、risk-check、confirmed version 保存和前端 workflow |
| Profile Center | 已完成 v0.8 MVP：profiles 表、Profile API、ProfilePage、summary/completeness 和 Dashboard readiness |
| Project Optimization | 已完成 v0.9 deterministic MVP：projects / project_rewrites、Project CRUD、rewrite API、ProjectOptimizationPage 和 Dashboard project summary |
| Interview Center | 已完成 v1.0 10A/10B/10C/10D：question generation、answer submit/list、deterministic scoring、InterviewCenterPage 和 Dashboard training stats |
| Study Plan Center | 已完成 v1.1 11A/11B/11C/11D：study plan generation、list/detail、task status update、stats API、StudyPlanPage 和 Dashboard study stats |
| JD Center | 已完成 deterministic MVP |
| Match Report | 已完成 deterministic MVP |
| RAG Knowledge Base | v1.2 12A/12B/12C/12D/12E 已完成 contract tightening、answer run persistence、answer history UI、Dashboard RAG stats、optional downstream refs 和 final handoff |
| Agent Runs | v1.3 已完成 deterministic workflow baseline：11 步 `job_application_preparation`、step timeline、final summary、Project/Interview/Study/Application orchestration |
| Application Tracking | v1.4 已完成 Product Operations hardening：JD/Resume 强绑定、status history、reflection、board、enhanced stats 和 `agent_run_id` linkage |
| Quality Review / Bad Case | v1.5B 已完成 lifecycle / root cause / fix strategy / tags / regression eval linkage |
| Evaluation | v1.5B 已完成 7 模块 deterministic smoke + regression foundation、dataset registry、failed cases 和 fileized runner |
| Docker / Compose | 已完成本地开发配置；build 需在 Docker daemon 可用环境验证 |
| Docs / Demo | 已完成 v1.3 release notes、handoff 文档、demo script 和 final acceptance 口径；未声明 tag 已创建 |

## 3. v0.9 Project Optimization 能力

Project Facts：

- `projects` 表保存用户手动确认的项目事实。
- Project API 支持 create / list / detail / patch。
- `profile_id` / `resume_version_id` 是可选关联；传入时后端会校验对象存在。
- `status` 支持 `active` / `archived`，列表支持状态筛选。
- 已有 Project API 和 DB infrastructure 测试。

Project Rewrite：

- `project_rewrites` 表保存 rewrite 结果。
- `POST /api/projects/{project_id}/rewrite` 针对 JD profile 运行 deterministic rewrite。
- `GET /api/project-rewrites/{rewrite_id}` 查询持久化 rewrite 结果。
- 输出包含 `matched_points`、`missing_points`、`evidence_required`、`rewritten_bullets`、`forbidden_changes`、`risk_flags` 和 `rewrite_strategy`。
- 已有 Project Rewrite API、规则和 DB infrastructure 测试。

Frontend / Dashboard：

- ProjectOptimizationPage 支持 project list、create / update project facts、project detail、rewrite form 和 rewrite result display。
- 前端展示 matched / missing / evidence required / rewritten bullets / forbidden changes / risk flags。
- Dashboard 展示 project count、active project count、latest project name/status，并保留 Profile/Resume/Application/Evaluation 等现有统计。

## 4. v1.0 Interview Center 当前状态

Interview Center 当前已完成 10A / 10B / 10C / 10D / 10E：

- 10A：新增 `interview_questions` 表、deterministic question generation 和 question list API。
- 10B：新增 `interview_answers` 表、answer submit / list / score API、deterministic scoring、feedback 和 `weakness_tags`。
- 10C：新增 InterviewCenterPage，前端接入 question generation/list、answer submit/list 和 score workflow。
- 10D：新增 `GET /api/interviews/stats`，Dashboard 展示独立 Interview Training stats，不复用 Application Tracking 的 interview status。
- 10E：补齐 v1.0 final acceptance、release notes、demo flow、安全与隐私边界和最终检查结果。

10D stats 字段：

- `total_questions`
- `total_answers`
- `scored_answers`
- `latest_average_score`
- `latest_weakness_tags`
- `by_question_type`
- `by_difficulty`

10D 新增测试：

- `backend/tests/test_interview_stats_api.py`
- 覆盖 empty stats、生成题目后的 stats、提交答案后的 stats、评分后的 latest average score / weakness tags，以及不返回 `answer_text`、Resume raw_text 或 JD raw_text。

10E 检查结果（2026-06-25）：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：216 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `docker compose config`：通过。
- `python3 -m py_compile scripts/seed_demo_data.py`：通过。
- `git diff --check`：通过。
- `docker compose build`：未验证，当前环境 Docker daemon/socket 不可用；`docker compose config` 已通过。

Interview Center 模块自身仍不做 Study Plan 自动写入、不接真实 LLM / LLM judge、不接 embedding/vector DB，也不展示 Resume/JD full raw_text 或完整已保存 `answer_text`。v1.2 12D 只支持可选 grounded RAG answer run refs；v1.3 Agent Workflow 可以调用 question generation，但不自动提交答案或修改面试记录。

## 5. v1.1 Study Plan Center 当前状态

Study Plan Center 当前已完成 11A / 11B / 11C / 11D：

- 11A：新增 `study_plans` 表、model/schema/repository/service/API 和 `POST /api/study-plans/generate`，支持 deterministic study plan generation。
- 11B：新增 `GET /api/study-plans`、`GET /api/study-plans/{study_plan_id}`、`PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}` 和 `GET /api/study-plans/stats`。
- 11C：新增 `frontend/src/api/studyPlans.ts`、Study Plan TypeScript types、StudyPlanPage、导航和路由，前端接入 generate/list/filter/detail/task status update API。
- 11D：Dashboard 接入 `GET /api/study-plans/stats`，展示 Study Plans、Active Study Plans、Pending Tasks、Blocked Tasks、Done Tasks、Latest Study Target 和 In Progress Tasks。
- 11E：新增 `docs/release-notes-v1.1.md`，并完成 README、architecture、API reference、database schema、demo script 和 final acceptance report 最终口径收口。

11D stats 字段：

- `total_plans`
- `active_plans`
- `completed_plans`
- `archived_plans`
- `pending_tasks`
- `blocked_tasks`
- `done_tasks`
- `in_progress_tasks`
- `skipped_tasks`
- `latest_plan_id`
- `latest_target_role`

11D 检查结果（2026-06-25）：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：237 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `docker compose config`：通过。
- `python3 -m py_compile scripts/seed_demo_data.py`：通过。
- `git diff --check`：通过。
- `docker compose build`：未验证，当前环境 Docker daemon/socket 不可用；`docker compose config` 已通过。

Study Plan Center 模块自身仍不接真实 LLM，不接外部学习平台或日历提醒，不自动修改简历、项目、面试答案或投递状态。v1.2 12D 只允许可选 grounded RAG answer run refs 作为学习/证据复核来源；v1.3 Agent Workflow 可以调用 study plan generation，但不自动更新 task status。`source_refs` 只保存 preview 和引用 ID；Dashboard study stats 只展示聚合计数和 latest target，不返回 source_refs 细节、Resume/JD raw_text 或完整 `answer_text`。

## 6. v1.2 RAG Completion Final Handoff

RAG Completion 当前已完成 12A / 12B / 12C / 12D / 12E：

- 12A：RAG answer contract 收紧，保留旧 `sources` 字段，同时新增 `evidence_summary`、`citations`、`source_refs` 和 `retrieval_debug`；grounded 命中返回 `grounded=true` / `uncertainty=grounded`，无来源返回 `no_relevant_source`，低证据返回 `insufficient_evidence`。
- 12B：新增 `rag_answer_runs` 表和 migration；`POST /api/rag/answer` 支持 `persist`，默认保存 answer run contract，并新增 `GET /api/rag/answers` / `GET /api/rag/answers/{answer_run_id}`。
- 12C：KnowledgeBasePage 新增 Answer History、grounded / uncertainty / retrieval mode filters、answer run detail、citations、source_refs preview 和折叠 retrieval_debug。
- 12D：新增 `GET /api/rag/stats`，Dashboard 展示 RAG Documents、Indexed Documents、RAG Chunks、Grounded Answers、Ungrounded Answers、Latest RAG Answer 和 Latest RAG Uncertainty；StudyPlanPage / InterviewCenterPage 支持可选 RAG Answer Run IDs。
- 12E：新增 `docs/release-notes-v1.2.md`，并完成 README、current architecture、API reference、database schema、demo script 和 final acceptance report 最终一致性检查。

12D stats 字段：

- `total_documents`
- `indexed_documents`
- `total_chunks`
- `total_answer_runs`
- `grounded_answer_runs`
- `ungrounded_answer_runs`
- `latest_answer_run_id`
- `latest_answer_question_preview`
- `latest_answer_uncertainty`
- `latest_answer_created_at`

12D 新增/更新测试：

- `backend/tests/test_rag_stats_api.py`
- 更新 `backend/tests/test_study_plan_generate_api.py`，覆盖 grounded / ungrounded / missing RAG answer run refs。
- 更新 `backend/tests/test_interview_questions_api.py`，覆盖 grounded RAG refs、ungrounded warning 和 missing RAG answer run error。

12E 文档收口：

- README 标记 v1.2 RAG Completion deterministic MVP 已完成，并加入 v1.2 release notes 链接。
- current architecture 明确 v1.2 RAG Completion 已完成，真实 LLM/vector DB/RAG evaluation dashboard 未完成。
- API reference 确认 RAG APIs 完整，chunk list 使用真实 `GET /api/rag/chunks` 路由。
- database schema 确认 `rag_answer_runs` 和 `citations_json` / `source_refs_json` / `retrieval_debug_json` 隐私边界。
- demo script 确认可演示 create/index document、search、grounded answer、answer history、Dashboard RAG stats、Interview / Study Plan optional RAG Answer Run IDs。
- release notes 记录能力、API、数据模型、前端、安全边界、测试结果和已知未完成项。

RAG Completion deterministic MVP 已达到 final handoff 状态；该模块仍不接真实 LLM、embedding/vector DB、reranker、外部 vector store 或 RAG evaluation dashboard；optional refs 不自动写入 Interview、Study Plan、Resume、Project 或 Application。v1.3 已在独立 Agent Workflow baseline 中编排这些模块，但不改变 RAG 自身边界。

## 7. v1.3 Agent Workflow Baseline + Application Linkage

v1.3 当前已完成：

- `job_application_preparation` 扩展为 11 步 deterministic workflow：`validate_inputs`、`load_resume_version`、`load_job_profile`、`run_match_report`、`rag_search`、`summarize_rag_context`、`run_project_rewrites`、`generate_interview_questions`、`generate_study_plan`、`create_or_link_application`、`build_final_summary`。
- `POST /api/agents/runs` 支持 `project_ids`、`application_id`、`create_application` 和 `rag_answer_run_ids`。
- `final_summary` 从 `output_refs.final_summary` 暴露到 `AgentRunRecord.final_summary`，包含 total score、top strengths/gaps、next actions 和 created record refs。
- `run_project_rewrites` 使用显式 `project_ids`，或按 `resume_version_id` 自动发现 active projects；无项目时 step skipped。
- `generate_interview_questions` 调用现有 Interview Center service，最多生成 6 个 deterministic questions。
- `generate_study_plan` 调用现有 Study Plan Center service。
- `create_or_link_application` 创建 saved draft application，或绑定已有 application；`create_application=false` 时可跳过创建。
- `applications.agent_run_id` 已新增到 model、schema、repository、service、API、migration、tests 和 frontend types。
- Application API 支持按 `agent_run_id` 筛选。
- AgentRunsPage 支持 Project IDs、Existing Application ID、Create/link application toggle、RAG Answer Run IDs 和 final summary 展示。
- ApplicationTrackerPage 支持 `agent_run_id` 创建、展示和筛选。
- Dashboard 展示 latest agent run status/score、linked application summary 和 linked application count。
- 新增 `docs/release-notes-v1.3.md`，并更新 README、architecture、API reference、database schema、Agent Workflow design、Application Management design、demo script 和 final acceptance report。

v1.3 仍不接真实 LLM，不做自由聊天 Agent，不做 true tool-calling autonomy，不自动投递，不接招聘网站，不自动修改简历、项目、面试答案、学习计划任务状态或投递状态。

## 8. v1.4 Product Operations / Application Management Hardening

v1.4 当前已完成：

- Application create/update 要求最终绑定有效 `jd_id` 和 `resume_version_id`；`match_report_id` 和 `agent_run_id` 仍为可选 linkage。
- `applications` 新增 source URL、location、priority、notes、interview question IDs 和 last contact date 等运营字段。
- 新增 `application_status_history` 表和 endpoint；create 写初始状态，status patch 写流转历史，非状态字段 patch 不重复写 history。
- 新增 reflection endpoint，支持投递复盘摘要、面试反馈、失败原因、准备缺口、下一步行动和 weakness tags；不自动写 Bad Case 或 Study Plan。
- Application stats 返回 total/by_status/active/interview/offer/rejected/withdrawn、conversion、upcoming/overdue 和 latest applications。
- ApplicationTrackerPage 支持 Application Board、filters、detail edit、status history 和 reflection。
- Dashboard 展示 application total、active、interview、offer、rejected、upcoming、overdue、conversion 和 latest application。
- Agent workflow create/link application 回归保持可用，`final_summary.application_id` 仍可用于追踪。
- RAG v1.2 contract 未回退，Application 模块不读取 document raw_text 或 chunk full text。

v1.4 仍不接真实 LLM，不接 embedding/vector DB，不自动投递，不接招聘网站，不自动状态流转，不保存完整投递材料，也不把 reflection 自动写入 Bad Case / Study Plan。

## 9. v1.5B Bad Case + Evaluation Regression Foundation

v1.5B 当前已完成：

- Bad Case 新增 `root_cause`、`fix_strategy`、`tags`、`added_to_eval_set`、`verified_at`、`regression_evaluation_run_id` 和 `regression_evaluation_case_id`。
- Bad Case status 支持 `verified`。
- 新增 direct `/api/bad-cases` routes，包含 stats 和 `POST /api/bad-cases/{bad_case_id}/add-to-eval`。
- 保留 legacy `/api/evaluations/bad-cases` routes。
- Evaluation modules 扩展为 `jd_parser`、`resume_parser`、`match`、`rag`、`agent`、`application`、`bad_case`。
- `synthetic_smoke_v1` 覆盖全部 7 个模块。
- 新增 `GET /api/evaluations/datasets`。
- Evaluation metrics 新增 `failed_case_ids`，`run_config` 新增 prompt/schema/retrieval/model/code version metadata。
- linked regression case pass 会将 Bad Case 标记为 `verified`；fail 不会编造验证结果。
- 新增 `evals/datasets/smoke`、`evals/expected/smoke` 和 `scripts/run_evals.py`。
- QualityReviewPage 展示 Bad Case stats、lifecycle 字段和 Add to regression eval；EvaluationPage 展示 datasets、run_config、failed cases 和 result detail。

v1.5B 仍不接真实 LLM，不做 LLM judge，不接 embedding/vector DB，不做多模型对比，不自动投递，不接招聘网站，不自动修改 Resume/Project/Application，也不保存 raw_text 或 full chunk text。

## 10. 明确边界

当前 v1.5B 明确不做：

- 不接真实 LLM。
- 不自动写回 Resume Version。
- 不编造项目经历、数字、公司、技术栈、上线状态、业务规模、用户量、收益或准确率。
- 不把 Study Plan 自动写回简历、项目、面试答案或投递记录。
- 不重写 Match Scoring。
- 不接 embedding / vector DB。
- 不做真实 LLM RAG completion。
- 不接外部学习平台 API。
- 不做日历提醒。
- 不做自动投递。
- 不接招聘网站。
- 不做自由聊天 Agent 或 true tool-calling autonomy。
- 不自动修改简历、项目、面试答案、学习计划任务状态或投递状态。
- 不把 reflection 自动写入 Bad Case 或 Study Plan。
- 不做认证、多用户权限。
- 不把 deterministic evaluation 当作模型能力最终评分。

## 11. 测试与检查结果

2026-06-30 在当前工作树执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

结果：263 passed, 6 warnings。

```bash
cd frontend && npm run build
```

结果：通过，TypeScript 和 Vite production build 成功。

```bash
docker compose config
```

结果：通过，Compose 配置可解析。

```bash
PYTHONPATH=backend DATABASE_URL=sqlite:////tmp/careeragent_v15b_alembic_check.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

结果：通过，所有 Alembic migrations 可从空 SQLite DB 升级到 head。

```bash
backend/.venv/bin/python -m py_compile scripts/seed_demo_data.py scripts/run_evals.py
```

结果：通过。

```bash
backend/.venv/bin/python scripts/run_evals.py --dataset smoke
```

结果：通过，7 total / 7 passed / 0 failed，输出写入 ignored `evals/results/smoke`。

```bash
git diff --check
```

结果：通过。

```bash
docker compose build
```

结果：通过，backend / frontend images 均构建成功。

## 12. 安全与隐私

- `.env`、真实 API key、local DB、`local_data/`、uploads、vector index、exports、logs、cache、`dist/` 和 `node_modules/` 不进入 Git。
- Demo 和测试只使用 synthetic data。
- 不提交真实简历、真实 JD、投递记录、面试复盘、真实公司隐私或敏感商业数据。
- PDF / DOCX 解析只做文本层提取，不做 OCR。
- Resume `raw_text` 仍属于本地 prototype 数据；前端只展示 preview，后续生产化前需要继续收敛 raw_text 返回和日志策略。
- Profile 只保存目标岗位、地点、行业、技能结构、偏好和可选 resume version ref，不保存身份证、详细住址、政治、健康等敏感身份信息。
- Project facts 只应保存用户确认的 synthetic 或可公开复述事实，不应保存真实公司私密信息或内部不可公开材料。
- Project Rewrite 不自动修改简历版本；`risk_flags` / `forbidden_changes` 用于提醒用户不要过度包装。
- Interview questions / answers 只用于本地 deterministic training；Dashboard stats 只展示聚合计数、latest average score 和 latest weakness tags，不展示完整 `answer_text`、Resume raw_text 或 JD raw_text。
- Study Plan source_refs 只保存 preview 和引用 ID；StudyPlanPage 只展示 source refs preview；Dashboard study stats 只展示聚合计数和 latest target，不展示 source_refs 细节、Resume/JD raw_text 或完整 `answer_text`。
- RAG stats 只展示聚合计数、latest question preview 和 uncertainty，不返回 citations、source_refs、retrieval_debug、raw_text、full chunk text 或完整 answer。
- Interview / Study Plan optional RAG refs 只使用 grounded answer run 的短 evidence/source preview；ungrounded runs 不作为强来源，不自动写入任何下游模块。
- Agent step payload 和 `final_summary` 只保存 refs、短 metadata、score、next actions 和 created record IDs，不保存 Resume/JD/RAG 原文、完整 answer 或投递材料。
- Application linkage 只保存 `agent_run_id` ref；Application 仍是 tracking record，不自动投递、不自动状态流转。
- Bad Case 和 Evaluation Case 不应保存大段隐私原文；v1.5B regression linkage 只保存 refs、短摘要、root cause / fix strategy / tags 和 run/case IDs。

## 13. 后续只读验收与 Tag 建议

当前 v1.5B development 完成后，建议先提交并推送：

```bash
git commit -m "feat: add bad case evaluation regression foundation"
```

提交后建议进入 v1.5B final readonly acceptance。是否创建 v1.5 tag 需单独确认；本文档不建议直接打 tag。

只读验收前建议确认：

- `git status --short --branch` clean 且 `main` 与 `origin/main` 同步。
- 全量 backend tests、frontend build、`docker compose config`、`py_compile` 和 `git diff --check` 通过。
- Docker daemon 可用时补跑 `docker compose build`；如果不可用，在 release notes 中保留环境限制说明。
