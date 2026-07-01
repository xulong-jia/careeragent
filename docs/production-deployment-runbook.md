# CareerAgent v3.1 Production-like Deployment Runbook

v3.1 提供 production-like deployment foundation：PostgreSQL/pgvector compose profile、生产环境样例、frontend 静态托管镜像、backend readiness/liveness/metrics 和可重复 quality gate。它仍不是 cloud production certification，也不能单独作为 production-ready tag 依据。

## Prerequisites

- 使用私有 `.env.production` 或部署平台 secret manager 注入环境变量；不要提交真实 secret。
- `APP_ENV=production`。
- `AUTH_JWT_SECRET`：至少 32 字符强随机值。
- `DATA_ENCRYPTION_KEY`：生产 Fernet key。
- `DATA_ENCRYPTION_KEY_ID`：稳定 key id，例如 `prod-2026-07-v1`。
- `DATABASE_URL`：PostgreSQL-compatible URL。SQLite 会被 production runtime 拒绝。
- `BACKEND_CORS_ORIGINS`：明确 frontend origin，不允许 `*`。
- Node.js >= 20.19.0 for local/CI frontend builds. The production frontend Dockerfile uses a Node 20 base image and should be kept at a compatible patch level.

可从模板开始：

```bash
cp .env.production.example .env.production
```

`.env.production.example` 只能作为字段清单；其中的占位值不能直接用于真实部署。

## Compose Profile

```bash
docker compose --env-file .env.production -f docker-compose.prod-like.yml config
docker compose --env-file .env.production -f docker-compose.prod-like.yml build
docker compose --env-file .env.production -f docker-compose.prod-like.yml up -d
```

服务：

- `postgres`: `pgvector/pgvector:pg16`，为 v3.2 semantic/vector path 提供部署基础。
- `backend`: 启动时执行 `alembic upgrade head`，提供 `/health`、`/live`、`/ready`、`/metrics`。
- `frontend`: `frontend/Dockerfile.production` build 后由 nginx 托管，并将 `/api/` 代理到 backend。

## Startup Gates

```bash
curl http://localhost:8000/live
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
```

`/ready` 在 production 中要求：

- runtime config valid；
- database reachable；
- local data dir writable；
- Alembic current revision 等于 head revision。

`/metrics` 返回 HTTP 进程内汇总和 DB 聚合的 Agent/Eval/RAG run counts，不包含 raw resume、JD、chunk、question、answer 或 provider payload。

## Migration

手动迁移入口：

```bash
DATABASE_URL=postgresql+psycopg://... scripts/db_migrate.sh
```

只查看当前/目标 revision：

```bash
DATABASE_URL=postgresql+psycopg://... DRY_RUN=1 scripts/db_migrate.sh
```

## Rollback

v3.1 不提供自动 schema downgrade。生产回滚策略是：

1. 停止写流量或切到维护模式。
2. 记录当前 image tag、git commit、Alembic current/head。
3. 从最近一次 verified backup 恢复到隔离环境。
4. 回滚应用镜像到上一已验证版本。
5. 对比 `/ready`、核心 smoke API、privacy delete dry-run 和 eval smoke。
6. 确认后再恢复生产流量。

## Production Boundaries

- v3.1 compose 是 production-like profile，不是托管云部署证明。
- PostgreSQL/pgvector deployment profile 已存在，但应用 RAG 默认仍是 local/database JSON vector foundation；semantic provider/pgvector query path 属于 v3.2。
- secret manager、backup encryption、centralized logs/metrics/tracing/alerts 需要由目标云平台接入并按本 runbook 验证。
