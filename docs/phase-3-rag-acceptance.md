# CareerAgent 阶段三 RAG 知识库验收报告

## 1. 阶段三目标回顾

阶段三目标是建立一个可持久化、可检索、可追踪来源的 RAG 知识库，为后续面试准备、学习计划和 Agent Workflow 提供 evidence source。本阶段不接真实 LLM、不接 embedding、不接 FAISS / pgvector / vector store，而是先跑通 deterministic RAG contract。

阶段三重点能力：

- 保存 RAG documents。
- 将 document 切分为可追踪的 chunks。
- 支持 metadata。
- 支持 deterministic lexical search。
- 支持 answer with citations。
- 无相关来源时返回明确 no-source behavior。
- 前端提供 KnowledgeBasePage 最小 UI。
- 全流程默认使用 synthetic sample documents，不使用真实简历、真实 JD、投递记录或面试复盘。

## 2. 已完成功能清单

- RAG 设计文档与边界确认。
- `rag_documents` / `rag_chunks` ORM models。
- Alembic migration：`20260621_0003_create_rag_tables.py`。
- RAG schemas skeleton 和后续 request / response schemas。
- RAG document create / list / detail API。
- RAG document indexing API。
- Deterministic chunking。
- Chunks 写入 SQLite。
- Chunks list API。
- Deterministic lexical retrieval。
- `POST /api/rag/search`。
- Search response 返回 sources / score / snippet / metadata。
- Metadata filter。
- Top-k retrieval。
- No-source search behavior：`sources=[]` 和 `uncertainty="no_relevant_source"`。
- Deterministic answer builder。
- `POST /api/rag/answer`。
- Answer response 返回 grounded / uncertainty / sources / citations。
- Answer 不基于无来源内容编造。
- KnowledgeBasePage 最小 UI。
- 前端 RAG API client。
- 前端 RAG TypeScript types。
- Dashboard / navigation 增加 Knowledge Base 入口。
- 前端默认展示 preview / snippet，不默认展示完整 raw_text 或完整 chunk text。

## 3. 当前不包含的能力

当前阶段不包含：

- 真实 LLM 接入。
- OpenAI / DeepSeek / Qwen API。
- Embedding。
- FAISS / pgvector / vector store。
- Reranker。
- PDF / DOCX parser。
- 复杂文档上传。
- Agent Workflow。
- 投递管理。
- Bad Case 页面。
- Evaluation Center。
- 登录 / 权限系统。
- RAG evaluation dashboard。
- RAG 与 Interview / Study Plan 的正式集成。
- 自动简历优化。
- 自动投递。

## 4. RAG API 清单

当前阶段三 RAG API：

```text
POST /api/rag/documents
GET /api/rag/documents
GET /api/rag/documents/{doc_id}
POST /api/rag/documents/{doc_id}/index
GET /api/rag/chunks
POST /api/rag/search
POST /api/rag/answer
```

API contract：

- 所有接口继续使用统一 response wrapper。
- Document list / detail 默认返回 `raw_text_preview`，不默认暴露完整 `raw_text`。
- Chunk list 默认返回 `text_preview`，不默认暴露完整 chunk text。
- Search 返回 sources / score / snippet / metadata。
- Answer 返回 deterministic answer / grounded / uncertainty / sources。
- 无 sources 时 answer 必须 `grounded=false`，并返回 `uncertainty="no_relevant_source"`。
- Search / answer 不调用真实 LLM、embedding 或 vector store。

## 5. KnowledgeBasePage 验收路径

本地手动验收路径：

1. 启动后端。
2. 执行 Alembic migration。
3. 打开 DB health，确认数据库可用。
4. 启动前端。
5. 打开 `http://localhost:5173`。
6. 进入 Knowledge Base。
7. 创建 synthetic RAG document。
8. 查看 documents list。
9. 选择 document，查看 detail / preview。
10. 点击 index document。
11. 查看 chunks list，确认只展示 text preview。
12. 输入 search query。
13. 查看 sources / score / snippet / metadata。
14. 输入 answer question。
15. 查看 deterministic answer / grounded / uncertainty / sources。
16. 输入无关问题。
17. 确认 no-source behavior：无来源时不编造答案。
18. 重启后端后确认 documents / chunks 仍然存在。

## 6. Synthetic test set 示例

以下示例只用于本地验收和测试，不包含真实简历、真实 JD、投递记录、面试复盘或 API Key。

### 6.1 Backend interview preparation synthetic note

Title:

```text
Backend Interview Preparation Notes
```

Source type:

```text
interview
```

Raw text example:

```text
# Backend Interview Preparation

For FastAPI backend interviews, candidates should explain request validation, dependency injection, error handling, and database session lifecycle. A strong answer should mention transaction boundaries and avoiding sensitive raw text in logs.

## System Design

When discussing a resume matching platform, focus on API contracts, persistence, version history, and safe evidence tracking. Avoid claiming LLM-based reasoning unless the system actually calls a model.
```

Metadata example:

```json
{
  "topic": "backend_interview",
  "role_category": "backend",
  "tags": ["fastapi", "system_design", "transactions"]
}
```

Search query:

```text
FastAPI database session transaction boundaries
```

Answer question:

```text
What should a candidate mention when explaining FastAPI backend persistence?
```

No-source query:

```text
How should I prepare for a quantum hardware lab interview?
```

### 6.2 Resume matching synthetic note

Title:

```text
Resume Matching Rubric Synthetic Note
```

Source type:

```text
learning
```

Raw text example:

```text
# Resume Matching Rubric

A resume match report should separate required skills, preferred skills, responsibilities, evidence, strengths, gaps, rewrite priorities, and risk flags. Scores should be explainable and linked to source snippets whenever possible.

## Versioning

Resume versions should not be silently overwritten. Clone operations must insert a new version, while archive operations should preserve historical content.
```

Metadata example:

```json
{
  "topic": "resume_matching",
  "role_category": "general",
  "tags": ["resume", "matching", "versioning"]
}
```

Search query:

```text
resume version archive preserve history
```

Answer question:

```text
Why should resume versions not be silently overwritten?
```

No-source query:

```text
What is the salary range for a real company offer?
```

### 6.3 RAG safety synthetic note

Title:

```text
RAG Safety Synthetic Note
```

Source type:

```text
manual
```

Raw text example:

```text
# RAG Safety

A RAG answer must cite retrieved sources. If no relevant source is found, the system should return uncertainty instead of fabricating an answer. Search results should expose snippets, document identifiers, chunk identifiers, scores, and metadata.

## Privacy

Do not use real resumes, real job descriptions, application records, interview retrospectives, or API keys as test data. Local database files and vector indexes must not be committed to Git.
```

Metadata example:

```json
{
  "topic": "rag_safety",
  "tags": ["citations", "privacy", "no_source"]
}
```

Search query:

```text
RAG answer cite retrieved sources no relevant source
```

Answer question:

```text
What should the RAG system do when no relevant source is found?
```

No-source query:

```text
Which private API key should be used in production?
```

## 7. 自动化检查命令

建议在阶段三验收时执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose config
PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
curl http://localhost:8000/api/db/health
git status --short --branch
git diff --check
```

安全扫描建议：

```bash
git ls-files | rg '(^|/)(\.env|local_data|node_modules|dist|\.venv|__pycache__|uploads|vector_index|exports|logs|cache)(/|$)|\.(db|sqlite|sqlite3)$|CareerAgent_最终版项目开发执行手册\.md' || true
rg -n --hidden --glob '!.git/**' --glob '!local_data/**' --glob '!**/__pycache__/**' '(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=\s*[^\s#]+|DEEPSEEK_API_KEY\s*=\s*[^\s#]+|QWEN_API_KEY\s*=\s*[^\s#]+)' . || true
```

## 8. 安全与隐私检查

提交前必须确认：

- `.env` 未提交。
- `local_data/` 未提交。
- `*.db` / `*.sqlite` / `*.sqlite3` 未提交。
- `vector_index/` 未提交。
- `node_modules/` 未提交。
- `frontend/dist/` 未提交。
- `backend/.venv/` 未提交。
- `__pycache__/` 未提交。
- `uploads/`、`exports/`、`logs/`、`cache/` 未提交。
- 真实简历未提交。
- 真实 JD 未提交。
- 真实文档未提交。
- API Key 未提交。
- 投递记录未提交。
- 面试复盘未提交。
- `CareerAgent_最终版项目开发执行手册.md` 未提交。
- 前端只默认展示 `raw_text_preview` / `text_preview` / `snippet`。
- RAG answer 不无来源编造。
- DB health 不输出完整 `DATABASE_URL`。

## 9. 阶段三验收标准

阶段三通过标准：

- 后端 pytest 通过。
- 前端 `npm run build` 通过。
- `docker compose config` 通过。
- Alembic `upgrade head` 通过。
- DB health 通过。
- RAG document 可创建。
- RAG document 可 list / detail。
- Document indexing 可生成 chunks。
- Chunks 可写入 DB 并查询。
- Search 可返回 top-k sources / score / snippet / metadata。
- Search 支持 metadata filter。
- Answer 可返回 deterministic grounded answer 和 citations。
- 无相关来源时返回 `grounded=false` 和 `uncertainty="no_relevant_source"`。
- KnowledgeBasePage 可完成 create / index / chunks / search / answer 手动验收。
- 不接真实 LLM。
- 不接 embedding。
- 不接 vector store。
- 不提交 DB 文件、`local_data/`、`vector_index/`、隐私文件、API Key、真实数据或执行手册。

## 10. 阶段三结论

阶段三可以视为通过：CareerAgent 已从 DB-backed persistence 工作台升级为具备 deterministic RAG knowledge base 的可演示系统。

当前 RAG 能力是 deterministic、source-grounded、可追踪的最小闭环，不包含真实 LLM、embedding、vector store 或 Agent Workflow。

下一步建议先做阶段三总验收确认，并考虑新增 `v0.3.0-rag` release notes。进入阶段四 Agent Workflow 前，应先做阶段四方案确认，不要直接开发 Agent。
