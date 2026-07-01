# CareerAgent Database Schema

当前数据库是 SQLite + SQLAlchemy + Alembic 原型。P1 已新增 Auth / Workspace / Data Isolation schema，并补 PostgreSQL driver readiness；默认本地运行仍使用 SQLite。表结构以 `backend/app/models/` 和 `backend/alembic/versions/` 为准。

## P1 ownership model

P1 使用 `users`、`workspaces`、`workspace_memberships` 表表达当前账号和 workspace scope。核心业务表新增或补齐 owner 字段，repository/service 通过当前认证上下文过滤：

- `user_id`：业务数据所属 user。
- `workspace_id`：业务数据所属 workspace。

Owned tables 包括 `resumes`、`resume_versions`、`profiles`、`projects`、`project_rewrites`、`interview_questions`、`interview_answers`、`study_plans`、`job_descriptions`、`match_reports`、`rag_documents`、`rag_answer_runs`、`agent_runs`、`applications`、`bad_cases`、`evaluation_runs`、`evaluation_cases`、`evaluation_results`。P1 migration 对历史本地数据使用默认 owner/workspace 补值，便于原型库继续升级；production 数据迁移需要单独设计真实用户映射。

## users

用途：记录可登录用户。

关键字段：

- `id`
- `email`
- `password_hash`
- `display_name`
- `role`
- `is_active`
- `created_at`
- `updated_at`

隐私说明：`password_hash` 使用 PBKDF2 hash，不保存明文密码。`AUTH_JWT_SECRET` 不在数据库保存。

## workspaces

用途：记录 workspace/tenant scope。

关键字段：

- `id`
- `name`
- `created_at`
- `updated_at`

## workspace_memberships

用途：记录 user 与 workspace 的关系和 role。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `role`
- `created_at`

## audit_logs

用途：记录 P1 privacy delete-all 等基础审计事件。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `action`
- `metadata_json`
- `created_at`

隐私说明：audit metadata 只保存 action、counts 和 refs，不保存 raw resume/JD/RAG/interview/application payload。

## resumes

用途：记录用户上传的一份 resume 逻辑对象。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `filename`
- `file_type`
- `source_file_hash`
- `parse_status`
- `status`
- `created_at`
- `updated_at`

## resume_versions

用途：记录 resume 的版本历史、结构化解析结果和软归档状态。

关键字段：

- `id`
- `resume_id`
- `workspace_id`
- `version_name`
- `version_number`
- `target_role`
- `raw_text`
- `raw_text_preview`
- `structured_resume`
- `extraction_status`
- `extraction_method`
- `extraction_warnings`
- `risk_flags`
- `risk_report`
- `status`
- `created_at`
- `archived_at`

隐私说明：`raw_text` 是本地 prototype 数据，不应提交真实简历或输出到日志。前端 Resume Center 只展示 preview；生产化前需要继续收敛 raw_text 返回策略。

## profiles

用途：记录用户求职画像和后续匹配、学习计划、Agent 工作流可读取的手动确认上下文。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `target_roles`
- `target_industries`
- `target_locations`
- `skill_map`
- `preferences`
- `source_resume_version_id`
- `created_at`
- `updated_at`

隐私说明：只保存求职目标、技能结构、偏好和可选 resume version ref，不复制 resume raw_text。

P1 后 `user_id` / `workspace_id` 由认证上下文写入并用于过滤；旧本地数据可能仍带默认 owner。Profile 不应保存身份证、详细住址、政治、健康等敏感身份信息。

## projects

用途：保存用户手动确认的项目事实，作为后续项目优化、简历版本和岗位匹配的证据基础。

关键字段：

- `id`
- `user_id`
- `workspace_id`
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
- `created_at`
- `updated_at`

隐私说明：不复制 resume raw_text；`profile_id` 和 `resume_version_id` 只保存引用。`evidence` 应保存可证明材料摘要，不粘贴大段隐私原文。Project facts 不应保存真实公司私密信息、敏感商业数据或内部不可公开材料。

## project_rewrites

用途：记录 deterministic project rewrite 结果，保存针对 JD 的匹配点、缺口、证据需求、改写建议和风险边界。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `project_id`
- `jd_id`
- `resume_version_id`
- `match_report_id`
- `profile_id`
- `matched_points`
- `missing_points`
- `evidence_required`
- `rewritten_bullets`
- `forbidden_changes`
- `risk_flags`
- `rewrite_strategy`
- `created_at`

JSON 字段说明：

- `matched_points`：JD required / preferred skill 与 project facts 的命中证据。
- `missing_points`：未在 project facts 中命中的 JD skill gap。
- `evidence_required`：unsupported metric、missing evidence、timeline/scope evidence 等需要用户补证据的项目 claim。
- `rewritten_bullets`：基于已有 responsibilities / results 生成的保守改写建议，包含 before / after / reason / evidence_required / risk_level。
- `forbidden_changes`：固定列出不得新增的事实类型，例如 company、user_count、revenue、accuracy、production_status、business_scale、tech_stack_not_in_facts、unsupported_metric。
- `risk_flags`：unsupported metric、fabricated skill、missing evidence、overclaim、learning-to-business overclaim 等 deterministic 风险标记。

隐私说明：只保存项目事实引用和 rewrite 产物，不复制 resume raw_text，也不保存真实公司内部材料。`rewritten_bullets` 必须基于已有 project facts；缺少指标或证据时写入 `evidence_required` / `risk_flags`，不生成虚构数字、公司、用户量、收益、准确率、上线状态或技术栈。

## job_descriptions

用途：记录岗位 JD。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `company`
- `job_title`
- `location`
- `raw_text`
- `source_url`
- `status`
- `created_at`

隐私说明：`raw_text` 可能包含非公开 JD 或用户备注，当前仅用于本地 prototype。

## job_profiles

用途：记录 deterministic JD profile。

关键字段：

- `id`
- `jd_id`
- `profile_version`
- `role_category`
- `required_skills`
- `preferred_skills`
- `responsibilities`
- `interview_focus`
- `risk_level`

## match_reports

用途：记录 resume version 与 JD 的匹配报告。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `resume_version_id`
- `jd_id`
- `job_profile_id`
- `total_score`
- `dimension_scores`
- `evidence`
- `strengths`
- `gaps`
- `rewrite_priorities`
- `risk_flags`

## interview_questions

用途：记录 v1.0 Interview Center 10A/10D 使用的 deterministic 面试题；10D Dashboard stats 会基于该表聚合 question count、by question type 和 by difficulty。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `jd_id`
- `resume_version_id`
- `project_id`
- `project_rewrite_id`
- `question_type`
- `question`
- `expected_points`
- `source_refs`
- `difficulty`
- `created_at`

JSON 字段说明：

- `expected_points`：回答应覆盖的结构化要点，不是标准答案。
- `source_refs`：题目来源引用，只允许保存 `source_type`、`source_id`、`field`、`label` 和短 `preview`。v1.2 12D 可包含 grounded `rag_answer_run` / `rag_chunk` refs，不保存 RAG full chunk text 或完整 answer。

隐私说明：Interview question generation 只读取 JD profile、structured resume、project facts、project rewrite JSON 和可选 grounded RAG answer run refs，不复制 Resume/JD full raw_text。Ungrounded RAG answer runs 只产生 warning，不作为强来源。题目不得诱导用户编造上线、收益、用户量、准确率、公司经历或未提供的项目事实。

## interview_answers

用途：保存用户面试回答和 deterministic scoring 结果。v1.0 10B 提供 answer submit / list / score API，10D Dashboard stats 基于该表聚合 answer count、scored answer count、latest average score 和 latest weakness tags；默认 API response 只暴露 preview 和评分结果。

关键字段：

- `id`
- `question_id`
- `user_id`
- `workspace_id`
- `answer_text`
- `answer_text_preview`
- `scores`
- `feedback`
- `weakness_tags`
- `created_at`

JSON 字段说明：

- `scores`：deterministic scoring 结果，包含 `structure`、`technical_depth`、`business_understanding`、`evidence`、`clarity`、`risk_control` 和 `overall_average`。
- `weakness_tags`：规则生成的薄弱项标签，例如 `weak_structure`、`shallow_technical_depth`、`missing_evidence`、`overclaim_risk`。

隐私说明：`answer_text` 可能包含个人经历或面试复盘，仅保存在本地 DB 用于 deterministic scoring；默认 API response、列表、Dashboard 和 stats 不暴露完整回答原文。Dashboard stats 只读取聚合计数、`scores.overall_average` 和 `weakness_tags`，不读取或展示完整 `answer_text`。Scoring 不读取 Resume/JD full raw_text，不调用真实 LLM judge，也不自动写入 Study Plan。

## study_plans

用途：记录 v1.1 Study Plan Center 11A/11B/11C/11D 生成和维护的 deterministic 学习计划。当前提供 backend generate、list/detail、task status update、stats API、StudyPlanPage 和 Dashboard study stats。11E final handoff 已确认本阶段仍使用 `study_plans.phases` JSON 承载 task 结构，不新增独立 `study_tasks` 表。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `match_report_id`
- `profile_id`
- `project_rewrite_id`
- `target_role`
- `source_refs`
- `phases`
- `status`
- `created_at`
- `updated_at`

JSON 字段说明：

- `source_refs`：学习计划来源引用，只允许保存 `source_type`、`source_id`、`field`、`label` 和短 `preview`。v1.2 12D 可包含 grounded `rag_answer_run` / `rag_chunk` refs；ungrounded answer runs 只记录 uncertainty ref，不作为强来源。
- `phases`：阶段化学习计划，每个 phase 包含 `phase_id`、`phase`、`goal`、`tasks`、`resources`、`deliverables` 和 `acceptance_criteria`。
- `tasks`：v1.1 11A/11B/11C/11D 先保存在 `phases` JSON 中，不建独立 `study_tasks` 表。每个 task 包含稳定 `task_id`、`title`、`description`、`source_gap`、`priority`、`status`、`due_hint`、`acceptance_criteria`、`evidence_required` 和 `source_refs`。

状态：plan `status` 支持 `active`、`completed`、`archived`。Task `status` 支持 `todo`、`in_progress`、`done`、`blocked`、`skipped`。11B task status update 会定位 `phases[*].tasks[*].task_id`，更新 nested task 后重新赋值整个 `phases` JSON 并刷新 `updated_at`；本阶段不自动把 plan status 改为 completed。11D Dashboard study stats 基于 `study_plans.status` 和 `phases[*].tasks[*].status` 聚合 total/active/completed/archived plan count、pending/in_progress/done/blocked/skipped task count 和 latest target，不读取或返回 `source_refs` 细节、Resume/JD raw_text 或完整 `answer_text`。

隐私说明：Study Plan generation 可以读取 Profile、Match gaps、Project Rewrite missing/evidence signals、Interview weakness tags 和可选 grounded RAG answer run refs，但默认 response 不返回 Resume/JD full raw_text、完整 `answer_text`、RAG document raw_text 或 full chunk text。`source_refs` 只保存短 preview 和引用 ID。Study plan tasks 只建议补证据、补学习、写交付物或审计 claim，不自动修改简历、项目、面试答案或投递状态，不编造课程链接、公司经历、指标、上线状态或业务规模。

## rag_documents

用途：记录 RAG 知识库文档。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `title`
- `source_type`
- `source_uri`
- `raw_text`
- `metadata`
- `index_status`
- `chunk_count`

隐私说明：API response 默认返回 `raw_text_preview`，不默认返回完整 `raw_text`。

## rag_chunks

用途：记录 deterministic chunking 结果。

关键字段：

- `id`
- `document_id`
- `chunk_index`
- `section`
- `text`
- `token_count`
- `metadata`
- `embedding_id`
- `embedding_vector`
- `embedding_provider`
- `embedding_model`
- `embedding_dim`
- `embedding_version`
- `embedding_created_at`

阶段 2.2 后，chunk embedding vector 和 metadata 持久化在 DB。当前默认 provider 是 `local_bow` / `local-bow-v1`，不是最终 semantic embedding。API response 不返回 `embedding_vector` 本体；FAISS、pgvector 或 remote vector store 仍未作为 production default。

隔离说明：`rag_chunks` 不直接保存 owner 字段，按 `document_id -> rag_documents.id` 继承 document 的 user/workspace scope；search/list 会先过滤当前 owner 的 documents，再读取 chunks。

## rag_answer_runs

用途：记录 v1.2 12B persisted answer run contract，供后续 Evaluation、Bad Case 或 Agent 引用 answer run ID。记录可以是 grounded 或 ungrounded；v1.2 12D 中 `GET /api/rag/stats` 基于该表聚合 answer run counts；Interview / Study Plan generation 可选接收 `rag_answer_run_ids`，只把 grounded runs 转换为 preview-first source refs。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `question`
- `filters_json`
- `top_k`
- `retrieval_mode`
- `answer`
- `answer_type`
- `grounded`
- `uncertainty`
- `evidence_summary`
- `citations_json`
- `source_refs_json`
- `retrieval_debug_json`
- `created_at`
- `updated_at`

`POST /api/rag/answer` 默认 `persist=true`，会写入 `rag_answer_runs` 并返回 `answer_run_id`。如果 request 设置 `persist=false`，则只返回即时 answer contract，不写入该表。

隐私说明：`rag_documents.raw_text` 和 `rag_chunks.text` 仅保存在本地 DB 用于 deterministic chunking/search/answer。默认 API response 使用 `raw_text_preview`、`text_preview`、`snippet`、`citations.snippet` 和 `source_refs.preview`，不返回完整 raw text 或完整 chunk text。`rag_answer_runs.citations_json` 只保存短 snippet 和 metadata preview，`source_refs_json` 只保存短 preview，`retrieval_debug_json` 只允许保存 retrieval_mode、embedding_model、query_tokens、candidate_count、selected_chunk_ids、scores、top_k、filters、score_threshold 和 insufficient_reason，不包含 full raw_text、chunk text、Resume/JD raw_text 或完整 `answer_text`。12D stats 只返回聚合计数、latest question preview 和 uncertainty，不返回 citations/source_refs/retrieval_debug。v1.6 local vector/hybrid retrieval 不接真实外部 embedding/vector DB，不自动修改 Interview / Study Plan / Resume / Project / Application。

## agent_runs

用途：记录 deterministic workflow run。v1.3 `job_application_preparation` 会串联 Resume Version、JD、Match、可选 RAG search、Project Rewrite、Interview Questions、Study Plan 和 Application linkage。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `workflow_name`
- `status`
- `input_refs`
- `output_refs`
- `output_refs.final_summary`
- `missing_slots`
- `questions`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`
- `duration_ms`

JSON 字段说明：

- `input_refs`：workflow 输入 ID、布尔开关和是否提供 query 的短 metadata。
- `output_refs`：workflow 输出 ID、下游 created record IDs 和聚合摘要。
- `output_refs.final_summary`：`total_score`、`top_strengths`、`top_gaps`、`next_actions` 和 `created_records`。`AgentRunRecord.final_summary` 从该字段派生，便于前端直接展示。
- `missing_slots` / `questions`：缺少 resume version、JD、project 或 application refs 时的可恢复提示。

隐私说明：只保存 refs、短 metadata、分数、warnings 和 created record IDs，不复制 resume/JD/RAG 原文、完整 interview answer 或投递材料。

## agent_steps

用途：记录 workflow step timeline。

关键字段：

- `id`
- `run_id`
- `step_name`
- `step_order`
- `status`
- `input_refs`
- `output_refs`
- `error_code`
- `error_message`
- `duration_ms`

## applications

用途：记录手动投递 tracking。v1.3 新增可选 `agent_run_id`，用于把 Agent Workflow 创建或绑定的 draft application 与对应 run 关联。v1.4 补强 Product Operations 字段，并要求新建/更新后的投递记录绑定 JD + Resume Version。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `company`
- `role_title`
- `role_category`
- `jd_id`
- `resume_version_id`
- `match_report_id`
- `agent_run_id`
- `status`
- `apply_date`
- `next_step_date`
- `source_url`
- `location`
- `priority`
- `notes`
- `interview_notes`
- `reflection`
- `interview_question_ids`
- `last_contact_date`
- `tags`

关系说明：

- `jd_id` 外键到 `job_descriptions.id`；v1.4 service 要求 application tracking 记录必须绑定有效 JD。
- `resume_version_id` 外键到 `resume_versions.id`；v1.4 service 要求 application tracking 记录必须绑定有效 Resume Version。
- `match_report_id` 可选外键到 `match_reports.id`。
- `agent_run_id` 可选外键到 `agent_runs.id`，并带索引，支持按 workflow run 查询投递记录。

状态说明：`status` 支持 `saved`、`ready_to_apply`、`applied`、`written_test`、`first_interview`、`second_interview`、`hr_interview`、`offer`、`rejected`、`withdrawn`、`archived`。`priority` 支持 `low`、`medium`、`high`。

隐私说明：不复制 resume raw_text、JD raw_text、match 源对象全文、Agent step payload 或投递材料全文。`notes`、`interview_notes` 和 `reflection` 应保存摘要，不粘贴真实投递材料、完整面试复盘或隐私原文。Agent Workflow 只会创建/绑定 draft tracking record，不做自动投递或状态流转。

## application_status_history

用途：记录 Application status 的手动流转历史。v1.4 创建 application 时写入初始 status；PATCH status 且状态真实变化时写入新 history；PATCH 非状态字段不重复写入。

关键字段：

- `id`
- `application_id`
- `from_status`
- `to_status`
- `changed_at`
- `reason`
- `note`
- `created_at`

关系说明：

- `application_id` 外键到 `applications.id`，删除 application 时级联删除 history。

隐私说明：history 只保存状态、原因和短 note，不保存投递材料、简历/JD 原文或 Agent step payload。

## bad_cases

用途：记录人工质量复盘和错误样例。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `source_type`
- `source_id`
- `category`
- `severity`
- `title`
- `description`
- `expected_behavior`
- `actual_behavior`
- `suggested_fix`
- `root_cause`
- `fix_strategy`
- `tags`
- `added_to_eval_set`
- `status`
- `resolved_at`
- `verified_at`
- `regression_evaluation_run_id`
- `regression_evaluation_case_id`

状态说明：`status` 支持 `open`、`reviewing`、`fixed`、`verified`、`wont_fix`。`added_to_eval_set` 和 regression refs 用于追踪 bad case 是否已进入 deterministic regression evaluation。

隐私说明：只保存 source refs、短摘要、root cause / fix strategy summary 和 tags，不粘贴大段隐私原文。

## evaluation_runs

用途：记录一次 deterministic evaluation run。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `name`
- `module`
- `dataset_name`
- `status`
- `metrics`
- `run_config`
- `started_at`
- `finished_at`

`metrics` 包含 `total_count`、`passed_count`、`failed_count`、`failed_case_ids`、`pass_rate` 和 `by_module`。`run_config` 记录 deterministic flags 以及 prompt/schema/retrieval/model/code/evaluation version metadata。

## evaluation_cases

用途：记录 synthetic / manual / bad_case 来源的评测 case。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `module`
- `dataset_name`
- `case_name`
- `input_payload`
- `expected_output`
- `tags`
- `source_type`
- `bad_case_id`

`module` 当前支持 `jd_parser`、`resume_parser`、`match`、`rag`、`agent`、`application`、`bad_case`。`source_type` 支持 `synthetic`、`bad_case`、`manual`。

隐私说明：manual case 会拒绝 `raw_text` / `jd_raw_text` / `chunk_text` / `full_text` / `resume_text` / `job_text` 等明显隐私字段；从 Bad Case 创建 case 时只保存 refs 和摘要。

## evaluation_results

用途：记录 evaluation run 中每个 case 的结果。

关键字段：

- `id`
- `user_id`
- `workspace_id`
- `run_id`
- `case_id`
- `module`
- `status`
- `actual_output`
- `expected_output`
- `passed`
- `score`
- `error`

当前 score 是 deterministic MVP 下的 0 或 1，不代表模型能力最终评分。

## v1.5C Privacy / Security / Data Governance Notes

v1.5C 没有新增数据库表或 migration，复用现有 schema 实现本地 prototype 级治理：

- `resumes.status`：`DELETE /api/resumes/{resume_id}` 将 resume 标记为 `deleted`；默认 resume list/detail 只返回 `active`。
- `resume_versions.status` / `archived_at`：删除 resume 时归档该 resume 下所有 versions。
- `job_descriptions.status`：`DELETE /api/jobs/{jd_id}` 将 JD 标记为 `archived`；默认 JD list/detail 只返回 `active`。
- `applications.status`：`DELETE /api/applications/{application_id}` 将记录标记为 `archived`，并写入 `application_status_history`。默认 Application list/stats 排除 archived；可显式 `status=archived` 查询。
- `rag_documents` / `rag_chunks`：`DELETE /api/rag/documents/{doc_id}` 删除 document，并通过已有 relationship cascade 删除 chunks。
- `rag_answer_runs`：不删除历史 answer run；该表只保留 answer contract、短 citations/source_refs 和 safe retrieval debug，不复制 document raw_text 或 chunk full text。
- `evaluation_runs.run_config`：记录 prompt/schema/retrieval/model/code/evaluation version metadata，不记录 API key 或 secret。

## P1 Production Foundation Notes

P1 migration `20260630_0018_add_auth_workspace_isolation` 新增 auth/workspace/audit 表，并为 owned business tables 补 owner columns 和 indexes。后端当前用 application-level repository/service filters 实现隔离；这已经覆盖 P1 checkpoint 的基础 data isolation tests，但还不是数据库 RLS、完整 RBAC、SSO、MFA、refresh token rotation、centralized audit/SIEM、retention policy、backup erasure 或 irreversible deletion workflow。

P1 privacy delete-all 会清理当前 user/workspace 的业务数据并保留 audit log counts；它不声明生产级合规删除证明。
