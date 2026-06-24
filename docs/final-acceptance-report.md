# CareerAgent Final Acceptance Report

本报告记录阶段七工程化收尾后的当前项目状态。报告基于当前仓库真实代码、测试和文档，不代表生产就绪系统。

## 1. 总体完成度

当前项目已经具备本地可运行、可持久化、可演示、可复查的求职工作台 prototype。

已完成：

- Resume / JD / Match 最小闭环。
- SQLite + SQLAlchemy + Alembic 持久化。
- Resume Version 管理。
- RAG deterministic lexical prototype。
- Agent deterministic state machine prototype。
- Application Tracking + Dashboard MVP。
- Quality Review / Bad Case。
- Deterministic Evaluation MVP。
- Docker / Compose 本地开发配置。
- README、API、DB schema、架构、demo、安全隐私文档。

## 2. 已完成模块

| 模块 | 状态 |
| --- | --- |
| Resume Center | 已完成 MVP |
| Resume Versions | 已完成 MVP |
| JD Center | 已完成 MVP |
| Match Report | 已完成 MVP |
| RAG Knowledge Base | 已完成 deterministic prototype |
| Agent Runs | 已完成 deterministic state machine prototype |
| Application Tracking | 已完成手动 tracking MVP |
| Dashboard | 已接入核心统计 |
| Bad Case | 已完成人工质量复盘 MVP |
| Evaluation | 已完成 deterministic smoke evaluation MVP |
| Docker / Compose | 已完成本地开发配置 |
| Docs / Demo | 已完成交付说明 |

## 3. 测试状态

标准检查命令：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose config
git diff --check
```

阶段七完成时应记录实际运行结果到提交说明或验收输出。

## 4. Docker / Docs / Safety 状态

- 后端 Dockerfile：`backend/Dockerfile`
- 前端 Dockerfile：`frontend/Dockerfile`
- Compose：`docker-compose.yml`
- Compose 后端启动时执行 `alembic upgrade head`
- SQLite bind mount：`backend/local_data:/app/backend/local_data`
- 安全清单：`docs/safety-privacy-checklist.md`
- Demo 流程：`docs/demo-script.md`
- API 文档：`docs/api-reference.md`
- DB 文档：`docs/database-schema.md`
- 当前架构：`docs/current-architecture.md`

## 5. 已知边界

- 不接真实 LLM。
- 不接真实 embedding/vector database。
- 不做 LLM judge。
- 不做多模型评测。
- 不做自动投递。
- 不接招聘网站。
- 不做生产级多用户权限。
- 不做 PostgreSQL / pgvector 部署。
- PDF / DOCX parser 仍是 placeholder。
- Evaluation score 是 deterministic smoke score，不是模型能力最终评分。

## 6. 数据与隐私

- `.env` 不进入 Git。
- `local_data/` 不进入 Git。
- SQLite DB 不进入 Git。
- uploads、vector index、exports、logs、cache 不进入 Git。
- Demo 和测试只使用 synthetic data。
- Bad Case 和 Evaluation Case 不应保存大段隐私原文。

## 7. 后续规划

建议后续只在明确目标下扩展：

1. 生产部署前引入认证、权限、审计日志和数据删除策略。
2. 接真实 LLM 前先完成隐私红线、prompt logging 策略和人工确认流程。
3. 接 PostgreSQL / pgvector 前先写 migration plan。
4. 将 deterministic evaluation 扩展为 regression dataset。
5. 补充 Playwright 或前端组件测试。
