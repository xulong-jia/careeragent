# CareerAgent 校招求职平台

CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。项目目标是把用户画像、简历版本、JD 理解、匹配评分、项目优化、面试准备、学习计划、投递管理、RAG 知识库、Agent Workflow、Bad Case 和评测体系组织成可运行、可追踪、可复查的工程链路。

CareerAgent 不是简历润色器，也不是 ChatGPT 套壳。本仓库当前已在 SQLite + SQLAlchemy 基础上支持 Profile Center MVP、Resume / JD / Match Report 持久化、Resume Version 历史管理、真实 PDF / DOCX / Markdown / txt 文本提取、JD/Resume real parser production foundation、deterministic risk-check、2.4 trustworthy Match Scoring + Project Rewrite foundation、Interview Center 题目生成、答案提交、deterministic scoring 前端工作流和 Dashboard training stats、Study Plan Center 11A/11B/11C/11D backend generate/list/detail/task status/stats API、StudyPlanPage 和 Dashboard study stats、RAG local vector production foundation、v3.2 semantic provider/reranker/LLM grounded RAG optional foundation、2.5 Agent Workflow production foundation、2.6 security/privacy/deployment production foundation、v3.0 security/privacy/data-governance production foundation candidate、v3.1 production deployment/database/operations foundation candidate、v3.2 production AI quality foundation candidate、v1.4 Product Operations / Application Management hardening、人工 Quality Review / Bad Case 闭环、v1.5B deterministic evaluation regression foundation、v1.5C privacy / security / data governance controls、v1.6 Production AI & Deployment Readiness baseline，以及 P1 Production Foundation 的 token auth、workspace scope、data isolation 和 privacy export/delete/audit baseline。默认仍不调用真实 LLM，不做 LLM judge、不做多模型评测、不做自动投递。

v3.2 定位：当前仓库只能称为 real parser + real RAG + trustworthy match/project rewrite + agent workflow + security/privacy/data-governance + production deployment/database/operations + production AI quality foundation candidate，不能称为 production-ready。deterministic、mock、synthetic、prototype、本地可演示或骨架完整的模块均不是生产级 DONE；真实缺口以 `docs/production-gap-baseline.md`、`docs/quality-gates.md`、`docs/security-privacy-deployment-hardening.md`、`docs/production-deployment-runbook.md`、`docs/database-operations.md`、`docs/operations-runbook.md`、`docs/production-ai-quality-upgrade.md`、`docs/real-evaluation-foundation.md`、`docs/real-rag-production-path.md`、`docs/real-parser-foundation.md`、`docs/trustworthy-match-foundation.md` 和 `docs/agent-workflow-productionization.md` 为准。下一阶段应是 v3.3 Frontend Productization & End-to-End Experience，不是打 production-ready tag。

## 技术栈

- Backend: FastAPI, Pydantic, Uvicorn, SQLAlchemy, Alembic, SQLite local dev；production config requires PostgreSQL-compatible `DATABASE_URL`
- Frontend: React, TypeScript, Vite；Node.js >= 20.19.0 for local/CI builds
- Test: pytest, Vite build
- Deployment: Docker Compose 本地开发骨架、v3.1 production-like PostgreSQL/pgvector compose profile、production runtime config fail-fast baseline
- Auth foundation: PBKDF2 password hash、HS256 bearer token、workspace membership、request-scoped owner filter
- AI readiness: deterministic LLM provider interface, local/vector semantic-shaped embedding providers, optional OpenAI-compatible HTTP providers, persisted RAG chunk vectors, lexical/vector/hybrid retrieval, optional reranker and LLM grounded RAG answer contract
- Later phase: v3.3 Frontend Productization & End-to-End Experience

## 当前能力

- Profile Center：创建、查询、更新用户求职画像，查看 completeness / readiness summary。
- v0.8 + 2.3 Resume + Profile Foundation：PDF / DOCX / Markdown / txt 文本层提取、Resume parser evidence/confidence/warnings/risk flags、confirmed resume version 保存，以及 Profile CRUD / readiness summary。
- v0.9 + 2.4 Project Optimization：保存、查询和更新项目事实，支持可选绑定 profile / resume version；Project Rewrite backend 和 ProjectOptimizationPage 已接入 trustworthy deterministic rewrite，展示 matched_points、missing_points、evidence_required、rewritten_bullets、forbidden_changes、risk_flags、rewrite_method 和 confidence；每条 bullet 带 before/after/reason/evidence_required/forbidden_changes/matched_jd_requirements/missing_points/risk_level/confidence。
- v1.0 Interview Center 10A/10B/10C/10D：新增 `interview_questions` / `interview_answers` 表、deterministic question generation / list API、answer submit / list API、deterministic scoring API、InterviewCenterPage 和 Dashboard interview training stats；本阶段不做 Study Plan 写入或 LLM judge。
- v1.1 Study Plan Center 11A/11B/11C/11D：新增 `study_plans` 表和 `POST /api/study-plans/generate`，基于 Profile、Match gaps、Project Rewrite missing/evidence signals、Interview weakness tags 和 request weakness tags 生成 deterministic phases/tasks/resources/deliverables/acceptance criteria；新增 list/detail、task status update、stats API、frontend API wrapper、TypeScript types、StudyPlanPage 和 Dashboard study stats。v1.1 阶段不接真实 LLM，不做 RAG refs、外部学习平台或日历提醒；v1.2 12D 已补 optional grounded RAG answer run refs，v1.3 Agent Workflow 可调用 Study Plan generation。
- Resume / JD / Match：上传 synthetic resume、解析 PDF / DOCX / Markdown / txt、创建 JD parser foundation profile、运行 2.4 trustworthy deterministic match report；Match 输出六维评分、维度 evidence、risk deduction、score_breakdown、recommended_projects、scoring_method/confidence，并支持 `/api/matches/compare`。
- Resume Versions：查询、clone、archive；Resume Center 已支持 parse、risk-check 和保存 confirmed structured resume version。
- RAG Knowledge Base：document、chunk/index、lexical/vector/hybrid search、local bag-of-words embedding、DB-persisted chunk vectors、deterministic grounded answer。阶段 2.2 已把 chunk embedding vector 和 provider/model/dim/version metadata 持久化到 DB；v3.2 新增 semantic provider metadata、offline `local_semantic` foundation、reranker contract、`answer_mode=llm_grounded` schema-validated grounded answer optional path 和 prompt/model/fallback metadata；`POST /api/rag/answer` 在保留 `sources` 兼容字段的同时返回 `citations`、`source_refs`、`evidence_summary`、`evidence_used`、`retrieval_mode`、safe `retrieval_debug` 和可选 `answer_run_id`。
- Agent Runs：2.5 deterministic workflow production foundation，支持 `job_application_preparation`、`interview_preparation`、`application_review`、`study_gap_planning`，具备 run lifecycle、attempt-aware step timeline、resume/retry/cancel、missing slots/questions、failure Bad Case draft、run_config、privacy-safe payload 和 `final_summary`。
- Application Tracking：v1.4 手动投递运营中心，要求绑定 JD + Resume Version，支持 Application Board、状态历史、reflection、interview notes、priority、upcoming/overdue/conversion stats，并支持可选 `match_report_id` / `agent_run_id` linkage。
- Quality Review / Bad Case：人工记录 bad case，可维护 root cause、fix strategy、tags、状态和 regression eval linkage。
- Evaluation：保留 7 模块 `synthetic_smoke_v1` contract regression；阶段 2.1 新增 `service_level` 脱敏样例集和 runner，真实调用当前 `job_service`、`resume_service`、`match_service`、`project_rewrite_service`、`rag_service`、`agent_service` 和 `agent.runner`，输出 metrics、failed cases、actual outputs 和 run config。阶段 2.3 已扩展 JD 12 cases、Resume 8 cases 和 parser evidence/confidence/warnings metrics；阶段 2.4 已扩展 Match 9 cases 并新增 Project Rewrite 6 cases；阶段 2.5 已扩展 Agent Workflow 8 cases；v3.2 新增 100-case synthetic benchmark foundation、human review sample、calibration、score stability、bad-case regression trend、RAG recall@k/MRR/groundedness metrics。当前仍不是 production-quality benchmark。
- Privacy / Security / Governance：v1.5C 新增集中 redaction 工具、Resume/JD/Application/RAG 删除或归档 API、默认列表隐藏 deleted/archived 数据、RAG/Agent/Evaluation 版本元数据，以及前端删除/归档入口；默认响应仍只展示 preview / refs / summary，不返回 full raw text。
- Production AI / Deployment Readiness：v1.6 新增 `backend/app/ai` provider 边界、deterministic fallback、OpenAI-compatible provider skeleton、health/config visibility、Docker/env placeholders 和部署文档；阶段 2.2 新增 local vector embedding persistence。真实外部 provider 必须显式 opt-in。
- P1 Production Foundation：新增 `/api/auth/register`、`/api/auth/login`、`/api/auth/me`、`/api/auth/logout`，业务 API 默认要求 bearer token；新增 `users`、`workspaces`、`workspace_memberships`、`audit_logs` 和 owned table 的 `workspace_id` / owner filtering；新增 privacy export、delete-all 和 audit-log API。P1 是生产化基础 checkpoint，不代表完整 production-ready SaaS。
- 2.6 Security / Privacy / Deployment：新增 production runtime validation、masked config summary、structured request logging、redacted error details、`/ready` / `/api/ready` readiness checks、privacy delete-summary / deletion proof、关键 auth/agent/eval/bad-case/privacy audit events；SQLite 明确只作为 local dev/test，production 配置必须使用 PostgreSQL-compatible URL。
- v3.0 Security / Privacy / Data Governance：新增 Fernet envelope 应用层敏感字段加密、`DATA_ENCRYPTION_KEY` / `DATA_ENCRYPTION_KEY_ID` production validation、token `jti` + logout revoke、route-level RBAC permission gate、mutating API audit foundation、privacy delete dry-run/execute proof，以及 Evaluation/Bad Case 更严格 redaction/encryption。v3.0 仍不是 production-ready；KMS/rotation backfill、backup purge、SSO/MFA、refresh token、SIEM 和 DB RLS 仍是后续阶段。
- v3.1 Production Deployment / Database / Operations：新增 `docker-compose.prod-like.yml`、PostgreSQL/pgvector deployment profile、frontend production nginx image、`.env.production.example`、DB pool config、`/live`、增强 `/ready` migration/storage checks、`/metrics`、Agent/Eval/RAG structured run logs，以及 migration/backup/restore/quality-gate scripts。v3.1 仍不是 production-ready；cloud deployment proof、managed observability、automated backup purge 和前端 E2E 仍是后续阶段。
- v3.2 Production AI Quality：新增 semantic embedding provider metadata、offline semantic-shaped provider、OpenAI-compatible embedding retry、RAG reranker contract、LLM grounded RAG answer optional path、LLM parser mode、OCR/table/bilingual resume foundation metadata、100-case benchmark dataset、human review calibration、score stability 和 bad-case regression trend。v3.2 仍不是 production-ready；真实 anonymized datasets、真实 provider benchmark、人类评审协议、LLM judge、production vector DB 应用路径和 v3.3 前端 E2E 仍是后续阶段。
- Dashboard：集中展示 Profile readiness、Resume、JD、Match、Project count / latest project status、Interview Training、Study Plan stats、RAG document/chunk/answer stats、Agent run status/score、Application operations stats、Bad Case、Evaluation 统计。

当前明确不做：

- 不做自动投递。
- 不接招聘网站。
- 不接真实 LLM judge。
- 默认不接真实 LLM parser、LLM reviewer 或 LLM Agent；2.3 parser 默认仍是 local deterministic foundation，v1.6 provider 仅为 opt-in readiness baseline。
- 不做 OCR；PDF / DOCX 当前只做文本层提取。
- 不自动写回 Resume Version，不编造项目经历、数字、公司、技术栈、上线状态或业务规模。
- 不做多模型评测平台。
- 不声明完整生产级多租户权限体系；P1 只完成 token auth、workspace scope 和基础 data isolation。
- 不把 pgvector deployment profile 等同于应用已完成 pgvector semantic retrieval；v3.2 已补 semantic provider metadata / reranker / benchmark foundation，但真实 provider + production vector DB application path 仍未认证。
- 不提交真实简历、真实 JD、投递记录、面试复盘或 API key。
- 不把当前 v3.0 foundation candidate 误标成 production-ready；KMS/rotation backfill、备份擦除、集中审计、完整 SSO/MFA/refresh-token/session 管理、DB RLS 和生产部署 runbook 仍是缺口。

## 目录结构

```text
backend/       FastAPI 应用、API 路由、配置与错误处理
frontend/      React + TypeScript + Vite 工作台 UI
docs/          架构、API、数据库、RAG、Agent、评测等文档
evals/         后续评测数据集、期望输出和评测脚本
scripts/       本地开发、检查和辅助脚本
local_data/    本地上传、向量索引、导出、日志和缓存，不进入 Git
```

## 本地运行

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
export AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars
export DATA_ENCRYPTION_KEY=MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew=
export DATA_ENCRYPTION_KEY_ID=local-dev-v1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/live
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
```

### 前端

```bash
cd frontend
npm install
cp .env.example .env.local  # 可选；默认 VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

默认访问：

```text
http://localhost:5173
```

### Docker Compose

```bash
cp .env.example .env
docker compose build
docker compose up
```

Docker Compose 默认文件只用于本地开发启动前后端服务。后端容器启动时会执行 `alembic upgrade head`，SQLite 数据通过 bind mount 保存到 `backend/local_data/careeragent.db`。默认 deterministic mode 不需要真实 AI provider key；P1 auth 必须设置 `AUTH_JWT_SECRET`，v3.0 数据加密必须设置 `DATA_ENCRYPTION_KEY` / `DATA_ENCRYPTION_KEY_ID`。Compose 会拒绝空 auth secret，本地可复制 `.env.example` 中的 dev-only placeholders；`APP_ENV=production` 会拒绝 dev-only/placeholder auth secret、本地 dev data encryption key、SQLite `DATABASE_URL`、`DB_ECHO_SQL=true` 和 `*` CORS。

v3.1 production-like profile：

```bash
cp .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod-like.yml config
docker compose --env-file .env.production -f docker-compose.prod-like.yml up -d
```

production 必须通过 secret manager 或部署环境注入强随机 auth secret、生产 Fernet data key 和 PostgreSQL-compatible database URL。不要提交 `.env` / `.env.production`，不要挂载真实简历、真实 JD、真实文档、投递记录或面试复盘。`docker-compose.prod-like.yml` 使用 PostgreSQL/pgvector 和 nginx frontend build，但仍是 production-like foundation，不是云生产认证。

## 环境变量

复制 `.env.example` 为 `.env` 后再按需填写本地配置。当前默认使用本地 SQLite，不需要任何真实 AI API key，但 Auth 需要 `AUTH_JWT_SECRET`，敏感字段加密需要 `DATA_ENCRYPTION_KEY`。

```bash
cp .env.example .env
```

仓库只提交 `.env.example`，不会提交 `.env`。

关键变量：

- `DATABASE_URL=sqlite:///./local_data/careeragent.db`：从 `backend/` 启动时写入 `backend/local_data/careeragent.db`，仅允许 local dev/test；`APP_ENV=production` 会拒绝 SQLite。
- `AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars`：本地开发占位 secret；production 环境必须使用至少 32 字符的强随机真实 secret，并通过 secret manager 或部署环境注入。`APP_ENV=production` 会拒绝 dev-only / replace-me / change-me 占位值。
- `DATA_ENCRYPTION_KEY` / `DATA_ENCRYPTION_KEY_ID`：v3.0 Fernet envelope 加密配置；本地可使用 `.env.example` 的 dev-only key，production 必须用 secret manager 注入生产 key 和稳定 key id。`APP_ENV=production` 会拒绝缺失、无效或本地 dev key。
- `AUTH_TOKEN_EXPIRE_MINUTES=60`：access token 过期时间。
- `APP_ENV=production`：启用 runtime fail-fast，要求强 JWT secret、非 SQLite production DB、`DB_ECHO_SQL=false` 和非通配 CORS。
- `DB_POOL_SIZE=5`、`DB_MAX_OVERFLOW=10`、`DB_POOL_TIMEOUT_SECONDS=30`、`DB_ECHO_SQL=false`：PostgreSQL production pool / SQL logging controls。
- `LOCAL_DATA_DIR=local_data`：本地 data/export 目录；readiness 会检查可写性。
- `API_RATE_LIMIT_PER_MINUTE=0`：本地默认关闭；设置为正数时启用进程内基础限流。
- `VITE_API_BASE_URL=http://localhost:8000`：前端 API base URL。
- `AI_PROVIDER_MODE=deterministic`、`LLM_PROVIDER=deterministic`、`EMBEDDING_PROVIDER=local`：默认本地 keyless mode。
- `ENABLE_REAL_LLM=false`、`ENABLE_REAL_EMBEDDING=false`：真实 provider opt-in 开关。
- `LLM_API_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`：OpenAI-compatible LLM provider 配置，默认留空。
- `EMBEDDING_API_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL=local-bow-v1`、`EMBEDDING_DIMENSION=384`：embedding provider 配置。
- `EMBEDDING_PROVIDER_CONFIG_ID=local-bow-default`：非敏感 provider config 标识，用于 embedding metadata/audit。
- `VECTOR_STORE=local`、`RAG_RETRIEVAL_MODE=lexical`：默认 local + lexical，可在本地测试 `vector` / `hybrid` retrieval。
- `RAG_RERANKER_MODE=none`、`RAG_RERANKER_MODEL=local-score-v1`、`RAG_ANSWER_MODE=deterministic_summary`：v3.2 RAG optional reranker / grounded-answer controls；默认不调用真实 provider。

## Demo Flow

本地后端启动并完成 migration 后，可以运行 synthetic seed script：

```bash
python3 scripts/seed_demo_data.py
```

如果 API 地址不同：

```bash
CAREERAGENT_API_BASE_URL=http://localhost:8000 python3 scripts/seed_demo_data.py
```

脚本会注册或登录 synthetic demo account，然后通过受保护 HTTP API 创建 synthetic demo data，包括 resume、JD、match、RAG document、Agent run、Application、Bad Case 和 Evaluation run。Project Optimization 仍建议在前端手动创建 synthetic project facts 并运行 rewrite。

手动演示建议顺序：

1. 打开前端后先注册或登录 synthetic demo account；前端会保存 bearer token 并自动附加到业务 API 请求。
2. Dashboard 查看总览。
3. Resume Center 上传 synthetic resume，运行 Parse，编辑 structured JSON，执行 Risk Check，并保存 confirmed version。
4. Profile Center 创建 synthetic profile 并查看 readiness。
5. Dashboard 查看 profile readiness、resume parse status 和 risk flags count。
6. JD Center 创建 synthetic JD。
7. Project Optimization 创建 synthetic project facts，输入 JD ID 运行 deterministic rewrite。
8. Match Report 运行匹配。
9. Knowledge Base 创建文档、index、search、answer，并复制 grounded Answer Run ID。
10. Interview Center 输入 JD ID、Resume Version ID 和可选 RAG Answer Run ID 生成题目，提交 synthetic answer，并运行 deterministic scoring；回到 Dashboard 查看 Interview Training stats。
11. Study Plan 输入 target role 和可选 RAG Answer Run ID 生成计划，更新 task status；回到 Dashboard 查看 Study Plan stats。
12. Agent Runs 输入 Resume Version、JD、可选 Project IDs / RAG Answer Run IDs，运行 deterministic workflow，查看 final summary 和 linked outputs。
13. Applications 查看 Agent 创建/绑定的 draft，或创建绑定 JD + Resume Version 的手动投递记录；在 board、status history、reflection 和 stats 中检查投递运营状态。
14. Quality Review 创建 Bad Case。
15. Evaluation 运行 `synthetic_smoke_v1`，查看 datasets、run_config、failed cases 和 result detail。
16. 可选运行 `python scripts/run_evals.py --dataset smoke`，查看 `evals/results/smoke` 下生成的 summary、metrics 和 failed cases。

完整流程见 [docs/demo-script.md](docs/demo-script.md)。

## 文档索引

- 当前架构：[docs/current-architecture.md](docs/current-architecture.md)
- API Reference：[docs/api-reference.md](docs/api-reference.md)
- Database Schema：[docs/database-schema.md](docs/database-schema.md)
- Evaluation：[docs/evaluation.md](docs/evaluation.md)
- Real Evaluation Foundation v2.1：[docs/real-evaluation-foundation.md](docs/real-evaluation-foundation.md)
- Real RAG Production Path v2.2：[docs/real-rag-production-path.md](docs/real-rag-production-path.md)
- Real Parser Foundation v2.3：[docs/real-parser-foundation.md](docs/real-parser-foundation.md)
- Trustworthy Match Foundation v2.4：[docs/trustworthy-match-foundation.md](docs/trustworthy-match-foundation.md)
- Agent Workflow Productionization v2.5：[docs/agent-workflow-productionization.md](docs/agent-workflow-productionization.md)
- Security / Privacy / Data Governance v3.0：[docs/security-privacy-deployment-hardening.md](docs/security-privacy-deployment-hardening.md)
- v3.0 Release Notes：[docs/release-notes-v3.0.md](docs/release-notes-v3.0.md)
- Production Deployment Runbook v3.1：[docs/production-deployment-runbook.md](docs/production-deployment-runbook.md)
- Database Operations v3.1：[docs/database-operations.md](docs/database-operations.md)
- Operations Runbook v3.1：[docs/operations-runbook.md](docs/operations-runbook.md)
- Data Governance v3.1：[docs/data-governance.md](docs/data-governance.md)
- Retention / Backup Policy v3.1：[docs/retention-backup-policy.md](docs/retention-backup-policy.md)
- v3.1 Release Notes：[docs/release-notes-v3.1.md](docs/release-notes-v3.1.md)
- Production AI Quality Upgrade v3.2：[docs/production-ai-quality-upgrade.md](docs/production-ai-quality-upgrade.md)
- v3.2 Release Notes：[docs/release-notes-v3.2.md](docs/release-notes-v3.2.md)
- Bad Cases v1.5B/v1.5C：[docs/bad-cases.md](docs/bad-cases.md)
- Safety / Privacy Checklist：[docs/safety-privacy-checklist.md](docs/safety-privacy-checklist.md)
- P1 Production Foundation Release Notes：[docs/release-notes-p1-production-foundation.md](docs/release-notes-p1-production-foundation.md)
- Demo Script：[docs/demo-script.md](docs/demo-script.md)
- Final Acceptance Report：[docs/final-acceptance-report.md](docs/final-acceptance-report.md)
- v0.7 Release Notes：[docs/release-notes-v0.7.md](docs/release-notes-v0.7.md)
- v0.8 Release Notes：[docs/release-notes-v0.8.md](docs/release-notes-v0.8.md)
- v0.9 Release Notes：[docs/release-notes-v0.9.md](docs/release-notes-v0.9.md)
- v1.0 Release Notes：[docs/release-notes-v1.0.md](docs/release-notes-v1.0.md)
- v1.1 Release Notes：[docs/release-notes-v1.1.md](docs/release-notes-v1.1.md)
- v1.2 Release Notes：[docs/release-notes-v1.2.md](docs/release-notes-v1.2.md)
- v1.3 Release Notes：[docs/release-notes-v1.3.md](docs/release-notes-v1.3.md)
- v1.4 Release Notes：[docs/release-notes-v1.4.md](docs/release-notes-v1.4.md)
- v1.5 Release Notes：[docs/release-notes-v1.5.md](docs/release-notes-v1.5.md)

## 当前阶段完成内容

阶段 0 已完成：

- 创建基础目录：`backend/`、`frontend/`、`docs/`、`evals/`、`scripts/`、`local_data/`、`docs/screenshots/`
- 创建根目录文件：`README.md`、`.gitignore`、`.env.example`、`docker-compose.yml`
- 后端初始化：FastAPI 应用、`GET /health`、基础配置、统一错误响应结构
- 前端初始化：React + TypeScript + Vite、Dashboard、Resume Center、JD Center、Match Report、简单导航
- 安全规则：忽略 `.env`、`local_data/`、uploads、vector_index、exports、logs、cache、私有数据目录和本地构建产物
- 不包含真实 LLM API 调用、真实 RAG embedding/vector store、真实 LLM Agent、真实 API Key 或隐私数据

阶段 1A / 1B / 1C 已完成：

- 阶段一 Resume 占位接口：上传校验、列表、详情。
- 阶段一 JD 占位接口：创建、列表、详情、deterministic profile。
- 阶段一 Match 占位接口：运行、列表、详情、deterministic rule score。
- 阶段一前端内存闭环：上传 Resume、创建 JD、运行 Match、展示报告。
- 内存 Mock Store：后端重启后数据会丢失。
- 契约加固：统一成功/错误响应、基础错误路径测试、服务层拆分。
- 最小文本提取：`.md`、`.markdown`、`.txt` 真实读取 UTF-8 文本。
- Parser placeholder：`.pdf`、`.docx` 返回明确 placeholder、extraction status、method 和 warnings，不假装真实解析成功。
- 安全边界：不保存真实上传文件到 Git，不调用真实 LLM/RAG/Agent。

阶段 2A / 2B / 2C / 2D / 2E / 2F / 2G 已完成：

- 2A：完成阶段二持久化与版本管理设计文档。
- 2B：新增 SQLite + SQLAlchemy + Alembic 基础设施、ORM skeleton、初始 migration 和 DB health check。
- 2C：Resume / JD 主路径已切换为 SQLite 持久化，创建 Resume 时生成 initial resume version，创建 JD 时生成 job profile。
- 2D：新增 Resume Version 后端 API，支持版本历史、详情、clone 和 archive；archive 是软归档，不删除历史内容。
- 2E：Match Report 主路径已切换为 SQLite 持久化，报告绑定 `resume_version_id + jd_id`，`GET /api/matches` 返回 DB 历史报告。
- 2F：前端展示 DB-backed Resume / JD / Match 历史；Resume Center 支持 versions 查看、clone 和 archive；Match Report 支持历史查看。
- 2G：补充阶段二验收文档、安全检查说明和 README 收口说明。
- 当前复杂 diff、多版本对比图表、同一 JD 多版本对比页面仍未实现，留到后续阶段。

阶段二验收文档：[docs/phase-2-acceptance.md](docs/phase-2-acceptance.md)

阶段 3A / 3B / 3C / 3D / 3E / 3F / 3G 已完成：

- 3A：完成 RAG 知识库设计文档与边界确认。
- 3B：新增 `rag_documents` / `rag_chunks` ORM models、Alembic migration、schema skeleton 和 DB smoke tests。
- 3C：新增 RAG document create / list / detail、deterministic chunking / indexing backend 和 chunks list API。
- 3D：新增 deterministic lexical retrieval 和 `POST /api/rag/search`，返回 sources / score / snippet / metadata。
- 3E：新增 deterministic RAG answer 和 `POST /api/rag/answer`，有来源时 grounded，无来源时返回 uncertainty。
- 3F：新增 KnowledgeBasePage 最小 UI，支持创建 document、index、查看 chunks、search 和 answer with citations。
- 3G：补充阶段三 RAG 验收文档、synthetic test set 示例、安全检查说明和 README 收口说明。
- 阶段三本身不包含真实 LLM、外部 embedding、production vector store、复杂 RAG evaluation dashboard 或真实 LLM Agent；后续 v1.0 Interview Center 和 v1.1 Study Plan Center 已作为独立 deterministic MVP 完成，阶段 2.2 补充 local vector embedding persistence 和 lexical/vector/hybrid retrieval foundation。
- v1.2 12A：完成 RAG Completion contract tightening，标准化 grounded answer 的 `citations`、`source_refs`、`evidence_summary` 和 `retrieval_debug`；默认仍是 deterministic lexical retrieval，不接真实 LLM、外部 embedding 或 vector DB。
- v1.2 12B：新增 `rag_answer_runs` 表，`POST /api/rag/answer` 默认持久化 answer run contract，并新增 `GET /api/rag/answers` / `GET /api/rag/answers/{answer_run_id}`；answer run 只保存 grounded contract、短 snippet/preview 和 safe retrieval debug，不保存 document raw_text、chunk full text 或完整 interview answer_text。
- v1.2 12C：KnowledgeBasePage 接入 answer run list/detail API，支持按 grounded、uncertainty 和 retrieval mode 筛选 answer history，查看 persisted answer run detail、citations、source_refs preview 和折叠 retrieval_debug；不展示 full raw_text / full chunk text，不做 Interview/Study Plan 深度集成。
- v1.2 12D：新增 `GET /api/rag/stats`，Dashboard 展示 RAG Documents、Indexed Documents、RAG Chunks、Grounded/Ungrounded Answers、Latest RAG Answer 和 Latest RAG Uncertainty；Study Plan / Interview generation 支持可选 `rag_answer_run_ids`，仅将 grounded answer runs 作为 preview-first refs 补充，ungrounded runs 不作为强来源。
- v1.2 12E：新增 `docs/release-notes-v1.2.md`，并完成 README、architecture、API reference、database schema、demo script 和 final acceptance report 最终口径收口。v1.2 deterministic RAG Completion MVP 已完成；真实 LLM、外部 embedding/vector DB、RAG evaluation dashboard 和自动写入 workflow 仍未完成。

阶段三设计文档：[docs/rag-design.md](docs/rag-design.md)

阶段三验收文档：[docs/phase-3-rag-acceptance.md](docs/phase-3-rag-acceptance.md)

阶段 4A / 4B / 4C / 4D / 4E / 4F 已完成：

- 4A：完成 Agent Workflow 设计文档与边界确认。
- 4B：新增 `agent_runs` / `agent_steps` ORM models、Alembic migration、schema skeleton 和 DB infrastructure tests。
- 4C：新增 deterministic workflow runner、fixed workflow `job_application_preparation`、step execution、`need_more_info`、failed behavior 和 step timeline persistence。
- 4D：新增 Agent Runs API，支持 create run、list runs、run detail 和 steps timeline。
- 4E：新增 AgentRunsPage 最小 UI，支持创建 deterministic workflow run、查看 runs list、run detail 和 steps timeline。
- 4F：补充阶段四验收文档、安全检查说明和 README 收口说明。
- 当前 Agent Workflow 是 deterministic state machine，不是真实 LLM Agent，不是自由聊天 Agent，不自动投递。

阶段四设计文档：[docs/agent-workflow-design.md](docs/agent-workflow-design.md)

阶段四验收文档：[docs/phase-4-agent-workflow-acceptance.md](docs/phase-4-agent-workflow-acceptance.md)

v1.3 Agent Workflow Baseline + Application Linkage 已完成：

- `job_application_preparation` 扩展为 11 步 deterministic workflow：validate inputs、load resume、load JD、run match、optional RAG search、RAG context summary、project rewrites、interview question generation、study plan generation、application create/link 和 final summary。
- `project_ids` 可显式传入；未传时按 `resume_version_id` 自动发现 active projects，未找到则跳过 project rewrite。
- `rag_answer_run_ids` 可传给 Interview / Study Plan generation；只使用 grounded answer run refs。
- `application_id` 可绑定已有投递记录；未传且 `create_application=true` 时创建 saved draft application，并写入 `applications.agent_run_id`。
- AgentRunsPage 支持新增 refs 输入和 final summary 展示；ApplicationTrackerPage 支持 `agent_run_id` 创建、展示和筛选；Dashboard 展示 latest agent run status/score 和 linked application 摘要。
- 仍不接真实 LLM、不做自由聊天 Agent、不自动投递、不接招聘网站、不自动修改简历/项目/面试答案/学习计划状态。

阶段 2.5 已在 v1.3 baseline 上补齐 Agent Workflow production foundation：

- 新增 `interview_preparation`、`application_review`、`study_gap_planning` 固定 workflow。
- Run status 覆盖 `pending`、`running`、`completed`、`failed`、`need_more_info`、`cancelled`、`retrying`。
- 新增 resume/retry/cancel API，retry/resume 通过 `attempt` 追加 step timeline，不覆盖旧步骤。
- Run/step 保存 `run_config`、`privacy_safe_payload`、`final_output_ref`、`retry_attempt` 和失败 Bad Case draft payload。
- Agent service-level eval 扩展到 8 cases，覆盖 success、need_more_info、resume、retry、cancel、Bad Case payload 和多 workflow。
- 仍是同步 deterministic foundation，不是 durable production workflow engine，也不是真实 LLM tool-calling agent。

Quality Review / Bad Case 原型已完成：

- 完成 Quality Review / Bad Case 设计文档与边界确认。
- 新增 `bad_cases` ORM model、Alembic migration、schema skeleton 和 DB infrastructure tests。
- 新增 Bad Case repository / service / API 和 tests，支持 create、list、filter、detail、patch。
- 新增 QualityReviewPage 最小 UI，支持人工创建、筛选、查看和更新 bad case。
- 新增 MarkBadCasePanel，并在 Match / Knowledge Base / Agent Runs 页面加入轻量 Mark as bad case 入口。
- 补充 Quality Review 验收文档、安全检查说明和 README 收口说明。
- 当前 Quality Review 是人工 review record，不是真实 LLM reviewer，不做自动评估、不做自动投递、不做 Evaluation Center。

Quality Review 设计文档：[docs/quality-review-design.md](docs/quality-review-design.md)

Quality Review 验收文档：[docs/phase-5-quality-review-acceptance.md](docs/phase-5-quality-review-acceptance.md)

阶段五 / v1.4：Application Management / Product Operations Hardening 已完成：

- `applications` 已补强运营字段：source URL、location、priority、notes、interview question refs、last contact date。
- 投递记录必须绑定 `jd_id` 和 `resume_version_id`；`match_report_id` 和 `agent_run_id` 仍为可选 linkage，传入时会校验 refs。
- 新增 `application_status_history`，创建时写入初始状态，状态变更写 history，非状态字段 patch 不重复写 history。
- 新增 reflection API，支持维护 interview feedback、failure reason、preparation gaps、next actions 和 weakness tags；不自动写 Bad Case。
- ApplicationTrackerPage 支持 Application Board、filters、detail edit、status history 和 reflection。
- Dashboard 已接入 enhanced application stats，展示 total、active、interview、offer、rejected、upcoming、overdue、conversion 和 latest applications。
- 当前只做手动 tracking，不自动投递、不接招聘网站、不接真实 LLM，不保存简历原文或 JD 原文到投递 API 响应。

投递管理设计文档：[docs/application-management-design.md](docs/application-management-design.md)

阶段六 / v1.5B：Deterministic Evaluation Regression Foundation 已完成：

- 新增 `evaluation_runs` / `evaluation_cases` / `evaluation_results` ORM models、Alembic migration、schema、repository、service、API 和 tests。
- 内置 `synthetic_smoke_v1` 已扩展到 JD Parser、Resume Parser、Match、RAG、Agent、Application 和 Bad Case 的确定性 contract 检查。
- 新增文件化 smoke fixtures：`evals/datasets/smoke`、`evals/expected/smoke` 和 `scripts/run_evals.py`。
- 新增 EvaluationPage datasets、run_config、failed cases 和 result detail 展示。
- Evaluation Case 可选关联 `bad_case_id`，Bad Case 可通过 `/api/bad-cases/{bad_case_id}/add-to-eval` 加入 `regression` eval set。
- Bad Case 增加 root cause、fix strategy、tags、added-to-eval、verified 和 regression run/case linkage。
- Dashboard 已接入 evaluation stats，展示 run 数、最新 pass rate 和失败结果数量。
- 当前评测目标是回归和质量追踪，不是给模型能力打最终分；不接真实 LLM judge，不做多模型对比，不做大型评测平台。

评测体系设计文档：[docs/evaluation-design.md](docs/evaluation-design.md)

阶段六 / v1.5C：Privacy / Security / Data Governance 已完成：

- 新增 `app.core.privacy`，提供 `safe_preview`、`redact_text` 和 `redact_mapping`，用于日志/调试数据 redaction，mask email、phone、API key/token/secret，并用 length/hash/preview 替代长文本。
- 新增统一版本常量：`PROMPT_VERSION`、`SCHEMA_VERSION`、`RETRIEVAL_VERSION`、`MODEL_VERSION`、`EVALUATION_VERSION`，并写入 RAG retrieval debug、Agent final summary、Evaluation `run_config` 和 fileized eval metrics。
- 新增删除/归档 API：`DELETE /api/resumes/{resume_id}`、`DELETE /api/jobs/{jd_id}`、`DELETE /api/applications/{application_id}`、`DELETE /api/rag/documents/{doc_id}`。Resume/JD/Application 使用软删除或归档策略；RAG document 删除会移除 chunks，历史 answer runs 只保留安全 refs。
- Resume/JD/RAG preview 统一收敛为短 preview 并 mask secret；默认 list/detail 响应不返回 full `raw_text`、full chunk text、full answer text 或 API key。
- ResumeCenterPage、JDCenterPage、ApplicationTrackerPage 和 KnowledgeBasePage 已加入确认式删除/归档入口；Application 默认列表和 stats 不包含 archived 记录，可通过 `status=archived` 显式查看。

v1.5C 当时不新增真实 LLM、embedding/vector DB、pgvector、自动投递、招聘网站集成、完整生产级权限体系或完整隐私删除证明；P1 后已补基础 token auth、workspace scope 和 data isolation。

v1.0 Interview Center 10A/10B/10C/10D 题目生成、答案提交、答案评分、前端页面和 Dashboard training stats 已完成：

- 新增 `interview_questions` / `interview_answers` ORM models 和 Alembic migration。
- 新增 `POST /api/interviews/questions/generate`，基于 JD profile、structured resume、可选 project facts 和 project rewrite 结果生成 deterministic interview questions。
- 新增 `GET /api/interviews/questions`，支持按 `jd_id`、`resume_version_id`、`project_id`、`question_type` 和 `difficulty` 筛选。
- 每个问题保存 `source_refs`，只包含 `source_type`、`source_id`、`field`、`label` 和短 `preview`，不返回 Resume/JD full raw_text。
- 新增 `POST /api/interviews/answers`、`GET /api/interviews/answers` 和 `POST /api/interviews/answers/{answer_id}/score`。
- Answer API 默认只返回 `answer_text_preview`；完整 `answer_text` 仅保存在本地 DB，用于 deterministic scoring。
- Scoring 输出 `structure`、`technical_depth`、`business_understanding`、`evidence`、`clarity`、`risk_control`、`overall_average`、`feedback` 和 `weakness_tags`。
- 新增 InterviewCenterPage，支持生成 questions、筛选 / 选择 question、提交 answer preview-first response、查看 answer list，并对 selected answer 运行 deterministic scoring。
- 新增 `GET /api/interviews/stats` 和 Dashboard Interview Training stats，展示 question count、answer count、scored answer count、latest average score 和 latest weakness tags。
- v1.0 final handoff 已补充 release notes、验收说明和安全边界。当时的 Study Plan 写入、RAG completion 和 Agent workflow 已在后续 v1.1 / v1.2 / v1.3 deterministic MVP 中推进；LLM judge 仍未实现。

v1.1 Study Plan Center 11A/11B/11C/11D 已完成：

- 新增 `study_plans` ORM model 和 Alembic migration。
- 新增 `POST /api/study-plans/generate`，从 `target_role`、Profile target_roles / skill_map、Match gaps / rewrite_priorities、Project Rewrite missing_points / evidence_required、Interview weakness_tags 和 request weakness_tags 生成 deterministic study plan。
- `phases` JSON 包含 phase、goal、tasks、resources、deliverables 和 acceptance_criteria；每个 task 包含稳定 `task_id`、source_gap、priority、status、acceptance_criteria、evidence_required 和 source_refs。
- `source_refs` 只保存 `source_type`、`source_id`、`field`、`label` 和短 `preview`，不复制 Resume/JD full raw_text 或完整 `answer_text`。
- 新增 `GET /api/study-plans`、`GET /api/study-plans/{study_plan_id}`、`PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}` 和 `GET /api/study-plans/stats`。
- Task status 支持 `todo`、`in_progress`、`done`、`blocked`、`skipped`，更新 JSON phases 时会刷新 plan `updated_at`，不自动修改 plan status。
- Stats 基于 `study_plans.phases` 聚合 plan count 和 task status count，不返回 source_refs、Resume/JD raw_text 或完整 `answer_text`。
- 新增 `frontend/src/api/studyPlans.ts`、Study Plan TypeScript types 和 StudyPlanPage，支持 generate、list/filter、detail、source_refs preview 展示、phase/task 展示和 task status update。
- Dashboard 接入 `GET /api/study-plans/stats`，展示 Study Plans、Active Study Plans、Pending Tasks、Blocked Tasks、Done Tasks、Latest Study Target 和 In Progress Tasks 摘要。
- Study Plan 模块不接真实 LLM，不接外部学习平台 API、日历提醒或自动修改简历/项目/面试答案；v1.2 12D 已补 optional grounded RAG answer run refs，v1.3 Agent Workflow 可调用 Study Plan generation，但不自动修改下游模块。

## API

`GET /health`、`POST /api/auth/register` 和 `POST /api/auth/login` 为公开入口；`GET /api/auth/me`、`POST /api/auth/logout` 以及其他 `/api/*` 工作台 API 默认需要 `Authorization: Bearer <access_token>`。后端按 token 中的 user/workspace scope 过滤 owned data。

当前工作台 API：

```text
GET /health
POST /api/auth/register
POST /api/auth/login
GET /api/auth/me
POST /api/auth/logout
GET /api/db/health
POST /api/profiles
GET /api/profiles
GET /api/profiles/{profile_id}
PATCH /api/profiles/{profile_id}
GET /api/profiles/{profile_id}/summary
POST /api/projects
GET /api/projects
GET /api/projects/{project_id}
PATCH /api/projects/{project_id}
POST /api/projects/{project_id}/rewrite
GET /api/project-rewrites/{rewrite_id}
POST /api/resumes/upload
POST /api/resumes/{resume_id}/parse
POST /api/resumes/{resume_id}/risk-check
POST /api/resumes/{resume_id}/versions
GET /api/resumes
GET /api/resumes/{resume_id}
DELETE /api/resumes/{resume_id}
GET /api/resumes/{resume_id}/versions
GET /api/resume-versions/{version_id}
POST /api/resume-versions/{version_id}/clone
PATCH /api/resume-versions/{version_id}/archive
POST /api/jobs
GET /api/jobs
GET /api/jobs/{jd_id}
DELETE /api/jobs/{jd_id}
POST /api/matches/run
GET /api/matches
GET /api/matches?jd_id={jd_id}
GET /api/matches?resume_version_id={resume_version_id}
GET /api/matches/{match_report_id}
POST /api/interviews/questions/generate
GET /api/interviews/questions
POST /api/interviews/answers
GET /api/interviews/answers
POST /api/interviews/answers/{answer_id}/score
GET /api/interviews/stats
POST /api/study-plans/generate
GET /api/study-plans
GET /api/study-plans/{study_plan_id}
PATCH /api/study-plans/{study_plan_id}/tasks/{task_id}
GET /api/study-plans/stats
POST /api/rag/documents
GET /api/rag/documents
GET /api/rag/documents/{doc_id}
DELETE /api/rag/documents/{doc_id}
POST /api/rag/documents/{doc_id}/index
GET /api/rag/chunks
POST /api/rag/search
POST /api/rag/answer
GET /api/rag/answers
GET /api/rag/answers/{answer_run_id}
GET /api/rag/stats
POST /api/agents/runs
GET /api/agents/runs
GET /api/agents/runs/{run_id}
GET /api/agents/runs/{run_id}/steps
POST /api/applications
GET /api/applications
GET /api/applications?status={status}
GET /api/applications?company={company}
GET /api/applications?role_category={role_category}
GET /api/applications?resume_version_id={resume_version_id}
GET /api/applications?jd_id={jd_id}
GET /api/applications?match_report_id={match_report_id}
GET /api/applications?agent_run_id={agent_run_id}
GET /api/applications?priority={priority}
GET /api/applications/{application_id}
PATCH /api/applications/{application_id}
DELETE /api/applications/{application_id}
POST /api/applications/{application_id}/reflection
GET /api/applications/{application_id}/status-history
GET /api/applications/stats
POST /api/evaluations/runs
GET /api/evaluations/runs
GET /api/evaluations/runs/{run_id}
GET /api/evaluations/runs/{run_id}/results
GET /api/evaluations/cases
POST /api/evaluations/cases
POST /api/evaluations/cases/from-bad-case/{case_id}
GET /api/evaluations/datasets
GET /api/evaluations/stats
GET /api/privacy/export
DELETE /api/privacy/delete-all
GET /api/privacy/audit-log
GET /api/bad-cases/stats
POST /api/bad-cases/{bad_case_id}/add-to-eval
POST /api/evaluations/bad-cases
GET /api/evaluations/bad-cases
GET /api/evaluations/bad-cases/{bad_case_id}
PATCH /api/evaluations/bad-cases/{bad_case_id}
```

成功响应结构：

```json
{
  "data": {
    "status": "ok",
    "service": "CareerAgent API",
    "environment": "development"
  },
  "request_id": "..."
}
```

错误响应结构：

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

### 手动跑通 v0.9 Project Optimization

1. 启动后端和前端。
2. 打开 `http://localhost:5173`。
3. 进入 Resume Center，上传 `.pdf`、`.docx`、`.md`、`.markdown` 或 `.txt` synthetic resume，确认 raw text preview 展示真实提取文本。
4. 点击 `Parse selected resume`，编辑 structured resume JSON，点击 `Run risk check`，再填写 version name / target role 并保存 confirmed version。
5. 进入 Profile Center，创建 synthetic profile，确认 readiness summary 展示 completeness。
6. 回到 Dashboard，确认 profile readiness、resume parse status 和 risk flags count 已展示。
7. 进入 JD Center，填写 company、job title、location 和 raw JD text，创建 JD。
8. 进入 Project Optimization，创建 synthetic project facts，输入 JD ID，运行 deterministic rewrite，查看 matched points、missing points、evidence required、rewritten bullets、forbidden changes 和 risk flags。
9. 进入 Match Report，点击 `Run Match`。
10. 查看总分、维度分、evidence、gaps 和 rewrite priorities。

PDF / DOCX / Markdown / txt 返回结果会包含：

- `extraction_status`: `extracted`
- `extraction_method`: `pymupdf_text`、`python_docx_text`、`utf8_md_decode`、`utf8_markdown_decode` 或 `utf8_txt_decode`
- `raw_text_preview`: 真实读取到的文本预览

PDF / DOCX 只做文本层提取，不做 OCR。扫描版 PDF、图片简历或复杂版式可能无法完整抽取文本。

当前阶段说明：

- Profile Center：支持 profiles 表、Profile API、ProfilePage 和 Dashboard readiness summary；P1 后 profile 按当前 user/workspace scope 读写，仍不自动从简历生成画像。
- Project Optimization：支持 `projects` / `project_rewrites` 表、Project CRUD API、2.4 trustworthy deterministic Project Rewrite API、ProjectOptimizationPage 和 Dashboard project readiness 摘要，用于保存项目事实并展示基于现有 facts 的 rewrite suggestions；每条 rewritten bullet 带 before/after/reason/evidence_required/forbidden_changes/matched_jd_requirements/missing_points/risk_level/confidence。当前不接真实 LLM，不自动写回 Resume Version，不编造项目经历、数字、公司、技术栈、上线状态或业务规模。
- Parser：JD / Resume 已具备 parser production foundation，输出 evidence、confidence、warnings、risk flags 和 parser metadata；默认仍是 local deterministic parser，optional LLM path 需显式开启。
- Risk-check：当前只做可确定规则检测，不是事实审计，不自动修改简历。
- SQLite 持久化：Resume / JD 数据默认保存到 `DATABASE_URL` 指定位置，默认 `local_data/careeragent.db`。
- Match Report 持久化：报告默认绑定 `resume_version_id + jd_id`，并保存到 SQLite；2.4 后包含六维评分、维度 evidence、risk deduction、score_breakdown、recommended_projects、scoring_method/confidence，并支持 `/api/matches/compare`。
- 版本管理：Resume Version 已支持历史查询、详情、clone 和 archive；archive 是软归档，不删除历史内容。
- 前端展示：Resume Center 可查看 versions、clone、archive、parse、risk-check 和保存 confirmed version；Match Report 可查看 DB 历史和详情。
- 版本边界：后端已支持同一 JD 多 resume versions / 同一 resume version 多 JDs 的 compare API；复杂版本 diff / compare UI 仍未实现。
- 无真实 LLM：没有 OpenAI、DeepSeek、Qwen 或其他模型调用。
- RAG 知识库：支持 document 管理、chunking/indexing、lexical/vector/hybrid search、DB-persisted local vectors、deterministic answer with citations/source_refs/retrieval_debug、grounded answer run persistence、KnowledgeBasePage answer history/detail、Dashboard RAG stats，以及 Study Plan / Interview generation 的可选 grounded answer run refs。
- RAG 边界：阶段 2.2 是 real RAG production foundation，v3.2 补充 semantic provider metadata、reranker contract、optional LLM grounded answer 和 synthetic benchmark foundation；local/offline vectorizer 不是最终 semantic embedding，SQLite JSON vector 不是 production-scale vector DB，FAISS/pgvector application path、真实 provider benchmark、人审 groundedness 和自动写入 Interview/Study Plan/Resume/Project/Application 的深度集成仍未生产认证。
- Agent Workflow：支持 2.5 deterministic workflow production foundation，包括 `job_application_preparation`、`interview_preparation`、`application_review`、`study_gap_planning`、Agent Runs API、resume/retry/cancel、attempt-aware step timeline、RAG context summary、failure Bad Case draft、run_config、privacy-safe payload 和 `final_summary`，可创建/绑定 Application tracking record。
- Agent 边界：没有真实 LLM Agent、自由聊天 Agent 或 true tool-calling Agent；Agent Workflow 仍是同步 local runner，不自动投递、不接招聘网站、不自动修改简历/项目/面试答案/学习计划任务状态，也不代表 durable production workflow engine。
- Quality Review：支持 `bad_cases` 持久化、Bad Case API、QualityReviewPage 和 Mark as bad case 入口。
- Quality Review 边界：当前是人工 review record，不是真实 LLM reviewer，不做自动评估、不做自动投递、不做 Evaluation Center。
- Application Management：支持手动投递 tracking、JD/Resume 强绑定、status history、reflection、Application Board、enhanced stats、`match_report_id` / `agent_run_id` linkage 和 ApplicationTrackerPage。
- Interview Center：支持 question generation、answer submit/list、deterministic scoring、InterviewCenterPage 和 Dashboard interview training stats；不接真实 LLM judge，不自动写入 Study Plan。
- Study Plan Center：11A/11B/11C/11D 支持后端 `study_plans` 持久化、deterministic generate API、list/detail、task status update、stats API、frontend API wrapper、StudyPlanPage 和 Dashboard study stats；v1.2 12D 可选接收 grounded RAG answer run refs 作为学习/证据引用，v1.3 Agent Workflow 可调用 generation。当前不接真实 LLM，不接外部学习平台或日历提醒，也不自动修改简历/项目/面试答案。
- Application 边界：不自动投递、不接招聘网站、不保存完整投递材料、不自动状态流转；状态历史只记录手动更新。
- Evaluation：支持 deterministic `synthetic_smoke_v1` contract regression、`service_level` 脱敏 service-level runner、evaluation runs / cases / results 持久化、EvaluationPage 和 Bad Case 可选关联。
- Evaluation 边界：service-level eval 会真实调用当前 foundation service，但不接真实 LLM judge，不做多模型对比，不做大型评测平台，不把评测结果当作模型能力最终评分。
- v3.1 边界：Security / Privacy / Data Governance 和 Production Deployment / Database / Operations 已达到 production foundation candidate；下一阶段应优先进入 v3.2 Production AI Quality Upgrade。当前仍不是 production-ready，Agent 仍缺 durable worker/queue/heartbeat、真实 LLM planning/tool-calling 和生产级 workflow observability，AI 核心能力仍缺 semantic provider、大样本评测和 human agreement。

## 安全与隐私

- 不提交 `.env`、真实 API Key 或任何私密凭据。
- 不提交真实简历、真实 JD、投递记录、面试复盘、上传文件、向量索引、导出文件、日志和缓存。
- `local_data/` 仅用于本地运行数据，并已加入 `.gitignore`。
- 开发执行手册只作为上下文使用，不复制、不移动、不提交到仓库。
- RAG 测试和验收只使用 synthetic data；前端默认展示 preview / snippet，不默认展示完整 raw_text 或完整 chunk text。
- RAG answer 的 `citations.snippet` 和 `source_refs.preview` 只使用短 snippet；`retrieval_debug` 只包含 retrieval_mode、embedding_provider、embedding_model、vector_index_used、query_tokens、candidate_count、selected_chunk_ids、scores、top_k、filters、score_threshold 和 insufficient_reason，不包含 full raw_text、chunk text 或完整 answer_text。
- `rag_answer_runs` 只保存 grounded answer contract、短 citations/source_refs 和 safe retrieval debug；不复制 RAG document `raw_text`、chunk full text、Resume/JD raw_text 或完整 interview `answer_text`。
- `GET /api/rag/stats` 只返回 document/chunk/answer run 聚合计数和 latest question preview/uncertainty，不返回 citations、source_refs、retrieval_debug、raw_text 或完整 answer。
- v3.0 repository/service 写入路径会把 Resume/JD raw_text、RAG raw_text/chunk/answer-run private fields、Interview answers、Application notes/reflection/status notes 和 Bad Case free text 保存为 Fernet envelope；legacy plaintext rows 仍可读。
- Resume / JD / RAG 默认 API response 和 UI 只返回 / 展示 `raw_text_preview`、`text_preview`、snippet 或 refs，不暴露完整 raw_text。
- KMS/rotation backfill、automated backup erasure proof、集中审计和合规证明仍是 production blockers；v3.1 已补 retention/backup policy 和脚本基础，但不等于自动 purge attestation。
- Agent step payload 只保存 IDs、refs 和 short metadata，不保存完整 resume raw_text、JD raw_text 或 RAG chunk text。
- Agent final summary 只保存 match score、短 strengths/gaps、next actions 和 created record IDs，不保存隐私原文。
- AgentRunsPage 使用 safe JSON render helper 过滤敏感字段，避免展示隐私原文。
- Bad Case 只保存 `source_type` / `source_id` 和问题摘要，不自动复制 Resume / JD / RAG chunk / Agent refs 原文。
- Application API 只保存投递状态、refs、日期、摘要备注和可选 `agent_run_id`，不复制 Resume raw_text、JD raw_text、Match 源对象全文或 Agent step payload。
- Profile API 只保存目标岗位、地点、行业、技能结构、偏好和可选 resume version ref，不复制 Resume raw_text。
- Profile 不应保存身份证、详细住址、政治、健康等敏感身份信息；P1 后 `user_id` / `workspace_id` 由认证上下文写入和过滤，旧本地数据仍可能带有默认 owner。
- Project facts 只应保存用户确认的 synthetic 或可公开复述项目事实，不应粘贴真实公司私密信息、敏感商业数据或大段内部材料。
- Project Rewrite 只基于已有 project facts 生成建议；不自动写回 Resume Version，不编造公司、用户量、收益、准确率、上线状态、业务规模或技术栈。
- Interview Question generation 只基于 JD profile、structured resume、project facts、project rewrite refs 和 v1.2 12D 可选 grounded RAG answer run refs；不读取或返回 Resume/JD full raw_text，不诱导编造上线、收益、用户量、准确率或公司经历。Ungrounded RAG answer runs 只产生 warning，不作为可靠来源。
- Interview Answer submit / scoring 只默认返回 `answer_text_preview`、scores、feedback 和 `weakness_tags`；完整 `answer_text` 仅保存在本地 DB 用于 deterministic scoring，不进入默认 API payload、Dashboard 或 stats。Dashboard interview stats 只读取聚合计数、latest average score 和 latest weakness tags，不展示完整回答原文。
- Study Plan generation 只保存结构化 `source_refs`、phases 和 tasks；`source_refs` 只允许短 preview 和引用 ID，不保存 Resume/JD full raw_text、完整 `answer_text` 或 RAG full chunk text。v1.2 12D 可选 grounded RAG answer run refs 只生成学习/证据复核任务；ungrounded runs 只记录 uncertainty ref，不作为强来源。生成任务只建议补证据、补学习或审计 claim，不自动修改简历、项目或面试答案。
- Evaluation Case 只保存 synthetic payload、结构化 refs 或摘要字段；从 Bad Case 创建 case 时不复制源对象 raw_text。

## v1.0 验收结果

2026-06-25 在 `main` 执行：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：216 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `docker compose config`：通过。
- `python3 -m py_compile scripts/seed_demo_data.py`：通过。
- `git diff --check`：通过。
- `docker compose build`：未完成，原因是本机 Docker daemon/socket 不可用，不是代码构建失败；`docker compose config` 已通过。

## v1.1 验收结果

2026-06-25 在 `main` 执行：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：237 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `docker compose config`：通过。
- `python3 -m py_compile scripts/seed_demo_data.py`：通过。
- `git diff --check`：通过。
- `docker compose build`：未完成，原因是本机 Docker daemon/socket 不可用，不是代码构建失败；`docker compose config` 已通过。

v1.1 Study Plan Center deterministic MVP 已完成；v1.2 12D 已补 optional grounded RAG answer run refs；v1.3 已补 deterministic Agent Workflow baseline；2.5 已补 Agent Workflow production foundation。真实 LLM、深度 RAG workflow、durable workflow engine、外部学习平台、日历提醒和完整生产级多租户权限体系仍未完成。

## v1.2 验收结果

2026-06-25 在 `main` 执行：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：251 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `docker compose config`：通过。
- `python3 -m py_compile scripts/seed_demo_data.py`：通过。
- `git diff --check`：通过。
- `docker compose build`：未完成，原因是本机 Docker daemon/socket 不可用，不是代码构建失败；`docker compose config` 已通过。

v1.2 RAG Completion deterministic MVP 已完成；v1.3 Agent Workflow Baseline + Application Linkage 已完成；2.5 Agent Workflow production foundation 已完成；2.6 Security / Privacy / Deployment production foundation 已完成；v3.0 Security / Privacy / Data Governance production foundation candidate 已完成；v1.4 Product Operations / Application Management hardening 已完成；v1.5B Bad Case + Evaluation Regression Foundation 已完成；v1.5C Privacy / Security / Data Governance controls 已完成；v1.6 Production AI & Deployment Readiness baseline 已完成。真实 LLM answer / judge、外部 embedding / vector DB / reranker、durable workflow engine、RAG evaluation dashboard、自动投递、KMS/rotation backfill、备份擦除证明和生产部署 runbook 仍未完成。

## v1.3 验收结果

2026-06-30 在当前工作树执行：

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests`：252 passed, 6 warnings。
- `cd frontend && npm run build`：通过。
- `PYTHONPATH=backend DATABASE_URL=sqlite:////tmp/careeragent_v13_alembic_check.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head`：通过。
- `backend/.venv/bin/python -m py_compile scripts/seed_demo_data.py`：通过。
- `docker compose config`：通过。
- `git diff --check`：通过。
- `docker compose build`：本轮未执行；Docker image build 仍需在 Docker daemon 可用环境补跑。

v1.4 Product Operations / Application Management hardening 已完成；v1.5B Bad Case + Evaluation Regression Foundation 已完成；v1.5C Privacy / Security / Data Governance controls 已完成；真实 LLM Agent、自由聊天 Agent、自动投递、招聘网站集成、自动状态流转和完整生产级多租户权限体系仍未完成。

## 自查命令

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose config
PYTHONPATH=backend DATABASE_URL=sqlite:////tmp/careeragent_alembic_check.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
git status --short --branch
git diff --check
```

## 后续阶段规划

1. 阶段一：最小可运行闭环，跑通简历上传、JD 输入、解析、匹配评分和报告展示。
2. 阶段二：数据持久化与版本管理，引入数据库、简历版本、JD 历史和匹配报告历史。
   - 设计文档：[docs/phase-2-persistence-design.md](docs/phase-2-persistence-design.md)
   - 验收文档：[docs/phase-2-acceptance.md](docs/phase-2-acceptance.md)
   - Release notes：[docs/release-notes-v0.2.0-persistence.md](docs/release-notes-v0.2.0-persistence.md)
3. 阶段三：RAG 知识库，建立 RAG document、chunk、metadata、lexical search、deterministic answer 和来源引用。
   - 设计文档：[docs/rag-design.md](docs/rag-design.md)
   - 验收文档：[docs/phase-3-rag-acceptance.md](docs/phase-3-rag-acceptance.md)
   - Release notes：[docs/release-notes-v0.3.0-rag.md](docs/release-notes-v0.3.0-rag.md)
4. 阶段四 / v1.3：Agent Workflow，用 deterministic state machine 串联 Resume / JD / Match / RAG / Project Rewrite / Interview / Study Plan / Application，并提供 Agent Runs API、AgentRunsPage 和 application linkage。
   - 设计文档：[docs/agent-workflow-design.md](docs/agent-workflow-design.md)
   - 验收文档：[docs/phase-4-agent-workflow-acceptance.md](docs/phase-4-agent-workflow-acceptance.md)
   - Release notes：[docs/release-notes-v0.4.0-agent-workflow.md](docs/release-notes-v0.4.0-agent-workflow.md)
5. 阶段五 / v1.4：Application Management / 手动投递管理与 Dashboard，当前已具备运营硬化能力：JD + Resume Version 强绑定、Match / Agent 可选 linkage、状态历史、reflection、priority、next-step stats 和 conversion stats；该阶段只做 tracking，不做自动投递，不接招聘网站，不自动提交申请。
   - 设计文档：[docs/application-management-design.md](docs/application-management-design.md)
6. 阶段六 / v1.5：评测体系、Bad Case 与 Privacy / Security / Data Governance，当前已具备 deterministic evaluation regression foundation、redaction helpers、delete/archive APIs、version metadata tracking 和 privacy-safe frontend controls；P1 已补 token auth、workspace scope 和基础 data isolation，后续仍需生产级 RBAC、SSO、审计、retention 和治理流程。
   - 设计文档：[docs/evaluation-design.md](docs/evaluation-design.md)
   - Quality Review 设计文档：[docs/quality-review-design.md](docs/quality-review-design.md)
   - Quality Review 验收文档：[docs/phase-5-quality-review-acceptance.md](docs/phase-5-quality-review-acceptance.md)
   - Quality Review release notes：[docs/release-notes-v0.5.0-quality-review.md](docs/release-notes-v0.5.0-quality-review.md)
7. 阶段七：工程化交付，补齐 Docker、文档、演示材料、安全说明和最终验收记录。
