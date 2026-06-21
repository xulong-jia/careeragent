# CareerAgent v0.3.0-rag Release Notes

## 1. 版本定位

CareerAgent 是面向校招学生和留学生回国求职场景的 AI 求职工作台。`v0.3.0-rag` 是阶段三 RAG 知识库完成节点。

本版本在 `v0.2.0-persistence` 的 DB-backed 工作台基础上，新增 deterministic RAG knowledge base。当前 RAG 不接真实 LLM、不接 embedding、不接 vector store。

## 2. 已继承的 v0.2.0-persistence 能力

- SQLite + SQLAlchemy + Alembic 数据库基础设施。
- Resume 持久化。
- Resume Version 初始创建、list、detail、clone、archive。
- JD 持久化。
- Job Profile 持久化。
- Match Report 持久化。
- Match Report 历史查询。
- 前端持久化 Resume / JD / Match 工作台。
- `v0.2.0-persistence` tag 已存在。

## 3. 阶段三新增能力

- `rag_documents` / `rag_chunks` 数据表。
- RAG ORM models。
- Alembic migration。
- RAG schemas。
- RAG document create / list / detail API。
- RAG document indexing API。
- Deterministic chunking。
- Chunks list API。
- Lexical search API。
- Search sources / score / snippet / metadata。
- Deterministic answer API。
- Answer with citations / sources。
- No-source behavior。
- KnowledgeBasePage 最小 UI。
- 前端 RAG API client。
- 前端 RAG TypeScript types。
- 前端只展示 preview / snippet。

## 4. RAG API 清单

- `POST /api/rag/documents`：创建 synthetic RAG document。
- `GET /api/rag/documents`：查询 RAG documents 列表。
- `GET /api/rag/documents/{doc_id}`：查询 document detail，默认返回 preview。
- `POST /api/rag/documents/{doc_id}/index`：对 document 执行 deterministic chunking / indexing。
- `GET /api/rag/chunks`：查询 chunks，默认返回 text preview。
- `POST /api/rag/search`：执行 deterministic lexical search，返回 sources / score / snippet / metadata。
- `POST /api/rag/answer`：基于 search sources 生成 deterministic answer with citations。

## 5. KnowledgeBasePage 能力

- 可创建 synthetic RAG document。
- 可查看 documents list。
- 可查看 document preview。
- 可 index document。
- 可查看 chunks。
- 可执行 lexical search。
- 可查看 sources / score / snippet。
- 可执行 deterministic answer。
- 可查看 grounded / uncertainty / citations。
- 不默认展示完整 raw_text 或完整 chunk text。

## 6. 当前不包含的能力

- 真实 LLM 接入。
- OpenAI / DeepSeek / Qwen API。
- Embedding。
- FAISS / pgvector / vector store。
- Reranker。
- PDF / DOCX parser。
- Richer KnowledgeBasePage。
- RAG 与 Interview / Study Plan 集成。
- RAG evaluation dashboard。
- Agent Workflow。
- 投递管理。
- Bad Case 页面。
- Evaluation Center。
- 自动投递。

## 7. 安全与隐私说明

- 不提交 `.env`。
- 不提交 `local_data/`。
- 不提交 SQLite 数据库文件。
- 不提交 `vector_index/`。
- 不提交真实简历、真实 JD、真实文档、投递记录、面试复盘。
- 不提交 API Key。
- 不提交 `CareerAgent_最终版项目开发执行手册.md`。
- 前端默认只展示 `raw_text_preview` / `text_preview` / `snippet`。
- RAG answer 无来源时不编造。
- DB health 不输出完整 `DATABASE_URL`。
- 测试使用 synthetic fixtures。

## 8. 验收状态

- 阶段一总验收通过。
- 阶段二总验收通过。
- 阶段三总验收通过。
- 后端 pytest 通过。
- 前端 build 通过。
- `docker compose config` 通过。
- Alembic upgrade 通过。
- DB health 通过。
- 安全扫描通过。

## 9. 后续阶段

下一阶段建议进入阶段四：Agent Workflow。

进入阶段四前应先做方案确认。阶段四应重点分析 Agent Workflow 状态机、`agent_runs` / `agent_steps`、工具边界、错误重试、审计日志和隐私保护。

不要直接接真实 LLM Agent。不要做自动投递。不要做未经约束的自由 Agent。
