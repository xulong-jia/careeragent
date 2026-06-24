# Release Notes v0.7 Engineering Handoff

`v0.7` 是 CareerAgent 阶段七工程化、Docker、README 和演示材料收尾节点。

## 1. 本轮新增

- 新增后端 Dockerfile。
- 新增前端 Dockerfile。
- 优化 `docker-compose.yml`，使用本地 build context。
- 显式配置 SQLite bind mount：`backend/local_data:/app/backend/local_data`。
- Compose 后端启动时执行 `alembic upgrade head`。
- 更新 `.env.example`，补充 `VITE_API_BASE_URL` 和 deterministic MVP 边界说明。
- 新增 `frontend/.env.example`。
- 新增 synthetic demo seed script：`scripts/seed_demo_data.py`。
- 新增 current architecture、API reference、database schema、safety/privacy checklist、demo script、final acceptance report 文档。

## 2. 当前能力

- Resume / JD / Match
- Resume Versions
- RAG lexical prototype
- Agent deterministic state machine
- Application Tracking
- Bad Case
- Deterministic Evaluation
- Dashboard
- Local Docker Compose startup

## 3. 不做内容

- 不接真实 LLM。
- 不接 embedding/vector database。
- 不做自动投递。
- 不接招聘网站。
- 不做复杂部署平台。
- 不做生产级多用户权限。
- 不提交真实隐私数据。

## 4. 验证命令

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose config
docker compose build
git diff --check
git status --short --branch
```

## 5. Demo

本地启动后可运行：

```bash
python3 scripts/seed_demo_data.py
```

该脚本只生成 synthetic demo data，通过公开 HTTP API 创建最小演示链路。

## 6. 注意事项

- `docs/screenshots/` 当前只保留 `.gitkeep`，不伪造截图。
- 如需提交截图，必须本地运行后人工截取，并确认没有真实个人信息或 API key。
- Docker Compose 是本地开发配置，不是生产部署配置。
