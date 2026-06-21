# CareerAgent 校招求职平台

CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。项目目标是把用户画像、简历版本、JD 理解、匹配评分、项目优化、面试准备、学习计划、投递管理、RAG 知识库、Agent Workflow、Bad Case 和评测体系组织成可运行、可追踪、可复查的工程链路。

CareerAgent 不是简历润色器，也不是 ChatGPT 套壳。本仓库当前处于阶段 0，只搭建可持续开发的工程骨架，不接入真实 LLM API，不实现正式 RAG，不实现正式 Agent。

## 技术栈

- Backend: FastAPI, Pydantic, Uvicorn
- Frontend: React, TypeScript, Vite
- Test: pytest, Vite build
- Deployment: Docker Compose 本地开发骨架
- Later phases: PostgreSQL, SQLAlchemy, Alembic, pgvector 或 FAISS, document parsers, LLM provider, Agent Workflow

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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/health
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

### Docker Compose

```bash
docker compose up
```

Docker Compose 只用于本地开发启动前后端服务。当前阶段不启动数据库、不接入 LLM、不挂载真实简历、真实 JD、投递记录或面试复盘。

## 环境变量

复制 `.env.example` 为 `.env` 后再按需填写本地配置。阶段 0 不需要任何真实 API Key。

```bash
cp .env.example .env
```

仓库只提交 `.env.example`，不会提交 `.env`。

## 当前阶段完成内容

阶段 0 已完成：

- 创建基础目录：`backend/`、`frontend/`、`docs/`、`evals/`、`scripts/`、`local_data/`、`docs/screenshots/`
- 创建根目录文件：`README.md`、`.gitignore`、`.env.example`、`docker-compose.yml`
- 后端初始化：FastAPI 应用、`GET /health`、基础配置、统一错误响应结构
- 前端初始化：React + TypeScript + Vite、Dashboard、Resume Center、JD Center、Match Report、简单导航
- 安全规则：忽略 `.env`、`local_data/`、uploads、vector_index、exports、logs、cache、私有数据目录和本地构建产物
- 不包含真实 LLM API 调用、真实 RAG、正式 Agent、真实 API Key 或隐私数据

## API

当前仅开放基础健康检查：

```text
GET /health
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

## 安全与隐私

- 不提交 `.env`、真实 API Key 或任何私密凭据。
- 不提交真实简历、真实 JD、投递记录、面试复盘、上传文件、向量索引、导出文件、日志和缓存。
- `local_data/` 仅用于本地运行数据，并已加入 `.gitignore`。
- 开发执行手册只作为上下文使用，不复制、不移动、不提交到仓库。
- 后续涉及日志、Agent step、RAG chunk 和评测样例时，需要默认脱敏并保留输入引用，避免保存完整隐私原文。

## 自查命令

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_health.py -q
cd frontend && npm run build
git status --short --ignored
```

## 后续阶段规划

1. 阶段一：最小可运行闭环，跑通简历上传、JD 输入、解析、匹配评分和报告展示。
2. 阶段二：数据持久化与版本管理，引入数据库、简历版本、JD 历史和匹配报告历史。
3. 阶段三：RAG 知识库，建立文档解析、chunk、metadata、向量索引、检索和来源引用。
4. 阶段四：Agent Workflow，用状态机和工具调用串联 JD 解析、匹配、项目优化、面试准备和学习计划。
5. 阶段五：投递管理与 Dashboard，绑定 JD、简历版本、状态、面试节点和复盘。
6. 阶段六：评测体系与 Bad Case，沉淀 smoke set、regression set、失败样例和回归指标。
7. 阶段七：工程化交付，补齐 Docker、文档、演示材料、安全说明和最终验收记录。
