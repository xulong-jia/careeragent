# CareerAgent 阶段二验收报告

## 1. 阶段二目标回顾

阶段二目标是把 CareerAgent 从阶段一的内存 Mock store 升级为 DB-backed 持久化工作台。本阶段仍然不接入真实 LLM、RAG 或 Agent，重点是让核心求职工作流可保存、可追踪、可复查。

- 从内存 Mock store 升级为 DB-backed 持久化工作台。
- 保存 Resume / Resume Version / JD / Job Profile / Match Report。
- 支持刷新页面或重启服务后数据不丢。
- 支持简历版本历史、clone、archive。
- 支持 Match Report 历史查询。
- 支持前端最小工作台展示。

## 2. 已完成功能清单

- SQLite + SQLAlchemy + Alembic 基础设施。
- `GET /api/db/health` DB health 检查。
- Resume 持久化。
- Resume Version 初始创建。
- Resume Version list / detail / clone / archive。
- JD 持久化。
- Job Profile 持久化。
- Match Report 持久化。
- Match Report 历史查询。
- 前端 Resume / JD / Match 持久化展示。
- 前端 Resume Version 查看、clone、archive。
- Dashboard 持久化数量入口。

## 3. 当前不包含的能力

当前阶段不包含以下能力：

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

## 4. 数据库与迁移说明

- 默认 SQLite 数据库路径：`local_data/careeragent.db`。
- `local_data/` 不提交 Git。
- 数据库结构使用 Alembic migration 管理。
- 当前 migration 列表：
  - `20260621_0001_create_phase_two_core_tables.py`
  - `20260621_0002_add_resume_version_target_role.py`
- 当前核心表：
  - `resumes`
  - `resume_versions`
  - `job_descriptions`
  - `job_profiles`
  - `match_reports`

## 5. 本地启动与迁移步骤

建议从项目根目录 `/Users/jiaxulong/Documents/CareerAgent` 执行以下命令。

创建并激活 backend venv：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

执行 Alembic migration：

```bash
PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

启动 FastAPI：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

检查 DB health：

```bash
curl http://localhost:8000/api/db/health
```

启动 React frontend：

```bash
cd frontend
npm install
npm run dev
```

前端默认访问：

```text
http://localhost:5173
```

## 6. 手动验收路径

1. 启动后端。
2. 执行 Alembic migration。
3. 打开 `GET /api/db/health`，确认数据库可访问且核心表存在。
4. 启动前端并打开 `http://localhost:5173`。
5. 进入 Resume Center，上传 `.md` 或 `.txt` Resume。
6. 查看 Resume list，确认新 Resume 出现在列表中。
7. 选择 Resume，查看 Resume versions。
8. clone version，输入新的 `version_name` 和可选 `target_role`。
9. archive version，确认 archived version 仍在列表中且可查看详情。
10. 进入 JD Center，创建 JD。
11. 查看 JD list 和 job profile 摘要。
12. 进入 Match Report，使用当前 Resume / JD 运行 match。
13. 查看 match history。
14. 查看 match detail，包括 score、dimension scores、evidence、strengths、gaps 和 rewrite priorities。
15. 重启后端后再次打开前端，确认 Resume / JD / Match 历史仍然存在。

## 7. 自动化检查命令

后端测试：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

前端 build：

```bash
cd frontend
npm run build
```

Docker Compose 配置检查：

```bash
docker compose config
```

Alembic upgrade：

```bash
PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

DB health：

```bash
curl http://localhost:8000/api/db/health
```

Git 状态：

```bash
git status --short --branch
```

空白和 patch 检查：

```bash
git diff --check
```

敏感文件路径扫描：

```bash
git ls-files | rg '(^|/)(\.env|local_data|node_modules|dist|\.venv|__pycache__|uploads|vector_index|exports|logs|cache)(/|$)|\.(db|sqlite|sqlite3)$|CareerAgent_最终版项目开发执行手册\.md|真实简历|真实JD|投递记录|面试复盘'
```

API Key 扫描：

```bash
rg -n --hidden --glob '!.git/**' --glob '!frontend/node_modules/**' --glob '!backend/.venv/**' --glob '!frontend/dist/**' --glob '!**/__pycache__/**' --glob '!.pytest_cache/**' --glob '!local_data/**' --glob '!backend/local_data/**' '(sk-[A-Za-z0-9_-]{10,}|OPENAI_API_KEY\s*=\s*[^\s#]+|DEEPSEEK_API_KEY\s*=\s*[^\s#]+|QWEN_API_KEY\s*=\s*[^\s#]+|api[_-]?key\s*=\s*[^\s#]+)' .
```

## 8. 安全与隐私检查

- `.env` 不提交。
- `local_data/` 不提交。
- `*.db` / `*.sqlite` / `*.sqlite3` 不提交。
- `node_modules/` 不提交。
- `frontend/dist/` 不提交。
- `backend/.venv/` 不提交。
- `__pycache__/` 不提交。
- 真实简历不提交。
- 真实 JD 不提交。
- API Key 不提交。
- 投递记录不提交。
- 面试复盘不提交。
- `CareerAgent_最终版项目开发执行手册.md` 不提交。
- 前端默认只展示 `raw_text_preview`，不展示完整 `raw_text`。
- 后端错误和日志不输出完整 `raw_text` / JD `raw_text`。
- DB health 不输出完整 `DATABASE_URL`。

## 9. 阶段二验收标准

- 后端测试通过。
- 前端 build 通过。
- `docker compose config` 通过。
- Alembic upgrade 通过。
- DB health 通过。
- Resume / JD / Match 数据可持久化。
- Resume Version clone / archive 行为正确。
- Match Report 绑定 `resume_version_id + jd_id`。
- 前端可展示持久化数据。
- 安全扫描无敏感文件。

## 10. 阶段二结论

阶段二可以视为通过。当前项目已从 Mock demo 升级为 DB-backed 持久化工作台，具备 Resume / JD / Resume Version / Match Report 的最小持久化闭环和前端展示能力。

下一阶段可以进入阶段三 RAG 知识库，但进入前应先做阶段三方案确认，不要直接进入阶段三开发。
