# CareerAgent Final Acceptance Report

本报告记录 v1.1.0 `study-plan-center` final handoff 后的当前项目状态。结论基于当前仓库真实代码、测试和文档，不代表生产就绪系统。

## 1. 验收结论

v1.1.0 `study-plan-center` 已完成 deterministic Study Plan Center MVP，并与既有 Profile、Resume、JD、Match、Project Optimization、Interview Center、Dashboard、Quality Review 和 Evaluation 工作台集成。v1.0.0 `interview-center` 仍作为已完成的上一个稳定里程碑保留在本报告中。

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
| RAG Knowledge Base | 已完成 lexical deterministic prototype |
| Agent Runs | 已完成 deterministic state machine prototype |
| Application Tracking | 已完成手动 tracking MVP |
| Quality Review / Bad Case | 已完成人工复盘 MVP |
| Evaluation | 已完成 deterministic smoke evaluation MVP |
| Docker / Compose | 已完成本地开发配置；build 需在 Docker daemon 可用环境验证 |
| Docs / Demo | 已完成 v1.1 handoff 文档、demo script 和 release notes |

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

Interview Center 当前仍不做 Study Plan 自动写入、不接真实 LLM / LLM judge、不接 embedding/vector DB、不做 RAG completion、不做 Agent full workflow，也不展示 Resume/JD full raw_text 或完整已保存 `answer_text`。

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

Study Plan Center 当前仍不接真实 LLM，不做 RAG completion，不做 Agent full workflow，不接外部学习平台或日历提醒，不自动修改简历、项目、面试答案或投递状态。`source_refs` 只保存 preview 和引用 ID；Dashboard study stats 只展示聚合计数和 latest target，不返回 source_refs 细节、Resume/JD raw_text 或完整 `answer_text`。

## 6. 明确边界

当前 v1.1 明确不做：

- 不接真实 LLM。
- 不自动写回 Resume Version。
- 不编造项目经历、数字、公司、技术栈、上线状态、业务规模、用户量、收益或准确率。
- 不把 Study Plan 自动写回简历、项目、面试答案或投递记录。
- 不重写 Match Scoring。
- 不接 embedding / vector DB。
- 不做 RAG completion。
- 不做 Agent full workflow。
- 不接外部学习平台 API。
- 不做日历提醒。
- 不做自动投递。
- 不做认证、多用户权限。
- 不把 deterministic evaluation 当作模型能力最终评分。

## 7. 测试与检查结果

2026-06-25 在 `main` 执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

结果：237 passed, 6 warnings。

```bash
cd frontend && npm run build
```

结果：通过，TypeScript 和 Vite production build 成功。

```bash
docker compose config
```

结果：通过，Compose 配置可解析。

```bash
python3 -m py_compile scripts/seed_demo_data.py
```

结果：通过。

```bash
git diff --check
```

结果：通过。

```bash
docker compose build
```

结果：未验证。当前环境 Docker daemon/socket 不可用：

```text
failed to connect to the docker API at unix:///Users/jiaxulong/.docker/run/docker.sock
```

该结果记录为环境限制，不视为代码失败。Docker build 需要在 Docker daemon 可用环境重新验证。

## 8. 安全与隐私

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
- Bad Case 和 Evaluation Case 不应保存大段隐私原文。

## 9. 后续只读验收与 Tag 建议

当前 v1.1 handoff 文档完成后，建议提交：

```bash
git commit -m "docs: finalize v1.1 study plan center handoff"
```

提交并完成最终只读验收后，可考虑创建 annotated tag。当前文档只记录建议，不表示 tag 已创建：

```bash
git tag -a v1.1.0-study-plan-center -m "CareerAgent v1.1.0 study plan center"
```

打 tag 前建议确认：

- `git status --short --branch` clean 且 `main` 与 `origin/main` 同步。
- 全量 backend tests、frontend build、`docker compose config`、`py_compile` 和 `git diff --check` 通过。
- Docker daemon 可用时补跑 `docker compose build`；如果不可用，在 release notes 中保留环境限制说明。
