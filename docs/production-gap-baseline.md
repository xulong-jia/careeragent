# CareerAgent Production Gap Baseline

v3.0 后，当前仓库是 production hardening + real evaluation + real RAG + real parser + trustworthy match/project rewrite + agent workflow + security/privacy/data-governance production foundation candidate。本文档不声明 production-ready。

## 1. 当前总体判断

当前版本可以作为 production hardening + real evaluation + real RAG + real parser + trustworthy match/project rewrite + agent workflow + security/privacy/data-governance production foundation candidate，因为主业务对象已经有持久化、Auth/Workspace 基础隔离、隐私 preview 收敛、Docker 本地骨架、Alembic migration、后端测试、前端 build、synthetic smoke regression、service-level evaluation runner、RAG local vector embedding persistence、JD/Resume parser evidence/confidence/warnings baseline、Match 六维评分、风险扣分、compare API、Project Rewrite 反编造字段、Agent run lifecycle、attempt-aware step timeline、resume/retry/cancel API、多 workflow 和失败 Bad Case draft，以及 2.6 runtime config validation、structured request logging、readiness check、privacy deletion proof/audit foundation；v3.0 进一步补齐应用层 sensitive field encryption、data encryption key validation、token revoke、route-level RBAC、dry-run/execute deletion proof 和更严格 audit/eval redaction。

当前版本不是 production-ready，原因是核心 AI 能力仍大量依赖 deterministic、synthetic 或本地 foundation 路径：RAG 已有 local vector path 和 DB-persisted chunk vectors，但没有最终 semantic embedding、reranker 或 production-scale vector DB；JD/Resume parser 已有 production foundation 字段和 optional LLM path，但默认仍是 deterministic local parser，未接 OCR、未做大规模真实 benchmark；Match/Rewrite 已有六维评分、证据绑定、风险扣分和防编造字段，但仍是 deterministic foundation，未经过大规模 human agreement / ranking stability 校准；Agent 已有 production foundation 状态机和恢复 API，但仍是同步 local runner，不是 durable queue/worker/LLM tool-calling agent；Evaluation 仍只是 foundation benchmark；安全侧仍缺 KMS/多 key 解密/rotation backfill、refresh token、SSO/MFA、DB RLS、集中 SIEM、backup purge proof 和 production deployment runbook。

完成标准口径：mock、stub、deterministic、synthetic、prototype、本地可演示、骨架完整都不能标为 DONE，只能标为 PARTIAL、FOUNDATION、MOCK_ONLY、DETERMINISTIC_ONLY、SYNTHETIC_ONLY 或 RISKY。

## 2. 模块状态矩阵

| 模块 | 状态 | 当前已有能力 | Production 缺口 | 下一阶段归属 | 主要风险 |
| --- | --- | --- | --- | --- | --- |
| Profile | PARTIAL | Profile CRUD、readiness summary、workspace scope | 仍是人工画像，不自动从可信证据生成；缺少生产级 profile audit | 2.6 / future profile audit | 用户画像与简历/JD 证据不一致 |
| Resume | FOUNDATION | PDF/DOCX/MD/txt 文本层提取、version、parser evidence/confidence/warnings、risk flags、optional LLM fallback path；v3.0 raw_text 应用层加密 | 默认仍是 deterministic local parser；无 OCR、大规模 benchmark、复杂 PDF/table resume production path；无 KMS/rotation backfill | 2.3 foundation, v3.0 | parser 误读、key 管理风险 |
| JD | FOUNDATION | 创建 JD、required/preferred、role category、responsibilities、business scenarios、hidden requirements、evidence/confidence/warnings、parser metadata | 默认仍是 deterministic local parser；真实 LLM parser calibration 和大样本 benchmark 不足 | 2.3 foundation | JD 理解仍需真实样本验证 |
| Match | FOUNDATION | 六维评分、维度 evidence、score_breakdown、risk deduction、rewrite priorities、recommended project order、same-JD/same-resume compare API | 仍是 deterministic foundation；无大规模 human agreement、ranking stability、LLM reviewer calibration | 2.4 foundation, future quality calibration | 分数仍可能给出错误信心 |
| Project Rewrite | FOUNDATION | 每条 bullet 包含 before/after/reason/evidence_required/forbidden_changes/matched_jd_requirements/missing_points/risk_level/confidence，支持 unsupported metric / overclaim / project mismatch 风险 | 仍需人工确认；无真实 LLM rewrite calibration，无自动证据采集和事实审核 | 2.4 foundation, 2.6 | 可能鼓励 unsupported claim，必须保留人工确认 |
| Interview | DETERMINISTIC_ONLY | question generation、answer submit/list、deterministic scoring | 无真实 interviewer model、无 rubric calibration、无 human agreement | 2.1, 2.4 | 分数和反馈无法代表真实面试质量 |
| Study Plan | DETERMINISTIC_ONLY | deterministic phases/tasks/resources、task status | 无真实 gap diagnosis、学习资源质量和进度验证 | 2.4, 2.5 | 计划看似完整但不针对真实缺口 |
| Application | PARTIAL | 手动 application tracking、status history、reflection | 不接招聘系统，不处理真实投递合规、通知、审计 | 2.5, 2.6 | 数据完整性和操作审计不足 |
| Dashboard | PARTIAL | 聚合本地 stats 和 latest summaries | 很多页面仍需手填 ID，缺少 production selectors 和测试 | 2.6 | 主流程误操作、可用性弱 |
| RAG | FOUNDATION | document/chunk、lexical/vector/hybrid、local bag-of-words embedding、DB-persisted chunk vectors、citations/source_refs、RAG service-level eval | local vectorizer 不是最终 semantic embedding；无 reranker、pgvector/FAISS、production-scale vector DB、真实 LLM grounded generation、大 benchmark | 2.2 foundation, 2.6 | 检索质量、规模化和引用可信度仍不足 |
| Agent | FOUNDATION | `job_application_preparation`、`interview_preparation`、`application_review`、`study_gap_planning`，run lifecycle、attempt-aware step timeline、resume/retry/cancel、missing slots/questions、failure Bad Case draft、run_config/privacy-safe payload | 仍是同步 local runner；无 durable worker/queue/heartbeat/cancellation token，无真实 LLM planning/tool-calling | 2.5 foundation, 2.6/future durable workflow | 短流程可追踪，但不能承载真实长任务 SLA |
| Bad Case | PARTIAL | 人工 bad case、root cause、regression linkage、Agent step failure auto draft | 真实失败样例 triage、owner/priority SLA、自动 eval DB 闭环不足 | 2.1, 2.5, 2.6 | 问题沉淀仍需运营流程 |
| Evaluation | PARTIAL | `synthetic_smoke_v1`、service-level de-identified dataset、fileized runner、metrics/failed cases/actual outputs/run_config；Agent workflow 8 cases 覆盖 resume/retry/cancel/bad-case payload | 仍不是 production benchmark；当前不自动写 DB | 2.1 foundation, 2.2-2.6 持续 | service-level pass/fail 可能被误读为生产质量 |
| Auth / Workspace | PRODUCTION_FOUNDATION | register/login/me/logout、bearer token、workspace owner filtering、token revoke、route-level RBAC gate、basic audit | 无 SSO/MFA/refresh token rotation/session 管理/DB RLS/SIEM | v3.0 | 多租户和认证强度仍不足 |
| Database | FOUNDATION | Alembic、SQLite local default、PostgreSQL driver readiness、production runtime rejects SQLite | 仍缺 managed PostgreSQL provisioning、backup/restore/retention/erasure proof | 2.6 foundation / final audit | 本地 DB 路径不可作为生产数据层 |
| Frontend | PARTIAL | React workbench、多页面业务流、auth token client | 缺 lint/minimal tests/object selectors，主流程仍有手填 ID | 2.6 | 生产操作易错且回归难发现 |
| Docker / Deployment | FOUNDATION | Docker Compose 本地骨架、non-empty auth secret、production fail-fast config、readiness endpoint | 无云部署 runbook、secret manager integration、backup、managed DB provisioning | 2.6 foundation / final audit | 新环境可启动但不是生产部署 |
| Security / Privacy | FOUNDATION | preview/redaction、ignore hygiene、privacy export/delete/audit baseline、redacted errors/logging、delete-summary/proof id、v3.0 sensitive field envelope encryption、token revoke、RBAC gate | 无 KMS/rotation backfill、backup erasure/legal audit、SSO/MFA、SIEM、DB RLS | v3.0 foundation / v3.1+ | 真实生产合规仍需运维和安全体系 |
| Documentation | PARTIAL | README、architecture、deployment、evaluation、安全和阶段文档 | 历史文档多，需持续防止 production-ready 误表述 | 2.0 持续, 2.6 | 文档口径造成错误验收 |

## 3. Production Blockers

### P0

- Production-quality benchmark 缺失；阶段 2.1 service-level eval 已能调用真实服务，但仍不是真实生产质量评测。
- RAG 已有 local vector foundation 和 embedding persistence，但缺最终 semantic embedding、reranker、production-scale vector DB 和大规模 groundedness/recall/citation benchmark。
- JD Parser、Resume Parser 已升级到 parser production foundation，但默认仍是 deterministic local path；Match、Project Rewrite 已升级到 trustworthy foundation，但核心求职判断仍未达到生产完成。
- v3.0 已补应用层敏感字段加密，但缺少 KMS/多 key 解密、rotation backfill、retention、backup erasure proof 和合规审计。
- Docker/Auth secret 风险：阶段 2.0 已禁止 Compose 空 secret，production 仍必须接入 secret manager、rotation 和环境隔离。

### P1

- Agent 已有 2.5 foundation 状态机，但仍缺 durable queue/worker、heartbeat、true async cancellation token、workflow lease 和 production observability。
- 前端大量流程仍依赖手填 ID，缺少对象选择器、主流程防错和 minimal UI tests。
- PostgreSQL 不是生产默认，SQLite/local_data 仅适合 local dev。
- Observability 仍是 foundation：已有 structured request logging、request_id 和 readiness check，但缺集中日志、metrics、tracing、alerting、eval trace pipeline 和 SIEM。
- Auth/Workspace 已有 route-level RBAC foundation 和 token revoke；仍缺 SSO/MFA、refresh token rotation、session/device controls、DB RLS 和 SIEM。

### P2

- Demo/synthetic/service-level foundation 数据和评测文档容易被误读为真实质量保障。
- 历史 release/acceptance 文档有“已完成/final”语境，需要持续以本 baseline 为准。
- Application/Interview/Study Plan 还没有真实外部系统、日历、通知、学习资源质量和运营审计。

## 4. 后续阶段映射

- 2.1 Real Evaluation Foundation：已建立脱敏 service-level 样例集，让 eval runner 调用当前 service/retriever/parser/agent 路径，并输出可人工转 Bad Case 的 failed cases；自动 DB 写入和 Bad Case draft 仍是后续补齐项。
- 2.2 Real RAG Production Path：已建立 local vector embedding provider、DB-persisted chunk vectors、lexical/vector/hybrid mode、metadata filter、top-k、threshold、citation、no-evidence refusal 和 RAG 指标。仍只是 production foundation。
- 2.3 Real JD Parser + Resume Parser：已补 parser schema validation、evidence、confidence、warnings、risk flags、service-level parser eval、optional LLM provider path、timeout/retry/fallback/prompt/model metadata。默认仍是 deterministic local parser foundation，不是 full production parser。
- 2.4 Trustworthy Match Scoring + Project Rewrite：已建立六维评分、证据绑定、风险扣分、多 JD/多简历对比、Project Rewrite 反编造字段和 service-level metrics。仍只是 trustworthy foundation。
- 2.5 Agent Workflow Productionization：已补 pending/running/completed/failed/need_more_info/cancelled/retrying、step refs、resume/retry/cancel API、失败 Bad Case draft、多 workflow、Agent service-level eval 和前端兼容。仍只是 production foundation。
- v3.0 Security / Privacy / Data Governance：已补 runtime config validation、redaction/logging、readiness、privacy delete-summary/proof、audit foundation、production SQLite rejection、sensitive field envelope encryption、token revoke 和 route-level RBAC gate。KMS/rotation backfill、retention/backup erasure、SSO/MFA、refresh token、centralized observability、frontend lint/tests/selectors 和 cloud deployment runbook 仍需 v3.1+ / v3.4 审计。
