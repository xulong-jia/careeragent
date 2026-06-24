# CareerAgent Final Acceptance Report

本报告记录 v0.8.0 `resume-profile-foundation` handoff 后的当前项目状态，并补充 v0.9.0 `project-optimization` 当前收口状态。报告基于当前仓库真实代码、测试和文档，不代表生产就绪系统。

## 0. v0.9 Project Optimization 当前状态

v0.9.0 `project-optimization` 已完成 Project Optimization 的 deterministic MVP：

- 9A Project facts backend：新增 `projects` 表、Project model / schema / repository / service / API，支持 create / list / detail / patch，可按 `profile_id`、`resume_version_id`、`status` 筛选。
- 9B Project rewrite backend：新增 `project_rewrites` 表、ProjectRewrite model / schema / service / API，支持 `POST /api/projects/{project_id}/rewrite` 和 `GET /api/project-rewrites/{rewrite_id}`。
- 9B deterministic rewrite：生成 `matched_points`、`missing_points`、`evidence_required`、`rewritten_bullets`、`forbidden_changes`、`risk_flags`，不接真实 LLM，不自动写回 Resume Version。
- 9C ProjectOptimizationPage：前端接入 Project CRUD 和 Project Rewrite API，支持创建 / 更新 project facts、选择 project、运行 rewrite、展示 risk flags 和 forbidden changes。
- 9D Dashboard / docs / tests 收口：Dashboard 展示 project count、active project count、latest project name/status；README、API、DB schema、架构和 demo flow 已更新。

v0.9 仍明确不做：

- 不接真实 LLM。
- 不自动写回 Resume Version。
- 不编造项目经历、数字、公司、技术栈、上线状态或业务规模。
- 不做 Interview Center。
- 不做 Study Plan。
- 不重写 Match Scoring。
- 不接 embedding / vector DB。
- 不做认证、多用户。

## 1. 总体完成度

当前项目已经具备本地可运行、可持久化、可演示、可复查的 deterministic 求职工作台 prototype。v0.8 的核心变化是补齐数据入口基础：Resume Center 从 parser placeholder 升级为文本层提取 + deterministic parser / risk-check / confirmed version 保存，Profile Center 从缺失状态升级为 CRUD + readiness summary。

已完成：

- Profile Center MVP：profiles 表、Profile API、ProfilePage、profile summary / completeness、Dashboard readiness。
- Resume Center v0.8 foundation：PDF / DOCX / Markdown / txt 文本层提取、deterministic parser、risk-check、confirmed resume version 保存。
- ResumeCenterPage：parse、编辑 structured JSON、risk-check、save confirmed version UI。
- Resume / JD / Match 最小闭环。
- SQLite + SQLAlchemy + Alembic 持久化。
- Resume Version 查询、detail、clone、archive。
- RAG deterministic lexical prototype。
- Agent deterministic state machine prototype。
- Application Tracking + Dashboard MVP。
- Project Optimization deterministic MVP。
- Quality Review / Bad Case。
- Deterministic Evaluation MVP。
- Docker / Compose 本地开发配置。
- README、API、DB schema、架构、demo、安全隐私文档。

## 2. 已完成模块

| 模块 | 状态 |
| --- | --- |
| Profile Center | 已完成 v0.8 MVP |
| Resume Center | 已完成 v0.8 foundation MVP |
| Resume Versions | 已完成 MVP，支持 confirmed version 保存 |
| JD Center | 已完成 MVP |
| Match Report | 已完成 MVP |
| RAG Knowledge Base | 已完成 deterministic prototype |
| Agent Runs | 已完成 deterministic state machine prototype |
| Application Tracking | 已完成手动 tracking MVP |
| Dashboard | 已接入 profile readiness、resume parse status、risk flags count、project count / latest project status 和核心统计 |
| Project Optimization | 已完成 v0.9 deterministic MVP |
| Bad Case | 已完成人工质量复盘 MVP |
| Evaluation | 已完成 deterministic smoke evaluation MVP |
| Docker / Compose | 已完成本地开发配置 |
| Docs / Demo | 已完成 v0.8 handoff 说明 |

## 3. v0.8 / v0.9 验收结果

2026-06-24 在 `main` 执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

v0.8 handoff 结果：165 passed, 6 warnings。

v0.9 9D 于 2026-06-24 执行全量回归：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

结果：193 passed, 6 warnings。

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

结果：未完成。失败原因是当前环境 Docker daemon/socket 不可用：

```text
failed to connect to the docker API at unix:///Users/jiaxulong/.docker/run/docker.sock
```

该结果记录为环境限制，不视为代码失败。Docker build 需要在 Docker daemon 可用的环境重新验证。

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

结果：未完成。失败原因是本机 Docker daemon/socket 不可用：

```text
failed to connect to the docker API at unix:///Users/jiaxulong/.docker/run/docker.sock
```

该结果记录为环境限制，不视为代码失败。Docker build 需要在 Docker daemon 可用的环境重新验证。

## 4. Resume / Profile 当前能力

Resume Center：

- 支持 `.txt` / `.md` / `.markdown` UTF-8 文本读取。
- 支持 PDF 文本层提取，使用 PyMuPDF。
- 支持 DOCX 文本层提取，使用 python-docx。
- 支持 `POST /api/resumes/{resume_id}/parse` deterministic parser。
- 支持 `POST /api/resumes/{resume_id}/risk-check` deterministic risk-check。
- 支持 `POST /api/resumes/{resume_id}/versions` 保存 confirmed structured resume version。
- ResumeCenterPage 支持 parse、查看 raw text preview、编辑 structured JSON、risk-check、保存 confirmed version。
- 不接真实 LLM，不做 OCR，不做事实审计。
- risk-check 是规则检测，不自动修改简历。

Profile Center：

- 支持 `profiles` 表。
- 支持 Profile create / list / detail / patch / summary API。
- 支持 ProfilePage 创建、选择、更新 profile 和查看 readiness summary。
- Dashboard 展示 profile readiness / completeness。
- 当前无认证系统，`user_id` 默认 `default`。
- 当前不做多用户权限，不从简历自动生成 profile。

Dashboard：

- 展示 latest profile readiness level 和 completeness score。
- 展示 latest resume parse status 和 risk flags count。
- 展示 project count、active project count 和 latest project name/status。
- 保留 application / evaluation / RAG / Agent / Bad Case 等现有统计。

## 5. API / DB / Docs 状态

- API 文档：`docs/api-reference.md`
- DB schema 文档：`docs/database-schema.md`
- 当前架构：`docs/current-architecture.md`
- Demo 流程：`docs/demo-script.md`
- 安全清单：`docs/safety-privacy-checklist.md`
- v0.8 release notes：`docs/release-notes-v0.8.md`

关键 API 已列出：

- Profile APIs：`POST /api/profiles`、`GET /api/profiles`、`GET /api/profiles/{profile_id}`、`PATCH /api/profiles/{profile_id}`、`GET /api/profiles/{profile_id}/summary`
- Resume APIs：`POST /api/resumes/upload`、`POST /api/resumes/{resume_id}/parse`、`POST /api/resumes/{resume_id}/risk-check`、`POST /api/resumes/{resume_id}/versions`

关键 DB 字段已列出：

- `profiles`
- `resumes.parse_status`
- `resume_versions.risk_report`

## 6. Docker / Compose 状态

- 后端 Dockerfile：`backend/Dockerfile`
- 前端 Dockerfile：`frontend/Dockerfile`
- Compose：`docker-compose.yml`
- Compose 后端启动时执行 `alembic upgrade head`
- SQLite bind mount：`backend/local_data:/app/backend/local_data`
- `docker compose config` 已验证通过。
- `docker compose build` 因本机 Docker daemon 不可用未验证。

## 7. 安全与隐私

- `.env` 不进入 Git。
- `local_data/` 不进入 Git。
- SQLite DB 不进入 Git。
- uploads、vector index、exports、logs、cache 不进入 Git。
- Demo 和测试只使用 synthetic data。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。
- PDF / DOCX 解析只做文本层提取，不做 OCR。
- Resume `raw_text` 仍属于本地 prototype 数据；前端当前只展示 preview，后续生产化前需要继续收敛 raw_text 返回和日志策略。
- Profile 只保存目标岗位、地点、行业、技能结构、偏好和可选 resume version ref，不保存身份证、详细住址、政治、健康等敏感身份信息。
- risk-check 不自动修改简历。
- Bad Case 和 Evaluation Case 不应保存大段隐私原文。

## 8. 已知边界

- 不接真实 LLM parser、LLM reviewer、LLM judge 或真实 LLM Agent。
- 不接真实 embedding/vector database。
- 不做 OCR。
- 不做多模型评测。
- 不做自动投递。
- 不接招聘网站。
- 不做生产级多用户权限。
- 不做 PostgreSQL / pgvector 部署。
- Project Optimization、Interview Center、Study Plan 仍不是当前 v0.8 范围。
- Evaluation score 是 deterministic smoke score，不代表模型能力最终评分。

## 9. 后续建议

建议下一步在完成 v0.8 tag 前先提交本 handoff 文档：

```bash
git commit -m "docs: finalize v0.8 resume profile handoff"
```

提交后可考虑打 tag：

```bash
git tag v0.8.0-resume-profile-foundation
```

打 tag 前应在 Docker daemon 可用环境补跑 `docker compose build`，或在 release notes 中明确记录该项未验证的环境原因。
