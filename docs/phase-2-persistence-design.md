# CareerAgent 阶段二：数据持久化与版本管理设计

## 1. 阶段二目标

阶段二目标是将阶段一的一次性内存 Mock store 升级为可保存、可追踪、可对比的求职工作台。阶段二仍然不接入真实 LLM、RAG 或 Agent，重点是建立稳定的数据持久化基础。

- 保存 Resume、Resume Version、JD、Job Profile、Match Report。
- 支持刷新页面后数据不丢。
- 支持简历版本管理、历史记录和对比。
- 支持同一 JD 匹配多个简历版本。
- 支持同一简历或简历版本匹配多个 JD。
- 版本记录不可被静默覆盖。
- 为后续 RAG、Agent Workflow、投递管理和评测体系预留清晰边界，但不提前实现这些能力。

## 2. 非目标

阶段二只处理数据持久化与版本管理，不做以下内容：

- 用户登录 / 权限系统。
- RAG、embedding、vector index、retriever 或引用生成。
- Agent Workflow、agent runs 或 agent steps。
- 投递管理、自动投递或投递状态流转。
- Bad Case 页面。
- Evaluation Center 或正式评测体系。
- 真实 LLM 接入。
- OpenAI / DeepSeek / Qwen API。
- 提交真实简历、真实 JD、投递记录、面试复盘或真实 API Key。

## 3. 数据库策略

阶段二建议采用 SQLite first、PostgreSQL later 的策略。

- 本地开发默认数据库：`local_data/careeragent.db`。
- 推荐 `DATABASE_URL`：`sqlite:///./local_data/careeragent.db`。
- PostgreSQL 后续用于更接近生产的部署或多人协作环境，例如：`postgresql+psycopg://careeragent:careeragent@localhost:5432/careeragent`。
- SQLAlchemy 用于 ORM，保证 SQLite 与 PostgreSQL 后续可共用一套 model 和 repository 逻辑。
- Alembic 用于数据库迁移，确保表结构变化可追踪、可回滚。
- Repository 层用于隔离数据库查询，避免 API route 和 service 直接依赖 ORM 细节。
- `mock_store` 后续逐步退出主路径。阶段 2B 可以暂时保留用于对照测试，阶段 2C 起 Resume / JD 主路径应切换到 repository，阶段 2E 后 Match Report 主路径也应切换到 repository。
- `.env.example` 后续应保留空白或本地默认的 `DATABASE_URL` 示例，不应包含真实数据库密码。
- 阶段 2A 不直接修改 `docker-compose.yml` 引入 Postgres。原因是阶段二第一目标是确认数据模型和迁移顺序，SQLite 已足够验证持久化契约；过早引入 Postgres 会增加本地环境复杂度并干扰 API 迁移。

## 4. 核心表设计

阶段二只设计持久化闭环所需核心表，不提前设计 RAG、Agent、Application、Bad Case 或 Evaluation 表。

当前暂不实现 users/auth。所有记录可以先使用 `user_id = "default"` 占位。后续接入登录系统时，再将 `user_id` 迁移到真实用户表外键。

### resumes

用途：表示一份逻辑简历实体，承载文件来源和当前状态。实际文本和结构化结果保存在 `resume_versions`。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| user_id | string | 阶段二使用 `default` 占位 |
| title | string | 简历标题，默认可来自文件名 |
| original_filename | string | 原始上传文件名 |
| file_type | string | pdf / docx / markdown / text |
| source_file_hash | string | 上传内容 hash，用于去重和审计 |
| status | string | active / archived / deleted |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

- 主键：`id`。
- 外键：暂不依赖 users 表。
- JSON 字段：无。
- 隐私字段：`original_filename` 可能包含个人信息，日志中不得完整输出。
- Append-only：否。`status` 和 `updated_at` 可更新，但不应覆盖版本内容。

### resume_versions

用途：保存简历某一次解析或编辑后的版本。版本内容应尽量 append-only，避免静默覆盖。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| resume_id | string / uuid | 外键，指向 `resumes.id` |
| version_name | string | 用户可读版本名 |
| version_number | integer | 同一 resume 下递增 |
| raw_text | text | 简历原文或 parser placeholder |
| raw_text_preview | text | 用于列表和前端预览 |
| structured_resume | json | 结构化简历结果 |
| extraction_status | string | extracted / parser_placeholder / failed |
| extraction_method | string | utf8_txt_decode 等 |
| extraction_warnings | json | parser warning 列表 |
| risk_flags | json | 当前阶段仍为空数组或 mock flags |
| status | string | active / archived / deleted |
| created_at | datetime | 创建时间 |
| archived_at | datetime nullable | 归档时间 |

- 主键：`id`。
- 外键：`resume_id -> resumes.id`。
- JSON 字段：`structured_resume`、`extraction_warnings`、`risk_flags`。
- 隐私字段：`raw_text`、`raw_text_preview`、`structured_resume`。
- Append-only：是。正文和结构化结果创建后不应原地覆盖；修改应创建新版本。允许更新 `version_name`、`status`、`archived_at`。

### job_descriptions

用途：保存用户输入或粘贴的 JD 原文和基础岗位信息。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| user_id | string | 阶段二使用 `default` 占位 |
| company | string | 公司名 |
| job_title | string | 岗位名 |
| location | string nullable | 地点 |
| source_url | string nullable | 来源 URL |
| raw_text | text | JD 原文 |
| status | string | active / archived / deleted |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

- 主键：`id`。
- 外键：暂不依赖 users 表。
- JSON 字段：无。
- 隐私字段：`raw_text` 可能包含非公开 JD 或用户备注，日志中不得完整输出。
- Append-only：否。基础元数据可更新；若 raw JD text 需要变更，建议创建新 JD 或记录修订策略，避免静默改变历史匹配依据。

### job_profiles

用途：保存从 JD 中抽取出的岗位画像。阶段二仍然可以是 deterministic mock profile，但应持久化。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| jd_id | string / uuid | 外键，指向 `job_descriptions.id` |
| profile_version | integer | 同一 JD 下递增 |
| role_category | string | 岗位类别 |
| required_skills | json | 必备技能列表 |
| preferred_skills | json | 加分技能列表 |
| responsibilities | json | 职责列表 |
| business_scenarios | json | 业务场景 |
| hidden_requirements | json | 隐含要求 |
| interview_focus | json | 面试关注点 |
| risk_level | string | low / medium / high |
| summary | text nullable | 岗位画像摘要 |
| created_at | datetime | 创建时间 |

- 主键：`id`。
- 外键：`jd_id -> job_descriptions.id`。
- JSON 字段：`required_skills`、`preferred_skills`、`responsibilities`、`business_scenarios`、`hidden_requirements`、`interview_focus`。
- 隐私字段：`summary` 和 JSON 字段可能引用 JD 原文片段，日志中不得完整输出。
- Append-only：建议是。重新解析 JD 应创建新的 `profile_version`，避免覆盖历史匹配依据。

### match_reports

用途：保存某个 resume version 与某个 JD / job profile 的匹配报告。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| resume_version_id | string / uuid | 外键，指向 `resume_versions.id` |
| jd_id | string / uuid | 外键，指向 `job_descriptions.id` |
| job_profile_id | string / uuid nullable | 外键，指向 `job_profiles.id` |
| total_score | integer | 总分 |
| dimension_scores | json | 维度评分 |
| evidence | json | 证据列表 |
| strengths | json | 优势列表 |
| gaps | json | 差距列表 |
| rewrite_priorities | json | 改写优先级 |
| risk_flags | json | 风险标记 |
| created_at | datetime | 创建时间 |

- 主键：`id`。
- 外键：`resume_version_id -> resume_versions.id`、`jd_id -> job_descriptions.id`、`job_profile_id -> job_profiles.id`。
- JSON 字段：`dimension_scores`、`evidence`、`strengths`、`gaps`、`rewrite_priorities`、`risk_flags`。
- 隐私字段：`evidence`、`strengths`、`gaps`、`rewrite_priorities` 可能包含简历或 JD 片段。
- Append-only：是。匹配报告代表一次历史运行，不应被静默覆盖。

## 5. 表关系

```text
resumes
  -> resume_versions

job_descriptions
  -> job_profiles

resume_versions + job_descriptions/job_profiles
  -> match_reports
```

- 一个 resume 可以有多个 resume_versions。
- 一个 JD 可以有一个或多个 job_profiles。
- 一个 match_report 必须绑定一个 resume_version 和一个 JD。
- 一个 match_report 可以绑定一个 job_profile，用于追踪当时使用的岗位画像版本。
- 后续支持同一 JD 对比多个 resume_versions：通过查询同一 `jd_id` 下的多个 `match_reports` 实现。
- 后续支持同一简历或简历版本匹配多个 JD：通过查询同一 `resume_version_id` 下的多个 `match_reports` 实现。

## 6. 隐私与安全策略

- `raw_text`、`structured_resume`、JD `raw_text`、match `evidence` 都属于敏感或半敏感内容。
- 不允许日志输出完整 `raw_text`、完整 JD、完整 `structured_resume` 或完整 match evidence。
- 日志中如需定位问题，只允许输出 record id、hash、长度、状态码和错误 code。
- 不允许将 `local_data/` 提交 Git。
- 不允许提交真实简历、真实 JD、投递记录、面试复盘、上传文件、导出文件、日志或缓存。
- API Key 只允许存在于本地 `.env`，仓库只提交 `.env.example`。
- 后续需要支持删除策略，至少包括：
  - soft delete：将 `status` 改为 `deleted`。
  - hard delete：在明确确认后删除 resume / JD / match 数据及关联版本。
  - 删除行为需要避免孤儿记录，并保留最小审计信息。

## 7. API 兼容策略

- 阶段二改造时应尽量保持当前 response shape，不破坏前端。
- Repository 返回的数据应先映射为当前 Pydantic schemas，例如 `ResumeRecord`、`JobRecord`、`MatchReport`。
- 先让持久化主路径与阶段一 API 契约兼容，再逐步扩展 version fields。
- 前端不应一次性重写。优先保证现有 Dashboard、Resume Center、JD Center、Match Report 能读取持久化数据。
- 新增版本管理字段时可以采用向后兼容方式，例如增加 `resume_version_id`、`version_name`、`version_number`，但保留现有 `resume_id`。
- 错误响应仍保持统一结构：

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found.",
    "details": {}
  },
  "request_id": "..."
}
```

## 8. 迁移顺序

- 阶段 2B：SQLAlchemy / Alembic / DB session 初始化，SQLite 本地跑通。
- 阶段 2C：Resume / JD 持久化替换 `mock_store`。
- 阶段 2D：Resume Version 创建、复制、归档、详情与历史。
- 阶段 2E：Match Report 持久化，支持历史查询和版本对比。
- 阶段 2F：前端读取持久化列表、版本选择和历史展示。
- 阶段 2G：阶段二验收、安全检查和 README 更新。

迁移原则：

- 每个阶段都保持后端测试通过。
- 每个阶段都保持前端 build 通过。
- 不在同一个提交里同时引入 DB、重写 API、重写前端。
- 不让 `mock_store` 和 DB 在同一业务主路径中长期并存。

当前状态：阶段 2D 已在阶段 2C 的 Resume / JD DB 主路径基础上新增 Resume Version 后端能力。Resume Version 支持历史列表、详情、clone 和 archive；archive 只更新 `status="archived"` 和 `archived_at`，不删除历史内容。Match Report 仍未持久化，留到阶段 2E；同一 JD 多版本对比仍未实现。

## 9. 测试策略

- 使用 SQLite test database，建议每个测试或测试模块使用独立数据库文件或事务隔离。
- pytest fixture 每次隔离数据，避免测试顺序依赖。
- 增加 repository tests，覆盖 create / get / list / archive / version copy / match report history。
- 保留 API tests，确保 response shape 与阶段一兼容。
- 前端继续执行 `npm run build`，防止 API type 扩展破坏 TypeScript。
- 继续执行 `docker compose config`，确认本地开发配置可解析。
- 每次提交前做隐私扫描，确认没有 `.env`、`local_data/`、真实数据、API Key 或手册文件进入 Git。

## 10. 风险与规避

- 数据库引入后测试不稳定：使用独立 SQLite test database、fixture 清理数据、避免共享全局状态。
- `mock_store` 和 DB 混用：以 repository 为边界逐步替换，阶段完成后删除或隔离旧主路径。
- `raw_text` 隐私风险：禁止日志输出正文；测试使用合成 mock 文本；`local_data/` 保持 ignored。
- 版本记录被覆盖：`resume_versions` 和 `match_reports` 采用 append-only 策略，更新只允许改状态或名称。
- API schema 被破坏：先映射到现有 schemas，再添加向后兼容字段；前端 build 作为必跑检查。
- Docker / 本地环境复杂化：阶段 2B 先 SQLite，不直接引入 Postgres service。
- JSON 字段未来迁移困难：阶段二保留 JSON 以支持快速持久化；后续字段稳定后再考虑拆表或增加索引。

## 11. 阶段 2B 最小开发计划

阶段 2B 只应该做数据库基础设施初始化，不替换现有 API 主路径。

当前状态：阶段 2B 已按 SQLite first 方案加入 DB 基础设施、ORM skeleton、Alembic 初始 migration 和 `GET /api/db/health`。Resume / JD / Match API 主路径仍保持阶段一 Mock store 行为，持久化替换留给阶段 2C。

应该做：

- 添加 SQLAlchemy / Alembic 依赖。
- 创建 `backend/app/db/session.py`。
- 创建 `backend/app/db/base.py`。
- 创建 ORM models skeleton，覆盖 `resumes`、`resume_versions`、`job_descriptions`、`job_profiles`、`match_reports`。
- 配置 SQLite `DATABASE_URL`，默认指向 `local_data/careeragent.db`。
- 初始化 Alembic。
- 添加最小 DB health / migration 检查。
- 添加最小 repository 或 model import smoke tests。
- 保持现有 Resume / JD / Match API 主路径不变。

不应该做：

- 不替换 `mock_store` 主路径。
- 不重写前端。
- 不接 LLM、RAG 或 Agent。
- 不做投递管理。
- 不做 Bad Case。
- 不做正式 Evaluation Center。
- 不提交真实简历、真实 JD、API Key、投递记录、面试复盘或手册文件。
