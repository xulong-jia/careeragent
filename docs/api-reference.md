# CareerAgent API Reference

所有 API 默认返回统一结构：

```json
{
  "data": {},
  "request_id": "..."
}
```

错误返回：

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable message.",
    "details": {}
  },
  "request_id": "..."
}
```

## Auth / Workspace Scope

公开入口：

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`

除上述入口外，`/api/*` 工作台 API 默认要求：

```text
Authorization: Bearer <access_token>
```

Token payload 包含当前 `user_id` 和 `workspace_id`。P1 后业务数据按当前 user/workspace scope 读写；跨用户或跨 workspace 访问应返回 404/401，而不是泄露目标对象存在性。P1 是基础认证和隔离 checkpoint，不等于完整 production-ready RBAC/SSO/MFA/refresh-token 体系。

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册 user，创建默认 workspace/membership，并返回 bearer token |
| POST | `/api/auth/login` | 使用 email/password 登录并返回 bearer token |
| GET | `/api/auth/me` | 查询当前 user/workspace；需要 bearer token |
| POST | `/api/auth/logout` | stateless logout success；需要 bearer token，前端负责清理本地 token |

Auth response 关键字段：

- `access_token`
- `token_type`
- `expires_at`
- `user.id`
- `user.email`
- `workspace.id`
- `workspace.name`
- `workspace.role`

## Health / DB

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/health` | API health check；v1.6 返回 provider/vector readiness metadata，不返回 API key 或 secret |
| GET | `/api/db/health` | DB reachability、database type、core table check |

`GET /health` response 关键字段：

- `status`
- `service`
- `ai_provider_mode`
- `llm_provider`
- `embedding_provider`
- `vector_store`
- `rag_retrieval_mode`
- `real_llm_enabled`
- `real_embedding_enabled`

隐私边界：health response 只暴露 provider mode、store/mode 和 enable flags，不返回 `LLM_API_KEY`、`EMBEDDING_API_KEY`、Authorization header、base URL secret 或模型调用 payload。

## Profile APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/profiles` | 创建用户求职画像 |
| GET | `/api/profiles` | 查询 profile 列表 |
| GET | `/api/profiles/{profile_id}` | 查询 profile detail |
| PATCH | `/api/profiles/{profile_id}` | 更新 profile |
| GET | `/api/profiles/{profile_id}/summary` | 查询 completeness / readiness summary |

关键字段：

- `id`
- `target_roles`
- `target_industries`
- `target_locations`
- `skill_map`
- `preferences`
- `source_resume_version_id`
- `readiness_level`
- `completeness_score`

隐私边界：Profile API 只保存目标、技能结构、偏好和可选 resume version ref，不返回 Resume raw text。P1 后 Profile 按当前 `user_id` / `workspace_id` 写入和过滤；旧本地数据可能仍带默认 owner。

## Project APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/projects` | 创建项目事实 |
| GET | `/api/projects` | 查询项目列表，可按 `profile_id`、`resume_version_id`、`status` 筛选 |
| GET | `/api/projects/{project_id}` | 查询项目事实详情 |
| PATCH | `/api/projects/{project_id}` | 更新项目事实或归档状态 |
| POST | `/api/projects/{project_id}/rewrite` | 针对 JD 运行 deterministic project rewrite |
| GET | `/api/project-rewrites/{rewrite_id}` | 查询 project rewrite 详情 |

关键字段：

- `id`
- `profile_id`
- `resume_version_id`
- `name`
- `role`
- `period`
- `background`
- `tech_stack`
- `responsibilities`
- `results`
- `evidence`
- `status`

Rewrite request 关键字段：

- `jd_id`
- `resume_version_id`
- `match_report_id`
- `profile_id`

Rewrite response 关键字段：

- `matched_points`
- `missing_points`
- `evidence_required`
- `rewritten_bullets`
- `forbidden_changes`
- `risk_flags`
- `rewrite_strategy`
- `rewrite_method`
- `confidence`

每条 `rewritten_bullets` item 包含：

- `before`
- `after`
- `reason`
- `evidence_required`
- `forbidden_changes`
- `matched_jd_requirements`
- `missing_points`
- `risk_level`
- `confidence`

当前 Project Rewrite 是 deterministic trustworthy foundation backend：只从用户保存的 project facts 和 JD profile 中提取匹配点，不接真实 LLM，不自动改写简历版本，不编造公司、用户量、收益、准确率、上线状态、业务规模、技术栈或 unsupported metric。risk_flags 覆盖 unsupported metric、fabricated skill、missing evidence、overclaim、learning-to-business overclaim、project/JD mismatch、unsupported production claim 和 unsupported business impact。Project API 不返回 Resume raw text，也不自动从简历生成项目事实。

前端流程：ProjectOptimizationPage 支持创建 / 更新 project facts、选择 project、输入 JD ID 运行 rewrite，并展示 matched points、missing points、evidence required、rewritten bullets、forbidden changes 和 risk flags。页面只展示建议，不自动写回 Resume Version。

v0.9 final handoff 的 Project Optimization API surface 以本节为准：Project CRUD 使用 `/api/projects`，rewrite 运行使用 `/api/projects/{project_id}/rewrite`，rewrite 详情查询使用 `/api/project-rewrites/{rewrite_id}`。

## Resume APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/resumes/upload` | 上传 `.pdf` / `.docx` / `.md` / `.markdown` / `.txt` 并提取文本 |
| POST | `/api/resumes/{resume_id}/parse` | parser foundation parse，返回结构化简历候选结果 |
| POST | `/api/resumes/{resume_id}/risk-check` | deterministic risk-check，不修改数据库 |
| POST | `/api/resumes/{resume_id}/versions` | 保存用户确认后的 structured resume version |
| GET | `/api/resumes` | 查询 resume 列表 |
| GET | `/api/resumes/{resume_id}` | 查询 resume detail |
| DELETE | `/api/resumes/{resume_id}` | 软删除 resume，并归档其 versions；默认列表/详情不再返回 |
| GET | `/api/resumes/{resume_id}/versions` | 查询 resume versions |

关键字段：

- `resume_id`
- `filename`
- `raw_text_preview`
- `structured_resume`
- `risk_flags`
- `risk_report`

`structured_resume` 在 2.3 后包含 `risk_flags`、`parse_confidence`、`evidence`、`warnings` 和 `parser_metadata`。默认 parser 是 local deterministic foundation；optional LLM parser 需要显式配置真实 provider。

隐私边界：Resume / Resume Version 默认 API response 不返回完整 `raw_text`。后端仍在本地 DB 保存 raw_text，用于 parse、risk-check 和保存 confirmed version；前端默认只展示短 `raw_text_preview`。`DELETE /api/resumes/{resume_id}` 是本地 prototype 的软删除/归档策略，不代表生产级不可恢复删除证明。

前端流程：Resume Center 会先调用 parse 生成可编辑 `structured_resume`，再用编辑后的 JSON 调用 risk-check，最后把 `structured_resume`、`risk_report`、`version_name`、`target_role` 和 `source_version_id` 提交到保存版本 API。risk-check 不会自动修改简历。

解析边界：PDF 使用文本层提取，DOCX 使用文档文本提取，Markdown / txt 使用 UTF-8 文本读取；当前不做 OCR，optional LLM parser 不是默认生产路径。risk-check 只做 unsupported metric、fabricated skill、timeline conflict、missing evidence、overclaim 等确定性规则检测，不是事实审计。

## Resume Version APIs

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/resume-versions/{version_id}` | 查询 version detail |
| POST | `/api/resume-versions/{version_id}/clone` | clone version |
| PATCH | `/api/resume-versions/{version_id}/archive` | soft archive |

关键字段：

- `resume_version_id`
- `version_name`
- `version_number`
- `target_role`
- `raw_text_preview`
- `status`
- `is_archived`

## JD APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/jobs` | 创建 JD 和 parser foundation job profile |
| GET | `/api/jobs` | 查询 JD 列表 |
| GET | `/api/jobs/{jd_id}` | 查询 JD detail |
| DELETE | `/api/jobs/{jd_id}` | 归档 JD；默认列表/详情不再返回 |

关键字段：

- `jd_id`
- `company`
- `job_title`
- `raw_text_preview`
- `job_profile.required_skills`
- `job_profile.preferred_skills`
- `job_profile.role_category`
- `job_profile.parse_confidence`
- `job_profile.evidence`
- `job_profile.warnings`
- `job_profile.parser_metadata`

隐私边界：JD 创建请求仍接收 `raw_text` 以生成 parser foundation profile；创建、列表和详情 response 默认只返回短 `raw_text_preview`，不返回完整 JD raw_text。归档 JD 不会删除历史 Application / Match refs。

## Match APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/matches/run` | 针对 resume version 和 JD 运行 trustworthy deterministic match foundation |
| POST | `/api/matches/compare` | 同一 JD 比较多个 resume versions，或同一 resume version 比较多个 JDs |
| GET | `/api/matches` | 查询 match reports |
| GET | `/api/matches?jd_id={jd_id}` | 按 JD 筛选 |
| GET | `/api/matches?resume_version_id={resume_version_id}` | 按 resume version 筛选 |
| GET | `/api/matches/{match_report_id}` | 查询 match detail |

关键字段：

- `match_report_id`
- `total_score`
- `dimension_scores`
- `strengths`
- `gaps`
- `evidence`
- `rewrite_priorities`
- `risk_flags`
- `recommended_projects`
- `score_breakdown`
- `scoring_method`
- `confidence`

`dimension_scores` 固定覆盖六维：`skill_match`、`project_relevance`、`business_understanding`、`expression_quality`、`education_fit`、`risk_control`。`score_breakdown` 记录 weights、weighted score、risk penalty、matched/missing required skills、project-supported required skills 和 `foundation_only=true`。

`POST /api/matches/compare` request 二选一：

- `{"jd_id": "...", "resume_version_ids": ["...", "..."]}`
- `{"resume_version_id": "...", "jd_ids": ["...", "..."]}`

Compare response 关键字段：

- `compare_mode`
- `sort_key`
- `items[].rank`
- `items[].match_report_id`
- `items[].resume_version_id`
- `items[].jd_id`
- `items[].total_score`
- `items[].score_delta_from_top`
- `items[].main_strengths`
- `items[].main_gaps`
- `items[].risk_flags`
- `items[].dimension_scores`

当前 Match 是 deterministic trustworthy foundation，不是生产级求职判断。分数必须结合 evidence、risk flags 和人工确认使用。

## Interview APIs

当前为 v1.0 Interview Center 10A/10B/10C/10D 范围：实现表结构、deterministic question generation、question list、answer submit / list、deterministic scoring、InterviewCenterPage 前端工作流和 Dashboard stats。v1.2 12D 补充可选 `rag_answer_run_ids`，只把 grounded RAG answer runs 作为 preview-first source refs；Study Plan 自动写入和 LLM judge 尚未实现。

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/interviews/questions/generate` | 基于 JD profile、structured resume、可选 project / project rewrite 生成 deterministic interview questions |
| GET | `/api/interviews/questions` | 查询已生成 questions，可按 `jd_id`、`resume_version_id`、`project_id`、`question_type`、`difficulty` 筛选 |
| POST | `/api/interviews/answers` | 提交面试回答，保存完整 `answer_text` 到本地 DB，默认 response 只返回 `answer_text_preview` |
| GET | `/api/interviews/answers` | 查询已提交 answers，可按 `question_id`、`jd_id`、`resume_version_id`、`project_id` 筛选 |
| POST | `/api/interviews/answers/{answer_id}/score` | 对已保存 answer 运行 deterministic scoring，返回 scores、feedback、weakness_tags 和 preview |
| GET | `/api/interviews/stats` | 查询 Interview Training 聚合统计，用于 Dashboard |

`POST /api/interviews/questions/generate` request:

- `jd_id`
- `resume_version_id`
- `project_id` optional
- `project_rewrite_id` optional
- `rag_answer_run_ids` optional：v1.2 12D 新增；仅 grounded answer runs 会补充 `source_refs`，ungrounded runs 返回 warning，不作为可靠来源
- `question_types` optional: `project_deep_dive` / `technical_depth` / `jd_skill_check` / `risk_or_gap_explanation` / `behavior_or_collaboration` / `resume_challenge`
- `max_questions` default `6`

关键字段：

- `id`
- `question_type`
- `question`
- `expected_points`
- `source_refs`
- `difficulty`
- `warnings`
- `need_more_info`

隐私边界：Interview questions 不返回 Resume/JD full raw_text。`source_refs` 只保存 `source_type`、`source_id`、`field`、`label` 和短 `preview`，用于追踪题目来源；RAG refs 只来自 persisted answer run 的短 `evidence_summary` / `source_refs.preview`，不返回 document raw_text、full chunk text 或完整 answer。题目生成不调用真实 LLM，不要求用户编造上线、收益、用户量、准确率或公司经历。

`POST /api/interviews/answers` request:

- `question_id`
- `answer_text`

`GET /api/interviews/answers` filters:

- `question_id` optional
- `jd_id` optional
- `resume_version_id` optional
- `project_id` optional

`POST /api/interviews/answers/{answer_id}/score` request body may be empty.

Answer response 关键字段：

- `id`
- `question_id`
- `user_id`
- `answer_text_preview`
- `scores`
- `feedback`
- `weakness_tags`
- `created_at`

Scoring dimensions:

- `structure`
- `technical_depth`
- `business_understanding`
- `evidence`
- `clarity`
- `risk_control`
- `overall_average`

隐私边界：Answer submit 会在本地 DB 保存完整 `answer_text`，用于后续 deterministic scoring；默认 API response、列表、Dashboard 和 stats 不返回完整 `answer_text`。Scoring 只使用已保存 answer、question、`expected_points` 和 `source_refs`，不读取或返回 Resume/JD full raw_text，不调用真实 LLM judge，不自动写入 Study Plan。

前端流程：InterviewCenterPage 使用 `frontend/src/api/interviews.ts` 调用上述真实 API，支持输入 `jd_id` / `resume_version_id` 和可选 RAG Answer Run IDs 生成 questions、按 filters 刷新 questions、选择 question、提交 answer、按 selected question 查询 answers，并对 selected answer 运行 scoring。页面中的 answer list 只展示 `answer_text_preview`，完整 `answer_text` 只保留在当前编辑 textarea 中。

`GET /api/interviews/stats` response 关键字段：

- `total_questions`
- `total_answers`
- `scored_answers`
- `latest_average_score`
- `latest_weakness_tags`
- `by_question_type`
- `by_difficulty`

Stats 隐私边界：只基于 `interview_questions` / `interview_answers` 做聚合，不返回完整 `answer_text`、Resume raw_text 或 JD raw_text。Dashboard 读取该 API 失败时会回退为空 stats，不阻断其他 workbench 数据加载。

## Study Plan APIs

当前为 v1.1 Study Plan Center 11A/11B/11C/11D 范围：实现 `study_plans` 表、deterministic generate service、list/detail、task status update、stats API、frontend API wrapper、StudyPlanPage 和 Dashboard study stats。v1.2 12D 补充可选 `rag_answer_run_ids`，用于把 grounded RAG answer runs 转为学习/证据复核 refs。v1.3 Agent Workflow 可调用 Study Plan generation；真实 LLM、外部学习平台和日历提醒尚未实现。

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/study-plans/generate` | 基于 target role、Profile、Match gaps、Project Rewrite signals、Interview weakness tags 和 request weakness tags 生成 deterministic study plan |
| GET | `/api/study-plans` | 查询 study plans，可按 `status`、`target_role`、`profile_id`、`match_report_id` 筛选 |
| GET | `/api/study-plans/{study_plan_id}` | 查询单个 study plan 详情 |
| PATCH | `/api/study-plans/{study_plan_id}/tasks/{task_id}` | 更新 phases JSON 中指定 task 的 status |
| GET | `/api/study-plans/stats` | 查询 Study Plan 后端聚合统计，供 Dashboard study stats 使用 |

`POST /api/study-plans/generate` request:

- `target_role` optional；为空时可从 `profile_id` 对应 profile 的 `target_roles` 推断。
- `profile_id` optional
- `match_report_id` optional
- `project_rewrite_id` optional
- `interview_answer_ids` default `[]`
- `rag_answer_run_ids` default `[]`：v1.2 12D 新增；grounded runs 可生成 `rag_grounded_evidence` 任务和 safe source refs，ungrounded runs 只记录 uncertainty ref，不作为强来源
- `weakness_tags` default `[]`
- `available_hours_per_week` default `5`
- `horizon_weeks` default `4`

Response 关键字段：

- `id`
- `user_id`
- `match_report_id`
- `profile_id`
- `project_rewrite_id`
- `target_role`
- `source_refs`
- `phases`
- `status`
- `created_at`
- `updated_at`

`phases` 内每个 task 包含：

- `task_id`
- `title`
- `description`
- `source_gap`
- `priority`
- `status`
- `due_hint`
- `acceptance_criteria`
- `evidence_required`
- `source_refs`

错误边界：

- `profile_not_found`
- `match_report_not_found`
- `project_rewrite_not_found`
- `interview_answer_not_found`
- `rag_answer_run_not_found`
- `study_plan_target_role_required`
- invalid `available_hours_per_week` / `horizon_weeks` 返回统一 `validation_error`

隐私边界：Study Plan generation 不返回 Resume/JD full raw_text，不返回完整 `answer_text`。`source_refs` 只保存 `source_type`、`source_id`、`field`、`label` 和短 `preview`。RAG refs 只读取 persisted answer run 的短 evidence/source preview，不返回 document raw_text、full chunk text、retrieval debug 细节或完整 answer。生成结果只创建学习任务、证据任务和 claim audit 任务，不自动修改简历、项目、面试答案或投递状态，也不编造课程链接、公司经历、指标、上线状态或业务规模。

`GET /api/study-plans` filters:

- `status` optional: `active` / `completed` / `archived`
- `target_role` optional
- `profile_id` optional
- `match_report_id` optional

`PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}` request:

- `status`: `todo` / `in_progress` / `done` / `blocked` / `skipped`

Task status update 只修改当前 study plan 的 `phases[*].tasks[*].status`，并刷新 `updated_at`；不会自动把 plan status 改为 completed，也不会修改简历、项目、面试答案或投递状态。`study_plan_id` 不存在返回 `study_plan_not_found`；`task_id` 不存在返回 `study_plan_task_not_found`；非法 status 返回统一 `validation_error`。

`GET /api/study-plans/stats` response 关键字段：

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

Stats 隐私边界：只基于 `study_plans` 和 `phases` JSON 做聚合，不返回 `source_refs` 细节、不返回 Resume/JD raw_text、不返回完整 `answer_text`。空数据返回 0 / null。

前端流程：StudyPlanPage 使用 `frontend/src/api/studyPlans.ts` 调用上述真实 API，支持输入 target role、profile/match/project rewrite/interview answer refs、可选 RAG Answer Run IDs 和 weakness tags 生成 study plan，按 filters 查询计划列表，查看 plan detail、source_refs preview、phases、tasks、resources、deliverables 和 acceptance criteria，并对每个 task 调用 PATCH API 更新 status。Dashboard 使用 `GET /api/study-plans/stats` 展示 plan/task 聚合统计和 latest target。页面和 Dashboard 只展示 source ref preview 或聚合数据，不展示 Resume/JD full raw_text 或完整 answer_text。

## RAG APIs

当前为 v1.2 RAG Completion deterministic MVP + 阶段 2.2 RAG production foundation 范围：实现 RAG document/chunk/index/search、DB-persisted local chunk vectors、grounded answer contract、answer run persistence、answer history list/detail、RAG stats、Dashboard RAG stats，以及 Interview / Study Plan optional grounded RAG answer run refs。阶段 2.2 在不改变默认 lexical 行为的前提下，补充 local bag-of-words embedding、vector/hybrid retrieval mode、score threshold 和 provider metadata。当前默认不接真实 LLM、外部 semantic embedding/vector DB、reranker、RAG evaluation dashboard 或自动写入 workflow；v1.3 Agent Workflow 只编排已有 RAG search / answer refs，不改变 RAG 自身边界。

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/rag/documents` | 创建 RAG document |
| GET | `/api/rag/documents` | 查询 documents |
| GET | `/api/rag/documents/{doc_id}` | 查询 document detail |
| DELETE | `/api/rag/documents/{doc_id}` | 删除 RAG document 及其 chunks；answer history 只保留 safe refs/citations |
| POST | `/api/rag/documents/{doc_id}/index` | deterministic chunk/index |
| GET | `/api/rag/chunks` | 查询 chunks，可按 `doc_id` 筛选 |
| POST | `/api/rag/search` | deterministic lexical/vector/hybrid search，返回 snippet-first sources 和 safe retrieval debug |
| POST | `/api/rag/answer` | deterministic grounded answer with citations / source_refs / retrieval_debug；默认持久化 answer run |
| GET | `/api/rag/answers` | 查询 persisted RAG answer runs，可按 grounded / uncertainty / retrieval_mode 筛选 |
| GET | `/api/rag/answers/{answer_run_id}` | 查询 persisted RAG answer run detail |
| GET | `/api/rag/stats` | 查询 RAG document/chunk/answer run 聚合统计，供 Dashboard RAG stats 使用 |

关键字段：

- `doc_id`
- `raw_text_preview`
- `chunk_count`
- `sources`
- `snippet`
- `uncertainty`
- `citations`
- `source_refs`
- `evidence_summary`
- `retrieval_debug`
- `answer_run_id`
- `latest_answer_question_preview`

`POST /api/rag/search` response：

- `query`
- `top_k`
- `retrieval_mode` request optional：`lexical` / `vector` / `hybrid`；legacy `deterministic_*` alias 仍可输入；默认使用 `RAG_RETRIEVAL_MODE=lexical`
- `score_threshold` request optional：过滤低分来源
- `sources[]`
- `sources[].doc_id`
- `sources[].chunk_id`
- `sources[].snippet`
- `sources[].score`
- `sources[].metadata`
- `sources[].retrieval_mode`
- `sources[].embedding_provider`：仅 vector/hybrid retrieval 返回
- `sources[].embedding_model`：仅 vector/hybrid retrieval 返回
- `sources[].vector_index_used`：vector/hybrid 是否使用持久化 chunk vector
- `uncertainty`
- `retrieval_debug`

`POST /api/rag/answer` request：

- `question`
- `top_k`
- `filters`
- `retrieval_mode` optional：同 search
- `score_threshold` optional：同 search
- `persist`：可选，默认 `true`；设置为 `false` 时不写入 `rag_answer_runs`，response 中 `answer_run_id=null`

`POST /api/rag/answer` response 仍保留旧的 `sources` 字段，同时 v1.2 返回 grounded answer contract：

- `answer_run_id`
- `answer`
- `grounded`
- `uncertainty`：`grounded` / `no_relevant_source` / `insufficient_evidence`
- `answer_type`
- `retrieval_mode`
- `evidence_used`
- `evidence_summary`
- `citations[]`：`source_type`、`document_id`、`chunk_id`、`title`、`section`、`label`、短 `snippet`、`score`、`metadata_preview`
- `source_refs[]`：`source_type=rag_chunk`、`source_id`、`document_id`、`chunk_id`、`field=snippet`、`label`、短 `preview`、`score`
- `retrieval_debug`：`retrieval_mode`、`retrieval_version`、`schema_version`、`model_version`、`embedding_provider`、`embedding_model`、`vector_index_used`、`score_threshold`、`query_tokens`、`candidate_count`、`selected_chunk_ids`、`scores`、`top_k`、`filters`、`insufficient_reason`

`GET /api/rag/answers` filters：

- `grounded`
- `uncertainty`
- `retrieval_mode`

`GET /api/rag/answers` 和 `GET /api/rag/answers/{answer_run_id}` 返回 `RagAnswerRunRecord`：

- `answer_run_id`
- `question`
- `filters`
- `top_k`
- `retrieval_mode`
- `answer`
- `answer_type`
- `grounded`
- `uncertainty`
- `evidence_summary`
- `citations`
- `source_refs`
- `retrieval_debug`
- `created_at`
- `updated_at`

`GET /api/rag/stats` response：

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

隐私边界：RAG API 默认不返回完整 document `raw_text`、chunk `text` 或 `embedding_vector`。`citations.snippet`、`source_refs.preview` 和 document/chunk preview 均为短文本；`retrieval_debug` 只包含 IDs、scores、counts、query metadata、retrieval mode、embedding provider/model、vector_index_used 和版本字段，不包含 full raw_text、chunk text、Resume/JD raw_text 或完整 `answer_text`。12B 新增的 `rag_answer_runs` 只保存 grounded answer contract。12D `GET /api/rag/stats` 只返回聚合计数、latest question preview 和 uncertainty，不返回 citations、source_refs 或 retrieval_debug。v1.5C `DELETE /api/rag/documents/{doc_id}` 删除 document/chunks，但不会回写或扩展历史 answer runs。阶段 2.2 vector/hybrid retrieval 使用 DB-persisted local vectors；local bag-of-words vectorizer 不是最终 semantic embedding，不强制 FAISS、pgvector 或外部 vector DB，也不自动写入 Interview / Study Plan / Resume / Project / Application。

前端流程：v1.2 12C 中 `frontend/src/api/rag.ts` 提供 `listRagAnswerRuns` 和 `getRagAnswerRun`，KnowledgeBasePage 可以按 grounded、uncertainty 和 retrieval_mode 查询 persisted answer runs，并查看 answer run detail、citations、source_refs preview 和折叠 retrieval_debug。v1.2 12D 新增 `getRagStats`，Dashboard 展示 RAG Documents、Indexed Documents、RAG Chunks、Grounded/Ungrounded Answers、Latest RAG Answer 和 Latest RAG Uncertainty；StudyPlanPage / InterviewCenterPage 可输入 RAG Answer Run IDs 作为可选 refs。页面只展示 snippet / preview / safe debug，不展示 document raw_text、full chunk text、Resume/JD raw_text 或完整 interview answer_text，也不提供自动写入 Interview / Study Plan / Resume / Project / Application 的操作。

## Agent APIs

当前为 v1.3 Agent Workflow Baseline + Application Linkage 范围：`job_application_preparation` deterministic workflow 会串联 Resume Version、JD profile、Match Report、可选 RAG search、RAG context summary、Project Rewrite、Interview Question generation、Study Plan generation，并创建或绑定 Application draft。它仍不是自由聊天 Agent，不接真实 LLM，不自动投递，也不自动修改 Resume / Project / Interview / Study Plan 内容。

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/agents/runs` | 创建 deterministic workflow run |
| GET | `/api/agents/runs` | 查询 runs，可按 workflow/status 筛选 |
| GET | `/api/agents/runs/{run_id}` | 查询 run detail |
| GET | `/api/agents/runs/{run_id}/steps` | 查询 step timeline |

当前 workflow：

- `job_application_preparation`

`POST /api/agents/runs` request:

- `workflow_name`
- `resume_id` optional；未传 `resume_version_id` 时会使用该 resume 的 latest active version
- `resume_version_id` optional
- `jd_id`
- `project_ids` optional；为空时按 `resume_version_id` 自动查找 active projects
- `application_id` optional；传入时 workflow 绑定已有 application
- `create_application` optional，默认 `true`；没有 `application_id` 时创建 draft application，设为 `false` 则跳过 application 创建
- `use_rag` optional
- `rag_query` optional；`use_rag=true` 时必填，用于 legacy deterministic RAG search step
- `rag_answer_run_ids` optional；传给 Interview / Study Plan 生成，只使用 grounded answer run refs

关键字段：

- `run.id`
- `status`
- `input_refs`
- `output_refs`
- `final_summary`
- `missing_slots`
- `steps`

当前 step order：

1. `validate_inputs`
2. `load_resume_version`
3. `load_job_profile`
4. `run_match_report`
5. `rag_search`
6. `summarize_rag_context`
7. `run_project_rewrites`
8. `generate_interview_questions`
9. `generate_study_plan`
10. `create_or_link_application`
11. `build_final_summary`

`build_final_summary` 输出：

- `resume_version_id`
- `jd_id`
- `match_report_id`
- `project_rewrite_ids`
- `interview_question_ids`
- `study_plan_id`
- `application_id`
- `rag_answer_run_ids`
- `rag_source_count`
- `grounded_source_count`
- `rag_context_warnings`
- `rag_context_summary`
- `final_summary.total_score`
- `final_summary.top_strengths`
- `final_summary.top_gaps`
- `final_summary.rag_context`
- `final_summary.next_actions`
- `final_summary.created_records`

错误 / 缺槽边界：

- 缺少 resume / resume version 返回 `need_more_info`，missing slot 名为 `resume_version_id`。
- 缺少或不存在 `jd_id` 返回 `need_more_info`。
- 不存在的 `project_ids` 或 `application_id` 返回 `need_more_info`。
- 下游 Project Rewrite / Interview / Study Plan / Application linkage 失败会记录对应 step error，并把 run 标记为 `failed`。

隐私边界：Agent step payload 只保存 IDs、refs、短 metadata、scores、warnings 和 created record IDs，不保存 Resume/JD full raw_text、RAG full chunk text、完整 interview answer 或投递材料。

## Application APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/applications` | 创建手动投递 tracking record |
| GET | `/api/applications` | 查询投递列表 |
| GET | `/api/applications?status={status}` | 按 status 筛选 |
| GET | `/api/applications?company={company}` | 按 company 筛选 |
| GET | `/api/applications?role_category={role_category}` | 按 role category 筛选 |
| GET | `/api/applications?resume_version_id={resume_version_id}` | 按 resume version 筛选 |
| GET | `/api/applications?jd_id={jd_id}` | 按 JD 筛选 |
| GET | `/api/applications?match_report_id={match_report_id}` | 按 Match Report 筛选 |
| GET | `/api/applications?agent_run_id={agent_run_id}` | 按 Agent run 筛选 |
| GET | `/api/applications?priority={priority}` | 按 priority 筛选 |
| GET | `/api/applications/{application_id}` | 查询 detail |
| PATCH | `/api/applications/{application_id}` | 更新状态或摘要字段 |
| DELETE | `/api/applications/{application_id}` | 将 Application 归档为 `archived` 并写 status history |
| POST | `/api/applications/{application_id}/reflection` | 写入或更新投递复盘摘要 |
| GET | `/api/applications/{application_id}/status-history` | 查询状态历史 |
| GET | `/api/applications/stats` | 查询投递统计 |

关键字段：

- `application_id`
- `company`
- `role_title`
- `status`
- `jd_id`
- `resume_version_id`
- `match_report_id`
- `agent_run_id`
- `source_url`
- `location`
- `priority`
- `notes`
- `interview_notes`
- `reflection`
- `interview_question_ids`
- `last_contact_date`
- `status_history`

Status enum：

- `saved`
- `ready_to_apply`
- `applied`
- `written_test`
- `first_interview`
- `second_interview`
- `hr_interview`
- `offer`
- `rejected`
- `withdrawn`
- `archived`

v1.4 规则：

- `POST /api/applications` 必须最终绑定 `jd_id` 和 `resume_version_id`；可以直接传入，也可以通过有效 `match_report_id` 推断。
- `match_report_id` 和 `agent_run_id` 为可选 linkage；传入时后端校验存在和归属关系。
- 创建记录会写入一条初始 `application_status_history`。
- `PATCH /api/applications/{application_id}` 只有 status 真实变化时才写新的 status history；更新 notes、priority、dates、refs、reflection 等非状态字段不会重复写 history。
- 非法 status 或 priority 返回统一 `application_invalid_field`。
- `POST /api/applications/{application_id}/reflection` 只更新 application reflection / interview notes / weakness tags，不自动写 Bad Case、不自动生成 Study Plan。
- `DELETE /api/applications/{application_id}` 不物理删除投递记录；它把记录归档为 `archived`，并写一条 status history。默认 `GET /api/applications` 和 `/stats` 不展示 archived；可显式使用 `status=archived` 查看。

`GET /api/applications/stats` response 关键字段：

- `total` / `total_applications`
- `by_status`
- `active_count`
- `interview_count`
- `offer_count`
- `rejected_count`
- `withdrawn_count`
- `conversion.applied_to_interview_rate`
- `conversion.interview_to_offer_rate`
- `conversion.applied_to_offer_rate`
- `upcoming_count`
- `overdue_count`
- `latest_applications`

Application 仍是手动 tracking record。v1.3 允许 Agent Workflow 创建 draft 或把已有 application 绑定到 `agent_run_id`；v1.4 只加强运营字段、状态历史和统计，不会自动投递、不会接招聘网站、不会自动状态流转，也不会保存完整投递材料。

## Privacy APIs

P1 privacy endpoints 只作用于当前 authenticated user/workspace，并使用现有 preview/ref/summary 边界；它们是本地 prototype 的数据治理 baseline，不等于生产级不可恢复删除证明或备份擦除流程。

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/privacy/export` | 导出当前 user/workspace 的数据摘要和 refs，不返回 secret 或大段 raw payload |
| DELETE | `/api/privacy/delete-all` | 删除/归档当前 user/workspace 的业务数据，并写入 audit log |
| GET | `/api/privacy/audit-log` | 查询当前 user/workspace 的 audit log |

`GET /api/privacy/export` response 关键字段：

- `user`
- `workspace`
- `counts`
- `items`

`DELETE /api/privacy/delete-all` response 关键字段：

- `status`
- `deleted_counts`
- `audit_log_id`

## Bad Case APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/evaluations/bad-cases` | 创建人工 bad case |
| GET | `/api/evaluations/bad-cases` | 查询 bad cases |
| GET | `/api/evaluations/bad-cases/{bad_case_id}` | 查询 detail |
| PATCH | `/api/evaluations/bad-cases/{bad_case_id}` | 更新 status/severity/摘要字段 |
| POST | `/api/bad-cases` | 创建人工 bad case，新直连路径 |
| GET | `/api/bad-cases` | 查询 bad cases，新直连路径 |
| GET | `/api/bad-cases/stats` | 查询 Bad Case lifecycle / module / type stats |
| POST | `/api/bad-cases/{bad_case_id}/add-to-eval` | 将 Bad Case 加入 `regression` evaluation set，幂等 |

关键字段：

- `source_type`
- `source_id`
- `category`
- `severity`
- `status`
- `description`
- `root_cause`
- `fix_strategy`
- `tags`
- `added_to_eval_set`
- `verified_at`
- `regression_evaluation_run_id`
- `regression_evaluation_case_id`

`status` 支持 `open`、`reviewing`、`fixed`、`verified`、`wont_fix`。Bad Case API 只保存 refs 和摘要，不保存 Resume/JD raw text、RAG full chunk text 或完整面试回答。

## Evaluation APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/evaluations/runs` | 创建并执行 deterministic evaluation run |
| GET | `/api/evaluations/runs` | 查询 runs |
| GET | `/api/evaluations/runs/{run_id}` | 查询 run summary |
| GET | `/api/evaluations/runs/{run_id}/results` | 查询 run results |
| GET | `/api/evaluations/cases` | 查询 evaluation cases |
| POST | `/api/evaluations/cases` | 创建 manual evaluation case |
| POST | `/api/evaluations/cases/from-bad-case/{case_id}` | 从 Bad Case 创建 evaluation case |
| GET | `/api/evaluations/datasets` | 查询 built-in / fileized dataset metadata |
| GET | `/api/evaluations/stats` | 查询 evaluation stats |

关键字段：

- `evaluation_runs.metrics.pass_rate`
- `evaluation_runs.metrics.failed_case_ids`
- `evaluation_runs.run_config.prompt_version`
- `evaluation_runs.run_config.schema_version`
- `evaluation_runs.run_config.retrieval_version`
- `evaluation_runs.run_config.model_version`
- `evaluation_runs.run_config.code_version`
- `evaluation_runs.run_config.evaluation_version`
- `evaluation_cases.bad_case_id`
- `evaluation_results.passed`
- `evaluation_results.score`

当前内置 synthetic smoke 支持 7 个 deterministic modules：`jd_parser`、`resume_parser`、`match`、`rag`、`agent`、`application`、`bad_case`。`service_level` dataset 额外覆盖 `project_rewrite`，并将 Match 扩展到 trustworthy foundation metrics。文件化 fixtures 位于 `evals/datasets/` 和 `evals/expected/`。当前只支持 deterministic smoke / service-level foundation / regression tracking，不做 LLM judge，不做多模型对比。
