# CareerAgent 阶段六：Application Management / 投递管理设计

## 1. 阶段六目标

阶段六目标是建立手动投递管理与 application tracking 能力，把用户求职过程中的投递记录结构化、可追踪、可复查。

阶段六计划支持：

- 记录用户的求职投递记录。
- 关联 `resume_version`、`job_description`、`match_report`、`agent_run`。
- 记录公司、岗位、渠道、URL、状态、优先级、投递时间、下一步动作、备注。
- 支持 application list / detail / update / archive。
- 支持后续 ApplicationTrackerPage 最小 UI。
- 支持后续与 Quality Review / Bad Case 关联。
- 当前阶段不做自动投递。
- 当前阶段不接招聘网站。
- 当前阶段不接 LLM 自动生成投递材料。
- 当前阶段不保存完整简历 / JD / 面试复盘原文。

现在适合做 Application Management，原因是当前项目已经具备 Resume Version、JD、Match Report、Agent Workflow 和 Quality Review。投递管理可以把前面模块串成真实求职流程记录，而 Quality Review 已经建立质量与风险边界，因此投递管理应保持手动、可控、隐私最小化。

## 2. 非目标

阶段六初期不做：

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
- 不保存完整面试复盘原文。
- 不保存投递材料全文。
- 不做未经用户确认的外部动作。

阶段六是手动 tracking，不是自动申请工具。

## 3. 数据模型设计

### application_records

用途：记录一条手动求职投递记录。

建议字段：

| 字段 | 类型建议 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | Application record ID |
| user_id | string | 是 | 默认 `default` |
| company_name | string | 是 | 公司名称 |
| job_title | string | 是 | 岗位名称 |
| job_location | string nullable | 否 | 岗位地点 |
| application_channel | string nullable | 否 | 渠道，建议默认 `manual` 或 nullable |
| application_url | string nullable | 否 | 公开岗位链接 |
| resume_version_id | string nullable | 否 | 投递使用的 resume version ref |
| jd_id | string nullable | 否 | 目标 JD ref |
| match_report_id | string nullable | 否 | 匹配报告 ref |
| agent_run_id | string nullable | 否 | 申请准备 workflow ref |
| status | string | 是 | 默认 `draft` |
| priority | string | 是 | 默认 `medium` |
| applied_at | datetime nullable | 否 | 实际投递时间 |
| next_action_at | datetime nullable | 否 | 下一步动作时间 |
| notes | text nullable | 否 | 摘要备注，不保存隐私原文 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |
| archived_at | datetime nullable | 否 | 归档时间 |

字段说明：

- `company_name` 必填。
- `job_title` 必填。
- `user_id` 必填，默认 `default`。
- `status` 必填，默认 `draft`。
- `priority` 必填，默认 `medium`。
- `application_channel` 建议默认 `manual` 或 nullable。
- `application_url` nullable，只保存公开岗位链接。
- `resume_version_id` / `jd_id` / `match_report_id` / `agent_run_id` 是 nullable refs。
- `notes` nullable，只保存摘要，不保存隐私原文。
- `applied_at` / `next_action_at` / `archived_at` nullable。
- `created_at` / `updated_at` 必填。

外键策略：

- 阶段六初期建议先保存 refs，不强制 FK。
- 原因是用户可能手动记录外部岗位，且上游对象可能 archive。
- 后续 service 可以做“存在则校验”的软约束。
- 不复制源对象全文。

索引建议：

- `status`
- `priority`
- `company_name`
- `created_at`
- `resume_version_id`
- `jd_id`
- `match_report_id`
- `agent_run_id`

暂不设计 `contact_person` / `recruiter` 等个人信息字段，避免过早保存个人信息。后续如需要联系人信息，应先做隐私设计。

## 4. Status / Priority 设计

Application status：

- `draft`
- `ready_to_apply`
- `applied`
- `online_assessment`
- `interview`
- `offer`
- `rejected`
- `withdrawn`
- `archived`

Priority：

- `low`
- `medium`
- `high`

说明：

- 阶段六初期只做 allowed values validation。
- 不做强状态机。
- 不做自动状态流转。
- `archived` 可由 `archived_at` 表示，也可 `status=archived` 双重标识；需要在 6B / 6C 再确认实现策略。

## 5. API Contract 草案

### POST /api/applications

用途：创建 application record。

输入建议：

- `company_name`
- `job_title`
- `job_location`
- `application_channel`
- `application_url`
- `resume_version_id`
- `jd_id`
- `match_report_id`
- `agent_run_id`
- `status`
- `priority`
- `applied_at`
- `next_action_at`
- `notes`

输出：

- `ApplicationRecord`

### GET /api/applications

用途：查询 application list。

Filters：

- `status`
- `company_name`
- `priority`
- `resume_version_id`
- `jd_id`
- `limit`

输出：

- `ListResponse[ApplicationRecord]`

### GET /api/applications/{application_id}

用途：查看 application detail。

输出：

- `ApplicationRecord`

### PATCH /api/applications/{application_id}

用途：更新 `status` / `priority` / `next_action_at` / `notes` / 基础字段。

输出：

- `ApplicationRecord`

### PATCH /api/applications/{application_id}/archive

用途：归档投递记录。

行为建议：

- 设置 `archived_at`。
- 设置 `status=archived`。

说明：

- 6C 再实现 API。
- 初期不做提醒、日历、自动投递、招聘网站集成。
- response 不返回源对象原文。

## 6. 前端页面草案

页面：ApplicationTrackerPage。

最小功能：

- 安全提示区：只记录摘要和状态，不粘贴完整简历 / JD / 面试内容 / API key。
- Create Application form。
- Application list。
- Filters。
- Application detail。
- Update status / priority / next_action_at / notes。
- Archive application。
- Dashboard 增加 Applications 卡片。
- 可显示不同状态数量或基础统计。

说明：

- 6D 再实现页面。
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
- Agent Run：通过 `agent_run_id` 引用申请准备 workflow。
- Quality Review / Bad Case：后续可允许 `source_type=application_record`，`source_id=application_id`。

初期策略：

- 阶段六初期只保存 refs，不复制源对象全文。
- 6B / 6C 不在 Resume / JD / Match / Agent 页面自动创建 application。
- 6E 再考虑轻量 “Create application” 入口。
- 即使做入口，也必须用户确认，不得自动投递。
- 不做外部平台动作。

## 8. 隐私与安全策略

阶段六必须遵守：

- 不保存完整 resume raw_text。
- 不保存完整 JD raw_text。
- 不保存完整面试复盘原文。
- 不保存投递材料全文。
- 不保存 API Key。
- 不保存招聘网站账号密码。
- `application_url` 只允许公开岗位链接。
- `notes` 只写摘要，不粘贴完整隐私材料。
- 前端提示用户不要输入敏感原文。
- 不接第三方招聘平台 API。
- 不自动提交申请。
- 不做未经用户确认的外部动作。
- 后续如接邮箱 / 日历 / 招聘网站，必须单独做安全设计和授权边界。

## 9. 测试策略

阶段六测试建议：

DB infrastructure tests：

- `application_records` table exists。
- ORM create application record。
- status / priority defaults。
- refs persist。
- notes persist。
- `archived_at` nullable。
- no `raw_text` / `jd_raw_text` / `interview_transcript` / `application_material_text` columns。

API tests：

- create application。
- list applications。
- filter by status / company_name / priority / resume_version_id / jd_id。
- get detail。
- patch status / priority / notes / next_action_at。
- archive application。
- missing application returns 404。
- invalid status / priority returns 400。
- response 不返回源对象原文。

Frontend build：

- ApplicationTrackerPage build 通过。

Safety tests：

- synthetic data only。
- no API key。
- no real resume / JD / interview content。

## 10. 阶段六子阶段拆分

推荐拆分：

- 6A：Application Management 设计文档与边界确认。
- 6B：`application_records` DB model + migration + schema skeleton。
- 6C：Application repository / service / API + tests。
- 6D：ApplicationTrackerPage 最小 UI。
- 6E：与 Resume / JD / Match / Agent 页面轻量 Create application 入口，必须用户确认。
- 6F：阶段六验收文档、安全检查、README 更新。
- Release notes + tag：`v0.6.0-application-management`。

## 11. 风险与规避

| 风险 | 规避策略 |
| --- | --- |
| 用户误以为系统会自动投递 | 文档、API、前端都明确这是手动 tracking，不自动提交职位申请。 |
| notes 中保存过多隐私原文 | schema 和 UI 提示只写摘要；测试检查不出现敏感字段；文档明确不粘贴完整原文。 |
| application_url 或渠道信息泄露 | 只建议保存公开岗位链接；不保存账号、私信链接、内部推荐聊天记录或招聘平台凭证。 |
| 与自动投递边界混乱 | 阶段六不提供自动投递按钮、不接招聘网站 API、不做外部动作。 |
| 过早接招聘网站 API | 招聘网站集成必须作为后续独立阶段设计授权边界。 |
| 与 Agent Workflow 过度耦合 | Application 只保存 `agent_run_id` ref，不由 Agent 自动创建或提交申请。 |
| 前端状态过复杂 | 先做 list / detail / form / filters，不做 Kanban、日历或复杂统计图。 |
| 状态流转过度设计 | 初期只做 allowed values validation，不做强状态机或自动流转。 |
| 过早保存 recruiter / contact_person 个人信息 | 初期不设计联系人字段；后续如需要，先做隐私和数据保留策略。 |

## 12. 阶段 6B 最小开发计划

6B 只应该做：

- 新增 ApplicationRecord ORM model。
- 新增 Alembic migration 创建 `application_records` 表。
- 新增 ApplicationRecord schema skeleton。
- 新增 DB infrastructure tests。
- 不实现 API。
- 不实现 service。
- 不实现 repository。
- 不改前端。
- 不接 LLM。
- 不做自动投递。
- 不接招聘网站。

建议 6B 文件：

- `backend/app/models/application.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/applications.py`
- `backend/alembic/versions/20260621_0006_create_application_records.py`
- `backend/tests/test_application_db_infrastructure.py`
