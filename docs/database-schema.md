# CareerAgent Database Schema

当前数据库是 SQLite + SQLAlchemy + Alembic 原型。表结构以 `backend/app/models/` 和 `backend/alembic/versions/` 为准。

## resumes

用途：记录用户上传的一份 resume 逻辑对象。

关键字段：

- `id`
- `user_id`
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
- `target_roles`
- `target_industries`
- `target_locations`
- `skill_map`
- `preferences`
- `source_resume_version_id`
- `created_at`
- `updated_at`

隐私说明：只保存求职目标、技能结构、偏好和可选 resume version ref，不复制 resume raw_text。

当前无认证系统，`user_id` 使用默认值 `default`；Profile 不应保存身份证、详细住址、政治、健康等敏感身份信息。

## projects

用途：保存用户手动确认的项目事实，作为后续项目优化、简历版本和岗位匹配的证据基础。

关键字段：

- `id`
- `user_id`
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

隐私说明：不复制 resume raw_text；`profile_id` 和 `resume_version_id` 只保存引用。`evidence` 应保存可证明材料摘要，不粘贴大段隐私原文。

## project_rewrites

用途：记录 deterministic project rewrite 结果，保存针对 JD 的匹配点、缺口、证据需求、改写建议和风险边界。

关键字段：

- `id`
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

隐私说明：只保存项目事实引用和 rewrite 产物，不复制 resume raw_text。`rewritten_bullets` 必须基于已有 project facts；缺少指标或证据时写入 `evidence_required` / `risk_flags`，不生成虚构数字、公司、用户量、收益、准确率、上线状态或技术栈。

## job_descriptions

用途：记录岗位 JD。

关键字段：

- `id`
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

## rag_documents

用途：记录 RAG 知识库文档。

关键字段：

- `id`
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

当前没有真实 embedding，`embedding_id` 是预留字段。

## agent_runs

用途：记录 deterministic workflow run。

关键字段：

- `id`
- `workflow_name`
- `status`
- `input_refs`
- `output_refs`
- `missing_slots`
- `questions`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`
- `duration_ms`

隐私说明：只保存 refs 和短 metadata，不复制 resume/JD/RAG 原文。

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

用途：记录手动投递 tracking。

关键字段：

- `id`
- `company`
- `role_title`
- `role_category`
- `jd_id`
- `resume_version_id`
- `match_report_id`
- `status`
- `apply_date`
- `next_step_date`
- `interview_notes`
- `reflection`
- `tags`

隐私说明：不复制 resume raw_text、JD raw_text 或投递材料全文。

## bad_cases

用途：记录人工质量复盘和错误样例。

关键字段：

- `id`
- `source_type`
- `source_id`
- `category`
- `severity`
- `title`
- `description`
- `expected_behavior`
- `actual_behavior`
- `suggested_fix`
- `status`
- `resolved_at`

隐私说明：只保存 source refs 和摘要，不粘贴大段隐私原文。

## evaluation_runs

用途：记录一次 deterministic evaluation run。

关键字段：

- `id`
- `name`
- `module`
- `dataset_name`
- `status`
- `metrics`
- `run_config`
- `started_at`
- `finished_at`

## evaluation_cases

用途：记录 synthetic / manual / bad_case 来源的评测 case。

关键字段：

- `id`
- `module`
- `dataset_name`
- `case_name`
- `input_payload`
- `expected_output`
- `tags`
- `source_type`
- `bad_case_id`

隐私说明：manual case 会拒绝 `raw_text` / `jd_raw_text` 等明显隐私字段；从 Bad Case 创建 case 时只保存 refs 和摘要。

## evaluation_results

用途：记录 evaluation run 中每个 case 的结果。

关键字段：

- `id`
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
