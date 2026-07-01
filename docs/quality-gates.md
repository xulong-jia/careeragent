# CareerAgent Quality Gates

这些门禁只证明 production hardening / real evaluation foundation 可继续迭代，不证明 CareerAgent production-ready。

## Required Baseline Gates

| Gate | Command | Pass meaning | Boundary |
| --- | --- | --- | --- |
| Git state | `git status -sb` | 确认当前分支和未提交变更范围 | 不替代 code review |
| Revision | `git rev-parse HEAD` | 记录验证起点 | 不代表 release tag |
| Backend tests | `PYTHONPATH=backend backend/.venv/bin/python -m pytest -p no:cacheprovider backend/tests` | 后端 contract、API、migration-adjacent tests 通过 | 主要是 deterministic/local tests |
| Aggregate v3.1 gate | `scripts/run_quality_gates.sh` | 聚合 backend tests、synthetic/service-level eval、frontend build、prod-like compose config、Alembic temp DB、diff/artifact/secret scan | 仍不是 cloud production certification |
| Frontend build | `cd frontend && npm run build -- --outDir /tmp/careeragent-frontend-build-v33` | TypeScript/Vite build 通过 | 不包含完整 UI regression |
| Frontend lint | `cd frontend && npm run lint` | 静态 contract lint 通过，检查 direct fetch、raw backend URL、手填 ID 文案和 selector exports | 不是 ESLint/AST 级完整 lint |
| Frontend typecheck | `cd frontend && npm run typecheck` | TS app 和 Vite config typecheck 通过 | 不证明运行时 UX 正确 |
| Frontend unit contract tests | `cd frontend && npm run test` | Node 内置 source contract tests 通过 | 不是 React Testing Library 组件测试 |
| Frontend mocked E2E smoke | `cd frontend && npm run test:e2e` | mock workflow 覆盖 selector/ref/privacy contract | 不是 Playwright/Cypress browser E2E |
| Docker Compose config | `docker compose config` | Compose 文件可解析，前提是 `.env` 或环境中提供 `AUTH_JWT_SECRET` | 不是 container build/push/deploy 证明 |
| Docker missing-secret negative check | `COMPOSE_DISABLE_ENV_FILE=1 env -u AUTH_JWT_SECRET docker compose config` | 在没有 `.env`/env secret 时应明确失败 | 验证 Compose 不接受空 secret |
| Alembic migration check | `DATABASE_URL=sqlite:////tmp/careeragent_phase26_alembic.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head` | 空临时 DB 可升级到 head | 不证明生产数据迁移策略 |
| Whitespace diff | `git diff --check` | 无 trailing whitespace 等 patch 问题 | 不证明逻辑正确 |
| Ignore hygiene | `git check-ignore -v .env local_data/careeragent.db backend/local_data/careeragent.db frontend/dist/index.html frontend/node_modules/react/package.json evals/results/smoke/summary.md` | 本地 secret/data/build artifacts 被 ignore | 不证明历史仓库无敏感数据 |
| Tracked artifact scan | `git ls-files local_data backend/local_data frontend/dist frontend/node_modules .pytest_cache backend/.venv` | 不应返回被跟踪 artifact | 仍需人工判断其他路径 |
| Secret scan | `rg -n "sk-[A-Za-z0-9_-]{12,}|BEGIN (RSA|OPENSSH|PRIVATE)|AUTH_JWT_SECRET=|API_KEY=" --hidden -g '!frontend/node_modules/**' -g '!backend/.venv/**' .` | 查找明显 secret/private key/placeholder 命中 | `.env.example` 和测试 fake key 需要人工确认 |
| Synthetic eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset synthetic --output-dir /tmp/careeragent-evals-synthetic-26` | synthetic contract runner 仍可执行 | 只防 contract fixture 破坏 |
| Service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --output-dir /tmp/careeragent-evals-service-26` | runner 真实调用当前 service/retriever/parser/agent/match/rewrite 路径并输出 metrics/failed cases | foundation，不是 production benchmark |
| Benchmark eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --output-dir /tmp/careeragent-evals-benchmark-v32` | v3.2 100-case synthetic benchmark foundation 输出 RAG recall/MRR/groundedness、match human agreement、score stability、human review 和 bad-case trend metrics | synthetic foundation，不是真实生产质量认证 |
| Readiness/redaction/privacy tests | `PYTHONPATH=backend backend/.venv/bin/python -m pytest -p no:cacheprovider backend/tests/test_auth_secret_config.py backend/tests/test_data_encryption_governance.py backend/tests/test_health.py backend/tests/test_privacy_governance.py backend/tests/test_p1_auth_workspace_isolation.py` | 覆盖 production config rejection、masked config summary、readiness、encryption envelope、redacted logging/errors、delete-summary/proof、token revoke、RBAC gate | 不证明完整合规体系 |
| Parser service-level eval | `backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module jd_parser --output-dir /tmp/careeragent-evals-jd-parser && backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module resume_parser --output-dir /tmp/careeragent-evals-resume-parser` | JD/Resume parser foundation cases 通过并输出 evidence/confidence/warnings metrics | parser foundation，不是 full production parser |
| RAG service-level eval | `backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module rag --output-dir /tmp/careeragent-evals-rag` | RAG lexical/vector/hybrid/no-evidence cases 通过并输出 vector metrics | local vector foundation，不是 full production RAG |
| Match service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module match --output-dir /tmp/careeragent-evals-match` | Match 六维评分、风险扣分、compare case 和 evidence metrics 通过 | trustworthy foundation，不是生产级求职判断 |
| Project Rewrite service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module project_rewrite --output-dir /tmp/careeragent-evals-project-rewrite` | before/after、evidence_required、forbidden_changes、risk_level、fabrication guard metrics 通过 | rewrite foundation，不是自动可用简历成稿 |
| Agent Workflow service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module agent_workflow --output-dir /tmp/careeragent-evals-agent-workflow` | 8 个 Agent cases 覆盖 success、need_more_info、resume、retry、cancel、Bad Case payload 和多 workflow | workflow foundation，不是 durable production engine |

## Auth Secret Gate

本地 Docker Compose 必须通过 `.env` 或 shell env 提供 `AUTH_JWT_SECRET`。推荐本地值来自 `.env.example`：

```bash
AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars docker compose config
```

Production 必须使用 secret manager 或部署环境注入强随机值。`APP_ENV=production` 会拒绝短 secret 和 dev-only / replace-me / change-me placeholder。

## Phase 2.6 Security / Privacy / Deployment Gates

- `GET /ready` / `GET /api/ready` must return DB/config readiness with masked config summary only.
- `APP_ENV=production` must reject SQLite `DATABASE_URL`, weak/placeholder `AUTH_JWT_SECRET`, and wildcard CORS.
- Request logs must include request_id/path/status/duration and must not include body, raw_text, Authorization, token or API key.
- Validation error responses must redact sensitive input values.
- Privacy delete-all must return resource-level `deleted_counts`, `deletion_proof_id`, and retention/backup limitation note.
- Audit metadata must remain refs/counts/config-safe only; no resume/JD/RAG raw payload.

## v3.0 Security / Privacy / Data Governance Gates

- Sensitive repository/service write paths must store Fernet envelopes for Resume/JD/RAG/Interview/Application/Bad Case private text fields.
- Legacy plaintext rows must remain readable so rollout does not break existing local/dev data.
- `APP_ENV=production` must reject missing/invalid/local-dev `DATA_ENCRYPTION_KEY`.
- `POST /api/auth/logout` must revoke current access token `jti`; revoked tokens must return `token_revoked`.
- Viewer/member/owner route permissions must be enforced before mutating protected APIs.
- Privacy delete-all must support `dry_run=true` and execute proof with retained-record and backup-purge limitation fields.
- Evaluation case/result payloads and audit metadata must remain redacted and JSON-serializable.

## v3.1 Production Deployment / Database / Operations Gates

- `docker-compose.prod-like.yml` must parse with production-like secrets and fail when required secrets such as `AUTH_JWT_SECRET` are missing.
- `APP_ENV=production` must reject SQLite, wildcard CORS, placeholder auth/data keys and `DB_ECHO_SQL=true`.
- `/live` must return process liveness.
- `/ready` must check DB reachability, config validity, local storage writability and Alembic current/head status.
- `/metrics` must return non-secret HTTP counters plus Agent/Eval/RAG DB counts.
- `scripts/db_migrate.sh` must run Alembic against a supplied `DATABASE_URL`.
- `scripts/db_backup.sh` and `scripts/db_restore.sh` must refuse SQLite and require PostgreSQL tooling.
- `scripts/db_restore.sh` must require `CONFIRM_RESTORE=restore`.
- Frontend production image must use build output served by nginx, not Vite dev server.
- Backup dump artifacts must remain ignored and untracked.

## v3.2 Production AI Quality Gates

- RAG chunk metadata must include provider/model/dim/version, provider config id, vector source, semantic flag, input hash and created_at without raw chunk text.
- `RAG_RERANKER_MODE=none|local_score|provider` must be safe to configure; default remains `none`.
- `POST /api/rag/answer` must support `answer_mode=deterministic_summary|llm_grounded`; default remains deterministic and no network.
- `llm_grounded` must validate schema output, enforce citation chunk ids from retrieved sources, return prompt/model/fallback metadata and refuse no-evidence answers.
- `POST /api/resumes/{resume_id}/parse` must support `parser_mode=deterministic|llm_parser`; deterministic mode must not require provider config.
- Resume parser metadata must report OCR unsupported status and table/bilingual/noisy layout signals without claiming OCR production readiness.
- `scripts/run_evals.py --dataset benchmark` must write metrics, actual outputs, failed cases, run_config and human_review_summary under `/tmp` or ignored paths only.
- Benchmark outputs must not include real private data, API keys, provider traces, raw resume/JD text or full RAG chunk text.

## v3.3 Frontend Productization / E2E Gates

- Main workflow pages must use object selectors for Profile, Resume Version, JD, Match Report, Project, Application, Agent Run, Knowledge Document, RAG Answer Run and Agent workflow refs.
- MatchReportPage must run match by `resume_version_id + jd_id` when a version is selected and expose compare via `/api/matches/compare`.
- Project, Interview, Study Plan, Application, Agent and Bad Case flows must not require ordinary users to copy/paste primary internal object IDs.
- Frontend pages must use centralized `frontend/src/api/*` clients; direct `fetch` remains isolated to `frontend/src/api/client.ts`.
- Privacy-sensitive saved data must render as preview, snippet, citation, source ref or sanitized JSON by default.
- `npm run lint`, `npm run typecheck`, `npm run test`, `npm run test:e2e` and `npm run build -- --outDir /tmp/careeragent-frontend-build-v33` must pass.
- The current `test:e2e` gate is mocked. Production readiness still requires real browser E2E, auth/data seeding, accessibility and visual/layout checks.

## Evaluation Boundary

当前 smoke/synthetic eval 是 synthetic contract regression。它只检查 JD Parser、Resume Parser、Match、RAG、Agent、Application、Bad Case 的固定 contract 是否还跑得通。

阶段 2.1 已新增 `service_level` evaluation foundation：

- 脱敏/自造 JD、简历、RAG 文档、match case、agent workflow case。
- Eval runner 调用 `job_service`、`resume_service`、`match_service`、`project_rewrite_service`、`rag_service`、`agent_service` 和 `agent.runner`。
- 输出 `summary.md`、`metrics.json`、`failed_cases.json`、`actual_outputs.json`、`run_config.json`。
- 失败样例包含可人工转 Bad Case 的摘要字段。

当前整体 evaluation 仍未做自动 DB 写入。Agent Workflow 2.5 已能为 step failure 自动创建 Bad Case draft，但 service-level pass/fail 仍不得解释为核心 AI 能力生产完成。

阶段 2.5 已新增 Agent Workflow production foundation:

- Agent Workflow service-level dataset 扩展到 8 cases，覆盖 `job_application_preparation`、`interview_preparation`、`application_review` 和 `study_gap_planning`。
- Agent metrics 包含 `resume_success`、`retry_success`、`cancel_success`、`bad_case_payload_present`、`run_config_present` 和 `privacy_safe_payload_present`。
- Agent remains deterministic/local synchronous runner; this is not a durable production workflow engine.

阶段 2.3 已新增 parser production foundation：

- JD parser 输出 required/preferred、role_category、responsibilities、business scenarios、hidden requirements、evidence、confidence、warnings 和 parser metadata。
- Resume parser 输出 section records、skill categories、risk flags、evidence、confidence、warnings 和 parser metadata。
- Parser service-level dataset 扩展为 JD 12 cases、Resume 8 cases。
- 默认 parser 仍是 local deterministic foundation；optional LLM path 不作为测试前提，也不是 production-ready parser。

阶段 2.4 已新增 trustworthy match/project rewrite foundation：

- Match service-level dataset 扩展到 9 cases，覆盖强/弱匹配、项目证据缺失、业务理解缺口、unsupported metric、教育 fit 和多简历比较。
- Project Rewrite service-level dataset 新增 6 cases，覆盖缺 required skill、unsupported metric、learning-to-business overclaim、空原 bullet 和防编造技术。
- Match metrics 包含 `dimension_score_present_rate`、`evidence_dimension_coverage`、`risk_flag_hit_rate`、`rewrite_priority_hit_rate`、`scoring_method_present` 和 `confidence_present`。
- Project Rewrite metrics 包含 `before_after_present`、`evidence_required_present`、`forbidden_changes_present`、`risk_level_present` 和 `fabrication_guard_pass`。
- 这仍不是 production-quality human agreement benchmark。

阶段 2.2 已新增 RAG local vector production foundation：

- RAG indexing 持久化 chunk embedding vector 和 provider/model/dim/version metadata。
- RAG search 区分 `lexical`、`vector`、`hybrid`，并保留 legacy `deterministic_*` request alias。
- RAG service-level metrics 包含 `retrieval_mode_match`、`average_top_score`、`vector_index_used` 和 no-evidence refusal。
- 这仍不是 full production RAG；local/offline vectorizer、SQLite JSON vector、未校准 reranker、optional LLM grounded path 和 synthetic benchmark 都是 foundation，不是生产认证。

v3.2 已新增 Production AI Quality foundation：

- RAG reranker contract、optional LLM grounded answer、semantic provider metadata、LLM parser mode、OCR/table/bilingual parser metadata 和 100-case synthetic benchmark。
- Benchmark metrics 覆盖 RAG recall@k/MRR/groundedness、match human agreement、score stability、human review summary 和 bad-case regression trend。
- 这仍不是 production-ready；真实 anonymized datasets、真实 semantic provider runs、LLM judge/human review protocol、production vector DB path 和 v3.4 final audit 仍是阻断项。
