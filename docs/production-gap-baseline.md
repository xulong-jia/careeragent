# CareerAgent Production Gap Baseline

阶段 2.3 后，当前仓库是 production hardening + real evaluation + real RAG + real parser production foundation。本文档不声明 production-ready。

## 1. 当前总体判断

当前版本可以作为 production hardening + real evaluation + real RAG + real parser production foundation，因为主业务对象已经有持久化、Auth/Workspace 基础隔离、隐私 preview 收敛、Docker 本地骨架、Alembic migration、后端测试、前端 build、synthetic smoke regression、service-level evaluation runner、RAG local vector embedding persistence，以及 JD/Resume parser evidence/confidence/warnings baseline。

当前版本不是 production-ready，原因是核心 AI 能力仍大量依赖 deterministic、synthetic 或本地 foundation 路径：RAG 已有 local vector path 和 DB-persisted chunk vectors，但没有最终 semantic embedding、reranker 或 production-scale vector DB；JD/Resume parser 已有 production foundation 字段和 optional LLM path，但默认仍是 deterministic local parser，未接 OCR、未做大规模真实 benchmark；Match/Rewrite 仍是规则和 overlap，Agent 是同步固定 workflow，Evaluation 仍只是 foundation benchmark，raw_text 仍明文保存，生产 DB、observability、retention、backup、RBAC 和部署策略不足。

完成标准口径：mock、stub、deterministic、synthetic、prototype、本地可演示、骨架完整都不能标为 DONE，只能标为 PARTIAL、FOUNDATION、MOCK_ONLY、DETERMINISTIC_ONLY、SYNTHETIC_ONLY 或 RISKY。

## 2. 模块状态矩阵

| 模块 | 状态 | 当前已有能力 | Production 缺口 | 下一阶段归属 | 主要风险 |
| --- | --- | --- | --- | --- | --- |
| Profile | PARTIAL | Profile CRUD、readiness summary、workspace scope | 仍是人工画像，不自动从可信证据生成；缺少生产级 profile audit | 2.6 / future profile audit | 用户画像与简历/JD 证据不一致 |
| Resume | FOUNDATION | PDF/DOCX/MD/txt 文本层提取、version、parser evidence/confidence/warnings、risk flags、optional LLM fallback path | 默认仍是 deterministic local parser；无 OCR、大规模 benchmark、复杂 PDF/table resume production path；raw_text 明文 | 2.3 foundation, 2.6 | parser 误读、隐私存储风险 |
| JD | FOUNDATION | 创建 JD、required/preferred、role category、responsibilities、business scenarios、hidden requirements、evidence/confidence/warnings、parser metadata | 默认仍是 deterministic local parser；真实 LLM parser calibration 和大样本 benchmark 不足 | 2.3 foundation | JD 理解仍需真实样本验证 |
| Match | DETERMINISTIC_ONLY | deterministic scoring、gaps、evidence-like refs | 仍以 skill overlap/规则为主，六维评分和证据绑定不足 | 2.4 | 分数给出错误信心 |
| Project Rewrite | DETERMINISTIC_ONLY | 基于项目 facts/JD 的 rewrite suggestions | 缺少 evidence_required/forbidden_changes 的生产级校验和人工确认闭环 | 2.4 | 可能鼓励 unsupported claim |
| Interview | DETERMINISTIC_ONLY | question generation、answer submit/list、deterministic scoring | 无真实 interviewer model、无 rubric calibration、无 human agreement | 2.1, 2.4 | 分数和反馈无法代表真实面试质量 |
| Study Plan | DETERMINISTIC_ONLY | deterministic phases/tasks/resources、task status | 无真实 gap diagnosis、学习资源质量和进度验证 | 2.4, 2.5 | 计划看似完整但不针对真实缺口 |
| Application | PARTIAL | 手动 application tracking、status history、reflection | 不接招聘系统，不处理真实投递合规、通知、审计 | 2.5, 2.6 | 数据完整性和操作审计不足 |
| Dashboard | PARTIAL | 聚合本地 stats 和 latest summaries | 很多页面仍需手填 ID，缺少 production selectors 和测试 | 2.6 | 主流程误操作、可用性弱 |
| RAG | FOUNDATION | document/chunk、lexical/vector/hybrid、local bag-of-words embedding、DB-persisted chunk vectors、citations/source_refs、RAG service-level eval | local vectorizer 不是最终 semantic embedding；无 reranker、pgvector/FAISS、production-scale vector DB、真实 LLM grounded generation、大 benchmark | 2.2 foundation, 2.6 | 检索质量、规模化和引用可信度仍不足 |
| Agent | DETERMINISTIC_ONLY | 固定 `job_application_preparation` 同步 state machine、timeline refs | 无 resume/retry/cancel、缺槽追问、失败恢复、多 workflow production path | 2.5 | 同步 demo 无法承载真实长流程 |
| Bad Case | PARTIAL | 人工 bad case、root cause、regression linkage | 自动 draft、真实失败样例入库、triage workflow 不足 | 2.1, 2.5 | 问题沉淀不完整 |
| Evaluation | PARTIAL | `synthetic_smoke_v1`、service-level de-identified dataset、fileized runner、metrics/failed cases/actual outputs/run_config | 仍不是 production benchmark；当前不自动写 DB，不自动生成 Bad Case draft | 2.1 foundation, 2.2-2.6 持续 | service-level pass/fail 可能被误读为生产质量 |
| Auth / Workspace | PRODUCTION_FOUNDATION | register/login/me/logout、bearer token、workspace owner filtering、basic audit | 无 SSO/MFA/refresh token/full RBAC/session 管理/SIEM | 2.6 | 多租户和认证强度不足 |
| Database | RISKY | Alembic、SQLite default、PostgreSQL driver readiness | PostgreSQL 不是生产默认，无 backup/restore/retention/erasure proof | 2.6 | 本地 DB 路径不可作为生产数据层 |
| Frontend | PARTIAL | React workbench、多页面业务流、auth token client | 缺 lint/minimal tests/object selectors，主流程仍有手填 ID | 2.6 | 生产操作易错且回归难发现 |
| Docker / Deployment | PARTIAL | Docker Compose 本地骨架，阶段 2.0 要求 non-empty auth secret | 无云部署 runbook、secret manager、readiness、backup、managed DB | 2.6 | 新环境可启动但不是生产部署 |
| Security / Privacy | RISKY | preview/redaction、ignore hygiene、privacy export/delete/audit baseline | raw_text 明文、无 encryption-at-rest/retention/backup erasure/legal audit | 2.6 | 真实隐私数据不可直接处理 |
| Documentation | PARTIAL | README、architecture、deployment、evaluation、安全和阶段文档 | 历史文档多，需持续防止 production-ready 误表述 | 2.0 持续, 2.6 | 文档口径造成错误验收 |

## 3. Production Blockers

### P0

- Production-quality benchmark 缺失；阶段 2.1 service-level eval 已能调用真实服务，但仍不是真实生产质量评测。
- RAG 已有 local vector foundation 和 embedding persistence，但缺最终 semantic embedding、reranker、production-scale vector DB 和大规模 groundedness/recall/citation benchmark。
- JD Parser、Resume Parser 已升级到 parser production foundation，但默认仍是 deterministic local path；Match、Project Rewrite 仍是规则和 overlap，核心求职判断尚不可信。
- `raw_text` 明文存储，缺少 encryption、retention、backup erasure proof 和合规审计。
- Docker/Auth secret 风险：阶段 2.0 已禁止 Compose 空 secret，production 仍必须接入 secret manager、rotation 和环境隔离。

### P1

- Agent 是同步单 workflow，缺少 pending/running/failed/retrying/cancelled/resume/retry/cancel 生产状态机。
- 前端大量流程仍依赖手填 ID，缺少对象选择器、主流程防错和 minimal UI tests。
- PostgreSQL 不是生产默认，SQLite/local_data 仅适合 local dev。
- Observability 不足：缺 structured logging、request_id trace、readiness check、eval trace、audit pipeline。
- Auth/Workspace 仍缺 full RBAC、SSO/MFA、refresh token、token rotation 和 session/device controls。

### P2

- Demo/synthetic/service-level foundation 数据和评测文档容易被误读为真实质量保障。
- 历史 release/acceptance 文档有“已完成/final”语境，需要持续以本 baseline 为准。
- Application/Interview/Study Plan 还没有真实外部系统、日历、通知、学习资源质量和运营审计。

## 4. 后续阶段映射

- 2.1 Real Evaluation Foundation：已建立脱敏 service-level 样例集，让 eval runner 调用当前 service/retriever/parser/agent 路径，并输出可人工转 Bad Case 的 failed cases；自动 DB 写入和 Bad Case draft 仍是后续补齐项。
- 2.2 Real RAG Production Path：已建立 local vector embedding provider、DB-persisted chunk vectors、lexical/vector/hybrid mode、metadata filter、top-k、threshold、citation、no-evidence refusal 和 RAG 指标。仍只是 production foundation。
- 2.3 Real JD Parser + Resume Parser：已补 parser schema validation、evidence、confidence、warnings、risk flags、service-level parser eval、optional LLM provider path、timeout/retry/fallback/prompt/model metadata。默认仍是 deterministic local parser foundation，不是 full production parser。
- 2.4 Trustworthy Match Scoring + Project Rewrite：建立六维评分、证据绑定、风险扣分、多 JD/多简历对比和 human agreement/evidence completeness 等评测。
- 2.5 Agent Workflow Productionization：补 pending/running/completed/failed/need_more_info/cancelled/retrying、step refs、resume/retry/cancel API、失败 Bad Case draft 和多 workflow。
- 2.6 Security / Privacy / Deployment Hardening：补 encryption/retention/audit/observability、PostgreSQL production default、RBAC、secret handling、frontend lint/tests/selectors 和可复现部署。
