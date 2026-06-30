# CareerAgent 阶段五：Application Management / 投递管理与 Dashboard 设计

## 阶段状态

- 5A：Application Management 设计文档与边界确认已完成。
- 5B：`applications` DB model、Alembic migration 和 schema 已完成。
- 5C：Application repository / service / API 和 tests 已完成。
- 5D：ApplicationTrackerPage 最小 UI 已完成。
- 5E：Dashboard 已接入 application stats。
- 当前实现仍保持 tracking：v1.3 支持可选 `agent_run_id` linkage，但不自动投递、不接招聘网站、不接真实 LLM、不做复杂拖拽 Kanban。

## 1. 阶段五目标

阶段五目标是建立手动投递管理与 application tracking 能力，把用户求职过程中的投递记录结构化、可追踪、可复查，并在 Dashboard 暴露基础统计。

当前 MVP 支持：

- 记录用户的求职投递记录。
- 可选关联 `resume_version`、`job_description`、`match_report`、`agent_run`。
- 记录公司、岗位、岗位类别、状态、投递日期、下一步日期、面试备注、复盘摘要和标签。
- 支持 application create / list / detail / patch。
- 支持通过 `status=archived` 归档，不提供单独 archive endpoint。
- 支持 ApplicationTrackerPage 最小 UI。
- 支持 Dashboard application stats。
- 支持后续与 Quality Review / Bad Case 关联。
- 当前阶段不做自动投递。
- 当前阶段不接招聘网站。
- 当前阶段不接 LLM 自动生成投递材料。
- 当前阶段不保存完整简历 / JD / 面试复盘原文。

现在适合做 Application Management，原因是当前项目已经具备 Resume Version、JD、Match Report、Agent Workflow 和 Quality Review。投递管理可以把前面模块串成真实求职流程记录，而 Quality Review 已经建立质量与风险边界，因此投递管理应保持手动、可控、隐私最小化。

## 2. 非目标

阶段五 MVP 不做：

- 不做自动投递。
- 不自动提交职位申请。
- 不接招聘网站 API。
- 不爬取岗位。
- 不保存招聘网站账号密码。
- 不接真实 LLM。
- 不接 OpenAI / DeepSeek / Qwen。
- 不自动生成投递材料。
- 不做邮件自动发送。
- 不做日历 / 提醒系统。
- 不做复杂 Kanban。
- 不做自动状态流转。
- 不保存完整 resume raw_text。
- 不保存完整 JD raw_text。
- 不保存完整面试复盘原文；`interview_notes` 和 `reflection` 只用于摘要备注。
- 不保存投递材料全文。
- 不做未经用户确认的外部动作。

阶段五是手动 tracking，不是自动申请工具。

## 3. 数据模型设计

### applications

用途：记录一条手动求职投递记录。

当前实现字段：

| 字段 | 类型建议 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | Application record ID |
| user_id | string | 是 | 默认 `default` |
| company | string | 是 | 公司名称 |
| role_title | string | 是 | 岗位名称 |
| role_category | string nullable | 否 | 岗位类别，可由已有 job profile 派生 |
| jd_id | string nullable | 否 | 目标 JD ref |
| resume_version_id | string nullable | 否 | 投递使用的 resume version ref |
| match_report_id | string nullable | 否 | 匹配报告 ref |
| agent_run_id | string nullable | 否 | Agent workflow run ref |
| status | string | 是 | 默认 `saved` |
| apply_date | date nullable | 否 | 实际投递日期 |
| next_step_date | date nullable | 否 | 下一步日期 |
| interview_notes | text nullable | 否 | 面试摘要备注，不保存隐私原文 |
| reflection | text nullable | 否 | 复盘摘要，不保存隐私原文 |
| tags | JSON list | 是 | 标签列表，默认空列表 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

字段说明：

- `company` 必填。
- `role_title` 必填。
- `user_id` 必填，默认 `default`。
- `status` 必填，默认 `saved`。
- `resume_version_id` / `jd_id` / `match_report_id` / `agent_run_id` 是 nullable refs。
- `interview_notes` / `reflection` nullable，只保存摘要，不保存隐私原文。
- `apply_date` / `next_step_date` nullable。
- `created_at` / `updated_at` 必填。

外键策略：

- 当前对 `jd_id`、`resume_version_id`、`match_report_id`、`agent_run_id` 使用 nullable FK，删除上游对象时 SET NULL。
- 原因是用户可能手动记录外部岗位，且上游对象可能 archive。
- Service 对传入 refs 做存在性校验；`match_report_id` 会校验并补齐对应 `jd_id` / `resume_version_id`。
- 不复制源对象全文。

当前索引：

- `status`
- `company`
- `role_category`
- `resume_version_id`
- `jd_id`
- `match_report_id`
- `agent_run_id`

暂不设计 `contact_person` / `recruiter` 等个人信息字段，避免过早保存个人信息。后续如需要联系人信息，应先做隐私设计。

## 4. Status 设计

Application status：

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

说明：

- 阶段五 MVP 只做 allowed values validation。
- 不做强状态机。
- 不做自动状态流转。
- 当前归档通过 `status=archived` 表示，不单独维护 `archived_at`。

## 5. API Contract

当前已实现以下 API。

### POST /api/applications

用途：创建 application record。

输入：

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
- `interview_notes`
- `reflection`
- `tags`

输出：

- `ApplicationRecord`

### GET /api/applications

用途：查询 application list。

Filters：

- `status`
- `company`
- `role_category`
- `resume_version_id`
- `jd_id`
- `agent_run_id`

输出：

- `ListResponse[ApplicationRecord]`

### GET /api/applications/{application_id}

用途：查看 application detail。

输出：

- `ApplicationRecord`

### PATCH /api/applications/{application_id}

用途：更新 `status`、基础字段、refs、日期、备注和标签。

输出：

- `ApplicationRecord`

### GET /api/applications/stats

用途：查询投递统计。

输出：

- `total_applications`
- `by_status`
- `interview_count`
- `offer_count`
- `rejected_count`
- `active_count`

归档说明：

- 当前 MVP 未单独实现 archive endpoint。
- 可通过 `PATCH /api/applications/{application_id}` 设置 `status=archived`。
- 初期不做提醒、日历、自动投递、招聘网站集成。
- response 不返回源对象原文。

## 6. 前端页面草案

页面：ApplicationTrackerPage，已实现最小版本。

最小功能：

- 安全提示区：只记录摘要和状态，不粘贴完整简历 / JD / 面试内容 / API key。
- Create Application form。
- Application list。
- Status / company / role category filters。
- Application detail。
- Update status。
- 通过状态更新支持 archived。
- Dashboard 增加 Applications、Interviews、Offers、Rejected、Active Apps 统计卡片。

说明：

- 初期不做 Kanban 拖拽。
- 初期不做复杂图表。
- 初期不做日历。
- 初期不做提醒系统。
- 初期不做自动投递按钮。

## 7. 与现有模块集成策略

与现有模块的关联方式：

- Resume Version：通过 `resume_version_id` 引用投递所用简历版本。
- JD / Job Profile：通过 `jd_id` 引用目标岗位。
- Match Report：通过 `match_report_id` 引用匹配依据。
- Agent Run：通过 `agent_run_id` 引用创建或绑定该投递记录的 deterministic workflow run。
- Quality Review / Bad Case：后续可允许 `source_type=application_record`，`source_id=application_id`。

初期策略：

- 阶段五 MVP 只保存 refs，不复制源对象全文。
- Agent Workflow 可创建或绑定 saved draft application，但只写 tracking record，不自动投递。
- 其他页面后续可考虑轻量 “Create application” 入口。
- 即使做入口，也必须用户确认，不得自动投递。
- 不做外部平台动作。

## 8. 隐私与安全策略

阶段五必须遵守：

- 不保存完整 resume raw_text。
- 不保存完整 JD raw_text。
- 不保存完整面试复盘原文。
- 不保存投递材料全文。
- 不保存 API Key。
- 不保存招聘网站账号密码。
- 当前不保存 `application_url`、联系人、招聘平台账号或渠道凭证。
- `interview_notes` / `reflection` 只写摘要，不粘贴完整隐私材料。
- 前端提示用户不要输入敏感原文。
- 不接第三方招聘平台 API。
- 不自动提交申请。
- 不做未经用户确认的外部动作。
- 后续如接邮箱 / 日历 / 招聘网站，必须单独做安全设计和授权边界。

## 9. 测试策略

阶段五测试：

DB infrastructure tests：

- `applications` table exists。
- ORM create application record。
- status defaults。
- refs persist。
- `interview_notes` / `reflection` persist。
- no `raw_text` / `jd_raw_text` / `interview_transcript` / `application_material_text` columns。

API tests：

- create application。
- list applications。
- filter by status / company / role_category / resume_version_id / jd_id / agent_run_id。
- get detail。
- patch status。
- missing application returns 404。
- invalid status returns 400。
- optional `jd_id` / `resume_version_id` / `match_report_id` / `agent_run_id` refs validate reasonably。
- response 不返回源对象原文。

Frontend build：

- ApplicationTrackerPage build 通过。

Safety tests：

- synthetic data only。
- no API key。
- no real resume / JD / interview content。

## 10. 阶段五子阶段拆分

已完成拆分：

- 5A：Application Management 设计文档与边界确认。
- 5B：`applications` DB model + migration + schema。
- 5C：Application repository / service / API + tests。
- 5D：ApplicationTrackerPage 最小 UI。
- 5E：Dashboard 接入 application stats。
- 5F：README / docs 更新。
- Release notes + tag：`v0.6.0-application-management`。

## 11. 风险与规避

| 风险 | 规避策略 |
| --- | --- |
| 用户误以为系统会自动投递 | 文档、API、前端都明确这是手动 tracking，不自动提交职位申请。 |
| notes 中保存过多隐私原文 | schema 和 UI 提示只写摘要；测试检查不出现敏感字段；文档明确不粘贴完整原文。 |
| application_url 或渠道信息泄露 | 只建议保存公开岗位链接；不保存账号、私信链接、内部推荐聊天记录或招聘平台凭证。 |
| 与自动投递边界混乱 | 阶段五不提供自动投递按钮、不接招聘网站 API、不做外部动作。 |
| 过早接招聘网站 API | 招聘网站集成必须作为后续独立阶段设计授权边界。 |
| 与 Agent Workflow 过度耦合 | Application 只保存 `agent_run_id` ref；Agent 只能创建/绑定 draft tracking record，不提交申请。 |
| 前端状态过复杂 | 先做 list / detail / form / filters，不做 Kanban、日历或复杂统计图。 |
| 状态流转过度设计 | 初期只做 allowed values validation，不做强状态机或自动流转。 |
| 过早保存 recruiter / contact_person 个人信息 | 初期不设计联系人字段；后续如需要，先做隐私和数据保留策略。 |

## 12. 当前仍未实现

- 不支持复杂 Kanban / 拖拽。
- 不支持日历 / 提醒。
- 不支持招聘网站同步。
- 不支持自动投递。
- 支持 `agent_run_id` 关联；不支持按 Agent 自动状态流转。
- 不支持联系人 / recruiter 信息。
- 不支持状态历史表。
- 不支持按时间趋势和转化漏斗图表。
