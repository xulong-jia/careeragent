# CareerAgent 阶段三：RAG 知识库设计

## 1. 阶段三目标

阶段三目标是建立可检索、可追踪来源的 CareerAgent 知识库，为后续面试准备、学习计划和 Agent Workflow 提供 evidence source。本阶段先确保数据结构、chunk、metadata、retrieval 和 citation contract 稳定，不直接接入真实 LLM、embedding 或 vector store。

当前实现口径：v1.2 已完成 deterministic grounded answer contract、answer run persistence、KnowledgeBasePage answer history、Dashboard RAG stats 和 downstream optional refs；v1.6 建立 provider boundary；阶段 2.2 新增 local bag-of-words embedding provider、DB-persisted chunk vectors、lexical/vector/hybrid retrieval mode、`score_threshold` 和 provider metadata。默认 retrieval mode 仍是 lexical。

- 建立可检索知识库。
- 支持 RAG document 管理。
- 支持 chunking。
- 支持 metadata。
- 支持 deterministic lexical retrieval。
- 支持阶段 2.2 local vector/hybrid retrieval foundation。
- 支持 source/citation 追踪。
- 支持 RAG answer 的 deterministic answer with citations。
- 为后续面试准备、学习计划、Agent Workflow 提供 evidence source。
- 默认不接真实 LLM；local embedding provider 无网络依赖。外部 embedding provider 仅显式 opt-in。

## 2. 非目标

阶段三初期不做以下内容：

- 不接真实 LLM。
- 不接 OpenAI / DeepSeek / Qwen。
- 默认不接外部 embedding API。
- 不强制接 FAISS / pgvector；阶段 2.2 vector/hybrid 是 local persisted-vector foundation。
- 不做 Agent Workflow。
- 不做投递管理。
- 不做 Bad Case 页面。
- 不做正式 Evaluation Center。
- 不使用真实简历、真实 JD、真实投递记录做测试集。
- 不允许无来源回答。

## 3. RAG 数据模型设计

阶段 3A 只做设计，不新增表。阶段 3B 已新增 RAG ORM models、Alembic migration、schemas skeleton 和 DB smoke tests。阶段 3C 新增 document create/list/detail、deterministic chunking/indexing backend 和 chunk list API。阶段 3D 新增 lexical retrieval 和 `POST /api/rag/search`，返回 sources / score / snippet / metadata。阶段 3E 新增 deterministic RAG answer 和 `POST /api/rag/answer`，answer 复用 search sources 并在无来源时返回 uncertainty。阶段 3F 新增 KnowledgeBasePage 最小 UI，可创建 document、index、查看 chunks、search、answer with citations。阶段 3G 补充阶段三验收文档、synthetic test set 示例、README 收口和安全检查清单；v1.6 补充 local deterministic vector/hybrid readiness，但真实 LLM、外部 embedding 和生产 vector store 仍需后续单独验收。

### rag_documents

用途：保存知识库文档主记录，承载标题、来源、原文、metadata 和索引状态。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| user_id | string | 阶段三仍可使用 `default` 占位 |
| title | string | 文档标题 |
| source_type | string | manual / markdown / text / jd / interview / project / learning / company |
| source_uri | string nullable | 外部 URL、本地来源描述或业务引用 |
| raw_text | text | 文档原文 |
| metadata | json | tags、role、company、topic 等扩展信息 |
| index_status | string | pending / indexed / failed |
| chunk_count | integer | 当前索引生成的 chunk 数量 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

隐私字段：

- `raw_text`
- `metadata`

### rag_chunks

用途：保存文档切块结果，作为检索和 citation 的最小可追踪单位。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| id | string / uuid | 主键 |
| document_id | string / uuid | 外键，指向 `rag_documents.id` |
| chunk_index | integer | 同一文档内递增 |
| section | string nullable | Markdown 标题、段落区域或 section hint |
| text | text | chunk 正文 |
| token_count | integer | 粗略 token / word count |
| metadata | json | chunk 级 metadata |
| embedding_id | string nullable | 当前 chunk embedding 的非 secret id |
| embedding_vector | json nullable | DB-persisted local vector；API response 不返回本体 |
| embedding_provider | string nullable | 例如 `local_bow` 或外部 provider 名 |
| embedding_model | string nullable | 例如 `local-bow-v1` |
| embedding_dim | integer nullable | vector dimension |
| embedding_version | string nullable | embedding/vectorizer version |
| embedding_created_at | datetime nullable | reindex 时更新 |
| created_at | datetime | 创建时间 |

隐私字段：

- `text`
- `metadata`

Alembic migration 策略：

- 阶段 3B 才新增 migration。
- 阶段 3A 不新增 migration。

## 4. Source Type 与 Metadata 策略

`source_type` 初始枚举建议：

- `manual`
- `markdown`
- `text`
- `jd`
- `interview`
- `project`
- `learning`
- `company`

`metadata` 可包含：

- `tags`
- `role_category`
- `company`
- `topic`
- `domain`
- `section_hint`
- `created_by`
- `source_label`

metadata filter 用途：

- 限定检索范围，例如只检索 company 文档或 learning 文档。
- 支持后续按岗位类别、主题、公司、学习阶段过滤。
- 保证 search 和 answer 的 sources 可解释、可复查。
- 为后续 Agent Workflow 提供明确 evidence scope。

## 5. API Contract 草案

所有接口继续使用统一 response wrapper：

```json
{
  "data": {},
  "request_id": "..."
}
```

错误响应继续使用统一结构：

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request.",
    "details": {}
  },
  "request_id": "..."
}
```

阶段三初期全部 deterministic，不调用 LLM。阶段 2.2 后，RAG retrieval 可使用 persisted local vectors；answer generation 仍是 deterministic grounded summary。

### POST /api/rag/documents

输入：

- `title`
- `source_type`
- `raw_text`
- `metadata`

输出：

- document record

建议错误码：

- `validation_error`
- `rag_document_create_failed`

### GET /api/rag/documents

支持 query：

- `source_type`
- `index_status`

输出：

- document list

### GET /api/rag/documents/{doc_id}

输出：

- document detail
- `raw_text_preview`
- 不默认暴露完整 `raw_text`

建议错误码：

- `rag_document_not_found`

### POST /api/rag/documents/{doc_id}/index

输入：

- optional chunk settings

输出：

- index result
- `chunk_count`
- chunk summary

建议错误码：

- `rag_document_not_found`
- `rag_index_failed`

### GET /api/rag/chunks

支持 query：

- `doc_id`
- `source_type`
- metadata filters

输出：

- chunk list
- `text_preview`

### POST /api/rag/search

输入：

- `query`
- `top_k`
- `filters`

输出：

- sources
- `doc_id`
- `chunk_id`
- `score`
- `section`
- `snippet`
- `metadata`

### POST /api/rag/answer

输入：

- `question`
- `top_k`
- `filters`

输出：

- `answer`
- `sources`
- `uncertainty`

## 6. Repository / Service / RAG 层边界

阶段三后续建议新增文件，但阶段 3A 不实现：

- `backend/app/models/rag.py`
- `backend/app/schemas/rag.py`
- `backend/app/repositories/rag_repository.py`
- `backend/app/services/rag_service.py`
- `backend/app/rag/chunking.py`
- `backend/app/rag/retriever.py`
- `backend/app/api/rag.py`

职责边界：

- API route：HTTP request / response / dependency injection。
- service：validation、index orchestration、search orchestration、answer rule。
- repository：DB persistence / query。
- chunking：纯函数，负责文本切块。
- retriever：lexical scoring、metadata filter、top_k 排序。

边界约束：

- route 不写复杂逻辑。
- repository 不做 chunking/scoring。
- service 不直接写 SQL 细节。

## 7. Chunking 策略

最小 chunking 方案：

- Markdown 按标题和段落切。
- Plain text 按空行段落切，再按长度拆分。
- JD 文本可按 requirements / responsibilities / preferred skills 等关键词做 section hint。
- 每个 chunk 保存 `section`、`chunk_index`、`token_count`、`metadata`、`text`、`embedding_vector` 和 embedding metadata。
- 初始 chunk 长度建议 800-1500 chars。
- overlap 初始设 0 或最多 100 chars。
- 不做 PDF/DOCX parser。
- 当前做 local bag-of-words vector embedding；不调用外部 semantic embedding API。

## 8. Retrieval 策略

最小检索方案：

- lexical / keyword overlap。
- metadata filter。
- `top_k` 默认 5，最大 20。
- score 使用 overlap ratio + term frequency 的简单规则。
- no relevant source 时返回 `sources: []` 和 `uncertainty`。
- 不允许无来源回答。
- RAG answer 暂时 deterministic summary，不调用 LLM。
- answer 必须引用 `doc_id` / `chunk_id` / source snippet。

阶段 2.2 retrieval foundation：

- `retrieval_mode` 标准值为 `lexical` / `vector` / `hybrid`；后端仍接受 legacy `deterministic_*` request alias。
- `lexical` 使用 keyword overlap，不依赖 embedding。
- `vector` 使用 query vector + DB-persisted chunk vectors 做 cosine similarity；search 不重新 embed chunk text。
- `hybrid` 当前使用 `0.4 lexical + 0.6 vector` 的简单加权；v3.2 另有 reranker contract，但未校准为 production reranker。
- `rag_chunks` 保存 `embedding_id`、`embedding_vector`、`embedding_provider`、`embedding_model`、`embedding_dim`、`embedding_version`、`embedding_created_at`。API response 只返回 metadata，不返回 vector 本体。
- `score_threshold` 可过滤低分来源；无来源时仍返回 uncertainty，不编造答案。
- `retrieval_debug` 可记录 retrieval mode、embedding provider/model、vector_index_used、scores、selected chunk IDs 和版本 metadata，但不包含 raw_text 或 full chunk text。
- local/offline vectorizer 不等于最终 semantic embedding；v3.2 的 reranker、LLM grounded answer 和 benchmark 都是 foundation。FAISS/pgvector application path、真实 provider benchmark、人审 groundedness 和 production-scale vector DB 仍需后续单独设计和验收。

## 9. Source / Citation Contract

固定 source 格式：

- `doc_id`
- `chunk_id`
- `title`
- `section`
- `snippet`
- `score`
- `metadata`

规则：

- RAG answer 必须带 sources。
- 没有 sources 时必须返回 uncertainty。
- 不能把模型推断伪装成检索证据。
- 后续 LLM 接入时也必须保留 source refs。

## 10. 测试策略

阶段三测试应覆盖：

- 创建 RAG document。
- index document。
- chunk count 正确。
- chunk metadata 正确。
- search top_k 返回相关 chunk。
- search with metadata filter。
- answer 返回 sources。
- no relevant source 返回 uncertainty。
- 不存在 doc_id / chunk_id 返回统一错误。
- 使用 synthetic fixtures。
- 不提交真实数据。
- backend pytest。
- frontend build。
- docker compose config。
- Alembic upgrade。
- DB health。

## 11. 安全与隐私策略

- 不使用真实简历 / 真实 JD / 投递记录 / 面试复盘作为测试数据。
- `raw_text` 和 chunk `text` 是敏感字段。
- 后端日志不输出完整 `raw_text` 或 chunk `text`。
- 前端默认只展示 preview/snippet。
- `local_data/vector_index/` 不提交 Git。
- API Key 只允许在 `.env`，本仓库只提交 `.env.example`。
- `LLM_API_KEY` / `EMBEDDING_API_KEY` 只允许本地 env 注入，health 和 logs 不返回 key。
- 默认 provider mode 必须 keyless deterministic 可运行。
- RAG answer 不得无来源编造。
- synthetic test data 必须可公开。

## 12. 阶段三子阶段拆分

- 3A：RAG 设计文档与边界确认。
- 3B：`rag_documents` / `rag_chunks` models + Alembic migration + DB smoke tests。
- 3C：document create/list/detail + chunking/indexing backend + chunk list API。
- 3D：lexical retrieval + `POST /api/rag/search`。
- 3E：deterministic RAG answer with citations + no-source behavior。
- 3F：KnowledgeBasePage 最小 UI。
- 3G：RAG synthetic test set、验收文档、安全检查、README 更新，作为阶段三收口。

## 13. 风险与规避

- embedding 过早接入导致复杂度上升：先做 lexical retriever abstraction，embedding retriever 留到后续。
- LLM 过早接入导致 hallucination：answer 先 deterministic，且无来源时只返回 uncertainty。
- chunk 太长或太短：用 800-1500 chars 初始范围，并用 synthetic fixtures 固定边界。
- metadata 缺失：document 和 chunk 都要求 metadata 字段，允许空对象但不允许缺字段。
- citation 不稳定：固定 source contract，所有 answer 使用同一 sources 结构。
- 真实隐私数据进入 RAG：测试只使用 synthetic data，提交前做安全扫描。
- vector index 文件误提交：继续依赖 `.gitignore`，提交前扫描 `vector_index/`。
- RAG answer 无来源：无 sources 时必须返回 uncertainty，不返回确定结论。
- 前端复杂化：后端 API 稳定后再做 KnowledgeBasePage。
- 与后续 Agent 混淆：阶段三只做 knowledge retrieval 和 answer contract，不做 workflow orchestration。

## 14. 阶段 3B 最小开发计划

阶段 3B 只应该做：

- 新增 `rag_documents` / `rag_chunks` ORM models。
- 新增 Alembic migration。
- 新增 schemas skeleton。
- 新增 repository skeleton 或最小 DB smoke tests。
- 不实现 RAG API。
- 不做 chunking。
- 不做 retrieval。
- 不接 embedding。
- 不接 LLM。
- 不做前端。
