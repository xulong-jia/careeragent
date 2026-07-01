# CareerAgent Phase 2.5 Agent Workflow Productionization

阶段 2.5 把 Agent Workflow 从固定同步 demo 升级为 production foundation。它仍是 deterministic/local service pipeline，不是真实 LLM Agent，也不是 production-ready。

## Scope

已补齐的 Agent foundation 能力：

- Run status：`pending`、`running`、`completed`、`failed`、`need_more_info`、`cancelled`、`retrying`。
- Step status：`pending`、`running`、`completed`、`failed`、`skipped`、`need_more_info`。
- Run 记录：`input_refs`、`output_refs`、`final_output_ref`、`missing_slots`、`questions`、`error`、`run_config`、`retry_attempt`、`bad_case_id`、`bad_case_payload`、timestamps 和 `duration_ms`。
- Step 记录：`input_refs`、`output_refs`、`run_config`、`privacy_safe_payload`、`attempt`、timestamps、`duration_ms` 和 error。
- API：create/list/detail/steps，以及 `resume`、`retry`、`cancel`。
- Retry 不覆盖旧 step；同一 run 下用 `attempt` 追加新 step timeline。
- Step failure 自动创建 Bad Case draft；如果 Bad Case 写入失败，run 仍保存 `bad_case_payload`。
- Frontend AgentRunsPage 支持 workflow 选择、resume/retry/cancel、missing slots/questions、run config、Bad Case payload 和 step privacy payload 展示。

## Workflows

当前固定 workflows：

- `job_application_preparation`：Resume/JD -> Match -> optional RAG -> Project Rewrite -> Interview -> Study Plan -> Application -> final summary。
- `interview_preparation`：Resume/JD -> Match -> optional RAG -> Interview Questions -> final summary。
- `application_review`：Application ref -> application context review -> final summary。
- `study_gap_planning`：Resume/JD -> Match -> optional RAG -> Study Plan -> final summary。

缺少必需 refs 时，workflow 返回 `need_more_info`，并写入 `missing_slots` / `questions`。`resume` 只允许从 `need_more_info` 继续；`retry` 只允许从 `failed` 继续；`cancel` 只允许 `pending`、`running`、`need_more_info` 或 `retrying`。

## Privacy Boundary

Agent run/step 只保存 refs、IDs、counts、短 metadata、warnings 和 config metadata。`raw_text`、`jd_raw_text`、`chunk_text`、`full_text`、`resume_text`、`job_text`、`snippet`、API key、secret 和 token 不应进入 Agent payload。`rag_query` 只以 present flag 形式进入 persisted refs。

## Evaluation

`evals/datasets/service_level/agent_workflow_cases.json` 已扩展到 8 cases，覆盖：

- successful `job_application_preparation`
- `need_more_info`
- resume success
- failed step Bad Case payload
- retry success after failed step
- cancel
- `interview_preparation`
- `study_gap_planning`

Agent service-level metrics 包含 `expected_status_match`、`expected_step_coverage`、`missing_slot_match`、`resume_success`、`retry_success`、`cancel_success`、`bad_case_payload_present`、`run_config_present`、`privacy_safe_payload_present` 和 `case_pass`。

## Remaining Gaps

- 仍是同步 local runner，不是 durable queue/workflow engine。
- `running` / `retrying` 在当前同步 API 中通常很短暂；真实长任务需要 worker、lease、heartbeat 和 cancellation token。
- 仍不接真实 LLM planning/tool-calling，不做自主工具选择。
- Application 不自动投递，不自动改简历、项目、面试答案或学习任务状态。
- Agent eval 是 foundation regression，不是生产级 workflow benchmark。

阶段完成标准：Agent Workflow 达到 production foundation，不得称为 production-ready。
