# CareerAgent v0.2.0-persistence Release Notes

## 1. 版本定位

- CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。
- `v0.2.0-persistence` 是阶段二完成节点。
- 本版本完成从最小 Mock 闭环到 DB-backed 持久化工作台的升级。

## 2. 阶段一能力

- FastAPI 后端基础服务。
- React + TypeScript + Vite 前端工作台。
- Resume Upload -> JD Create -> Match Report -> Frontend Display 最小闭环。
- Markdown / txt 最小 raw text extraction。
- PDF / DOCX parser placeholder。
- deterministic `structured_resume` / JD profile / match report。
- 统一 API response 和错误结构。

## 3. 阶段二能力

- SQLite + SQLAlchemy + Alembic 数据库基础设施。
- Alembic migrations。
- DB health check。
- Resume 持久化。
- Resume Version 初始创建、list、detail、clone、archive。
- JD 持久化。
- Job Profile 持久化。
- Match Report 持久化。
- Match Report 历史查询。
- Match Report 绑定 `resume_version_id + jd_id`。
- 前端展示持久化 Resume / JD / Match 历史。
- Resume Center 支持版本查看、clone、archive。
- Dashboard 展示持久化工作台入口和数量。

## 4. 当前不包含的能力

- 真实 LLM 接入。
- RAG。
- Agent Workflow。
- 投递管理。
- Bad Case 页面。
- Evaluation Center。
- 登录 / 权限系统。
- 同一 JD 多版本复杂对比 UI。
- 简历版本 diff UI。
- 自动简历优化。
- 自动投递。

## 5. 安全与隐私说明

- 不提交 `.env`。
- 不提交 `local_data/`。
- 不提交 SQLite 数据库文件。
- 不提交真实简历、真实 JD、投递记录、面试复盘。
- 不提交 API Key。
- 不提交 `CareerAgent_最终版项目开发执行手册.md`。
- 前端默认只展示 `raw_text_preview`。
- DB health 不输出完整 `DATABASE_URL`。

## 6. 验收状态

- 阶段一总验收通过。
- 阶段二总验收通过。
- 后端 pytest 通过。
- 前端 build 通过。
- `docker compose config` 通过。
- Alembic upgrade 通过。
- DB health 通过。
- 安全扫描通过。

## 7. 后续阶段

- 下一阶段建议进入阶段三：RAG 知识库。
- 进入阶段三前应先做方案确认。
- 阶段三应重点分析文档解析、chunk schema、metadata、检索接口、引用结构、安全边界和测试策略。
- 不要直接接真实 LLM 或 Agent。
