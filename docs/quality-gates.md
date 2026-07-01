# CareerAgent Quality Gates

这些门禁只证明 production hardening / real evaluation foundation 可继续迭代，不证明 CareerAgent production-ready。

## Required Baseline Gates

| Gate | Command | Pass meaning | Boundary |
| --- | --- | --- | --- |
| Git state | `git status -sb` | 确认当前分支和未提交变更范围 | 不替代 code review |
| Revision | `git rev-parse HEAD` | 记录验证起点 | 不代表 release tag |
| Backend tests | `PYTHONPATH=backend backend/.venv/bin/python -m pytest -p no:cacheprovider backend/tests` | 后端 contract、API、migration-adjacent tests 通过 | 主要是 deterministic/local tests |
| Frontend build | `cd frontend && npm run build -- --outDir /tmp/careeragent-frontend-build-24` | TypeScript/Vite build 通过 | 不包含完整 UI regression |
| Docker Compose config | `docker compose config` | Compose 文件可解析，前提是 `.env` 或环境中提供 `AUTH_JWT_SECRET` | 不是 container build/push/deploy 证明 |
| Docker missing-secret negative check | `COMPOSE_DISABLE_ENV_FILE=1 env -u AUTH_JWT_SECRET docker compose config` | 在没有 `.env`/env secret 时应明确失败 | 验证 Compose 不接受空 secret |
| Alembic migration check | `DATABASE_URL=sqlite:////tmp/careeragent_phase24_alembic.db backend/.venv/bin/alembic -c backend/alembic.ini upgrade head` | 空临时 DB 可升级到 head | 不证明生产数据迁移策略 |
| Whitespace diff | `git diff --check` | 无 trailing whitespace 等 patch 问题 | 不证明逻辑正确 |
| Ignore hygiene | `git check-ignore -v .env local_data/careeragent.db backend/local_data/careeragent.db frontend/dist/index.html frontend/node_modules/react/package.json evals/results/smoke/summary.md` | 本地 secret/data/build artifacts 被 ignore | 不证明历史仓库无敏感数据 |
| Tracked artifact scan | `git ls-files local_data backend/local_data frontend/dist frontend/node_modules .pytest_cache backend/.venv` | 不应返回被跟踪 artifact | 仍需人工判断其他路径 |
| Secret scan | `rg -n "sk-[A-Za-z0-9_-]{12,}|BEGIN (RSA|OPENSSH|PRIVATE)|AUTH_JWT_SECRET=|API_KEY=" --hidden -g '!frontend/node_modules/**' -g '!backend/.venv/**' .` | 查找明显 secret/private key/placeholder 命中 | `.env.example` 和测试 fake key 需要人工确认 |
| Synthetic eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset synthetic --output-dir /tmp/careeragent-evals-synthetic-24` | synthetic contract runner 仍可执行 | 只防 contract fixture 破坏 |
| Service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --output-dir /tmp/careeragent-evals-service-24` | runner 真实调用当前 service/retriever/parser/agent/match/rewrite 路径并输出 metrics/failed cases | foundation，不是 production benchmark |
| Parser service-level eval | `backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module jd_parser --output-dir /tmp/careeragent-evals-jd-parser && backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module resume_parser --output-dir /tmp/careeragent-evals-resume-parser` | JD/Resume parser foundation cases 通过并输出 evidence/confidence/warnings metrics | parser foundation，不是 full production parser |
| RAG service-level eval | `backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module rag --output-dir /tmp/careeragent-evals-rag` | RAG lexical/vector/hybrid/no-evidence cases 通过并输出 vector metrics | local vector foundation，不是 full production RAG |
| Match service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module match --output-dir /tmp/careeragent-evals-match` | Match 六维评分、风险扣分、compare case 和 evidence metrics 通过 | trustworthy foundation，不是生产级求职判断 |
| Project Rewrite service-level eval | `PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module project_rewrite --output-dir /tmp/careeragent-evals-project-rewrite` | before/after、evidence_required、forbidden_changes、risk_level、fabrication guard metrics 通过 | rewrite foundation，不是自动可用简历成稿 |

## Auth Secret Gate

本地 Docker Compose 必须通过 `.env` 或 shell env 提供 `AUTH_JWT_SECRET`。推荐本地值来自 `.env.example`：

```bash
AUTH_JWT_SECRET=dev-only-change-me-careeragent-local-auth-secret-32chars docker compose config
```

Production 必须使用 secret manager 或部署环境注入强随机值。`APP_ENV=production` 会拒绝短 secret 和 dev-only / replace-me / change-me placeholder。

## Evaluation Boundary

当前 smoke/synthetic eval 是 synthetic contract regression。它只检查 JD Parser、Resume Parser、Match、RAG、Agent、Application、Bad Case 的固定 contract 是否还跑得通。

阶段 2.1 已新增 `service_level` evaluation foundation：

- 脱敏/自造 JD、简历、RAG 文档、match case、agent workflow case。
- Eval runner 调用 `job_service`、`resume_service`、`match_service`、`rag_service`、`agent.runner`。
- 输出 `summary.md`、`metrics.json`、`failed_cases.json`、`actual_outputs.json`、`run_config.json`。
- 失败样例包含可人工转 Bad Case 的摘要字段。

当前仍未做自动 DB 写入和 Bad Case draft。service-level pass/fail 都不得解释为核心 AI 能力生产完成。

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
- 这仍不是 full production RAG；local bag-of-words vectorizer、SQLite JSON vector、无 reranker 和小 benchmark 都是后续缺口。
