# CareerAgent 校招求职平台

CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。项目目标是把用户画像、简历版本、JD 理解、匹配评分、项目优化、面试准备、学习计划、投递管理、RAG 知识库、Agent Workflow、Bad Case 和评测体系组织成可运行、可追踪、可复查的工程链路。

CareerAgent 不是简历润色器，也不是 ChatGPT 套壳。本仓库当前处于阶段 3G，已在 SQLite + SQLAlchemy 基础上支持 Resume / JD / Match Report 持久化、Resume Version 历史管理，以及 deterministic RAG knowledge base。当前 RAG 支持 document、chunking/indexing、lexical search、deterministic answer with citations 和 KnowledgeBasePage，但仍不接入真实 LLM、embedding、vector store 或 Agent。

## 技术栈

- Backend: FastAPI, Pydantic, Uvicorn, SQLAlchemy, Alembic, SQLite
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

Docker Compose 只用于本地开发启动前后端服务。当前阶段默认使用本地 SQLite，不接入 LLM、embedding、vector store，不挂载真实简历、真实 JD、真实文档、投递记录或面试复盘。

## 环境变量

复制 `.env.example` 为 `.env` 后再按需填写本地配置。阶段二默认使用本地 SQLite，不需要任何真实 API Key。

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

阶段 1A / 1B / 1C 已完成：

- 阶段一 Resume 占位接口：上传校验、列表、详情。
- 阶段一 JD 占位接口：创建、列表、详情、deterministic profile。
- 阶段一 Match 占位接口：运行、列表、详情、deterministic rule score。
- 阶段一前端内存闭环：上传 Resume、创建 JD、运行 Match、展示报告。
- 内存 Mock Store：后端重启后数据会丢失。
- 契约加固：统一成功/错误响应、基础错误路径测试、服务层拆分。
- 最小文本提取：`.md`、`.markdown`、`.txt` 真实读取 UTF-8 文本。
- Parser placeholder：`.pdf`、`.docx` 返回明确 placeholder、extraction status、method 和 warnings，不假装真实解析成功。
- 安全边界：不保存真实上传文件到 Git，不调用真实 LLM/RAG/Agent。

阶段 2A / 2B / 2C / 2D / 2E / 2F / 2G 已完成：

- 2A：完成阶段二持久化与版本管理设计文档。
- 2B：新增 SQLite + SQLAlchemy + Alembic 基础设施、ORM skeleton、初始 migration 和 DB health check。
- 2C：Resume / JD 主路径已切换为 SQLite 持久化，创建 Resume 时生成 initial resume version，创建 JD 时生成 job profile。
- 2D：新增 Resume Version 后端 API，支持版本历史、详情、clone 和 archive；archive 是软归档，不删除历史内容。
- 2E：Match Report 主路径已切换为 SQLite 持久化，报告绑定 `resume_version_id + jd_id`，`GET /api/matches` 返回 DB 历史报告。
- 2F：前端展示 DB-backed Resume / JD / Match 历史；Resume Center 支持 versions 查看、clone 和 archive；Match Report 支持历史查看。
- 2G：补充阶段二验收文档、安全检查说明和 README 收口说明。
- 当前复杂 diff、多版本对比图表、同一 JD 多版本对比页面仍未实现，留到后续阶段。

阶段二验收文档：[docs/phase-2-acceptance.md](docs/phase-2-acceptance.md)

阶段 3A / 3B / 3C / 3D / 3E / 3F / 3G 已完成：

- 3A：完成 RAG 知识库设计文档与边界确认。
- 3B：新增 `rag_documents` / `rag_chunks` ORM models、Alembic migration、schema skeleton 和 DB smoke tests。
- 3C：新增 RAG document create / list / detail、deterministic chunking / indexing backend 和 chunks list API。
- 3D：新增 deterministic lexical retrieval 和 `POST /api/rag/search`，返回 sources / score / snippet / metadata。
- 3E：新增 deterministic RAG answer 和 `POST /api/rag/answer`，有来源时 grounded，无来源时返回 uncertainty。
- 3F：新增 KnowledgeBasePage 最小 UI，支持创建 document、index、查看 chunks、search 和 answer with citations。
- 3G：补充阶段三 RAG 验收文档、synthetic test set 示例、安全检查说明和 README 收口说明。
- 当前不包含真实 LLM、embedding、vector store、Agent Workflow、复杂 RAG evaluation dashboard 或 Interview / Study Plan 正式集成。

阶段三设计文档：[docs/rag-design.md](docs/rag-design.md)

阶段三验收文档：[docs/phase-3-rag-acceptance.md](docs/phase-3-rag-acceptance.md)

## API

当前开放的阶段三工作台 API：

```text
GET /health
GET /api/db/health
POST /api/resumes/upload
GET /api/resumes
GET /api/resumes/{resume_id}
GET /api/resumes/{resume_id}/versions
GET /api/resume-versions/{version_id}
POST /api/resume-versions/{version_id}/clone
PATCH /api/resume-versions/{version_id}/archive
POST /api/jobs
GET /api/jobs
GET /api/jobs/{jd_id}
POST /api/matches/run
GET /api/matches
GET /api/matches?jd_id={jd_id}
GET /api/matches?resume_version_id={resume_version_id}
GET /api/matches/{match_report_id}
POST /api/rag/documents
GET /api/rag/documents
GET /api/rag/documents/{doc_id}
POST /api/rag/documents/{doc_id}/index
GET /api/rag/chunks
POST /api/rag/search
POST /api/rag/answer
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

### 手动跑通阶段二持久化闭环

1. 启动后端和前端。
2. 打开 `http://localhost:5173`。
3. 进入 Resume Center，上传 `.md`、`.markdown` 或 `.txt` mock resume，确认 raw text preview 展示真实 UTF-8 文本。
4. 进入 JD Center，填写 company、job title、location 和 raw JD text，创建 JD。
5. 进入 Match Report，点击 `Run Match`。
6. 查看总分、维度分、evidence、gaps 和 rewrite priorities。

PDF / DOCX 当前阶段也可以上传用于接口契约检查，但不会做真实文本解析。返回结果会包含：

- `extraction_status`: `parser_placeholder`
- `extraction_method`: `pdf_parser_placeholder` 或 `docx_parser_placeholder`
- `extraction_warnings`: 说明对应 parser 尚未接入

Markdown / txt 返回结果会包含：

- `extraction_status`: `extracted`
- `extraction_method`: `utf8_md_decode`、`utf8_markdown_decode` 或 `utf8_txt_decode`
- `raw_text_preview`: 真实读取到的 UTF-8 文本预览

当前阶段说明：

- Deterministic：结构化简历、JD 解析和匹配评分仍是 deterministic 规则，不调用真实 LLM。
- SQLite 持久化：Resume / JD 数据默认保存到 `DATABASE_URL` 指定位置，默认 `local_data/careeragent.db`。
- Match Report 持久化：报告默认绑定 `resume_version_id + jd_id`，并保存到 SQLite。
- 版本管理：Resume Version 已支持历史查询、详情、clone 和 archive；archive 是软归档，不删除历史内容。
- 前端展示：Resume Center 可查看 versions、clone、archive；Match Report 可查看 DB 历史和详情。
- 版本边界：复杂版本 diff / compare UI、同一 JD 多版本对比页面仍未实现，留到后续阶段。
- 无真实 LLM：没有 OpenAI、DeepSeek、Qwen 或其他模型调用。
- RAG 知识库：支持 document 管理、deterministic chunking/indexing、lexical search、deterministic answer with citations 和 KnowledgeBasePage。
- RAG 边界：没有真实 embedding、FAISS、pgvector、vector store、真实 LLM answer、reranker 或 RAG evaluation dashboard。
- 无 Agent：没有 Agent Workflow、agent runs 或 agent steps。

## 安全与隐私

- 不提交 `.env`、真实 API Key 或任何私密凭据。
- 不提交真实简历、真实 JD、投递记录、面试复盘、上传文件、向量索引、导出文件、日志和缓存。
- `local_data/` 仅用于本地运行数据，并已加入 `.gitignore`。
- 开发执行手册只作为上下文使用，不复制、不移动、不提交到仓库。
- RAG 测试和验收只使用 synthetic data；前端默认展示 preview / snippet，不默认展示完整 raw_text 或完整 chunk text。
- 后续涉及日志、Agent step、RAG chunk 和评测样例时，需要默认脱敏并保留输入引用，避免保存完整隐私原文。

## 自查命令

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose config
PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
git status --short --branch
git diff --check
```

## 后续阶段规划

1. 阶段一：最小可运行闭环，跑通简历上传、JD 输入、解析、匹配评分和报告展示。
2. 阶段二：数据持久化与版本管理，引入数据库、简历版本、JD 历史和匹配报告历史。
   - 设计文档：[docs/phase-2-persistence-design.md](docs/phase-2-persistence-design.md)
   - 验收文档：[docs/phase-2-acceptance.md](docs/phase-2-acceptance.md)
   - Release notes：[docs/release-notes-v0.2.0-persistence.md](docs/release-notes-v0.2.0-persistence.md)
3. 阶段三：RAG 知识库，建立 RAG document、chunk、metadata、lexical search、deterministic answer 和来源引用。
   - 设计文档：[docs/rag-design.md](docs/rag-design.md)
   - 验收文档：[docs/phase-3-rag-acceptance.md](docs/phase-3-rag-acceptance.md)
   - Release notes：[docs/release-notes-v0.3.0-rag.md](docs/release-notes-v0.3.0-rag.md)
4. 阶段四：Agent Workflow，用状态机和工具调用串联 JD 解析、匹配、项目优化、面试准备和学习计划。
   - 设计文档：[docs/agent-workflow-design.md](docs/agent-workflow-design.md)
5. 阶段五：投递管理与 Dashboard，绑定 JD、简历版本、状态、面试节点和复盘。
6. 阶段六：评测体系与 Bad Case，沉淀 smoke set、regression set、失败样例和回归指标。
7. 阶段七：工程化交付，补齐 Docker、文档、演示材料、安全说明和最终验收记录。
