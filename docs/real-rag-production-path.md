# CareerAgent Phase 2.2 Real RAG Production Path

阶段 2.2 建立 real RAG production foundation。它不是 full production-ready RAG。

## What Changed From 2.1

- 2.1 RAG eval 只证明 current `rag_service` 可被 service-level runner 调用。
- 2.2 RAG indexing 会生成并持久化 chunk vectors。
- 2.2 search 明确区分 `lexical`、`vector`、`hybrid`，并在 sources / retrieval debug 中返回 mode、score、metadata、embedding provider/model 和 `vector_index_used`。
- 2.2 service-level RAG eval 覆盖 lexical、vector、hybrid 和 no-evidence refusal。

## Embedding Provider

Default provider: `LocalVectorEmbeddingProvider`

- provider name: `local_bow`
- model: `local-bow-v1`
- dimension: `EMBEDDING_DIMENSION`, default `384`
- no external network or API key
- stable bag-of-words feature vector with cosine similarity

This is a local vector foundation, not a final semantic embedding model like bge/OpenAI/Qwen.

## Vector Persistence

Chunk vectors are persisted in `rag_chunks`:

- `embedding_id`
- `embedding_vector`
- `embedding_provider`
- `embedding_model`
- `embedding_dim`
- `embedding_version`
- `embedding_created_at`

API responses expose metadata, not the full vector. Reindexing a document deletes old chunks and writes new chunks with fresh vectors and metadata.

## Retrieval Modes

- `lexical`: keyword overlap baseline. No vector needed.
- `vector`: query vector is generated at search time; chunk vectors are read from persisted DB fields.
- `hybrid`: foundation weighting, `0.4 lexical + 0.6 vector`.

The API accepts legacy `deterministic_lexical`, `deterministic_vector`, and `deterministic_hybrid` request aliases, but new responses use `lexical`, `vector`, and `hybrid`.

## Answer Boundary

RAG answer generation is still deterministic grounded summary. It is not LLM grounded generation.

Responses include:

- `sources`
- `citations`
- `source_refs`
- `uncertainty`
- `retrieval_mode`
- `evidence_used`
- `retrieval_debug`

No-evidence queries return no sources and `uncertainty=no_relevant_source`.

## Evaluation

Run:

```bash
backend/.venv/bin/python scripts/run_evals.py --dataset service_level --module rag --output-dir /tmp/careeragent-evals-rag
```

RAG metrics include:

- `recall_at_k_term_hit`
- `citation_present`
- `expected_source_type_match`
- `retrieval_mode_match`
- `average_top_score`
- `vector_index_used`
- `uncertainty_match`
- `case_pass`

## Still Not Production-Ready

- Local bag-of-words vectorizer is not final semantic embedding.
- SQLite JSON vectors are not a production-scale vector DB.
- No pgvector/FAISS path is enabled as production default.
- No reranker.
- No LLM grounded generation.
- Benchmark remains small.
- `raw_text` and chunk `text` remain plaintext DB fields; 2.6 must address encryption, retention, deletion proof, backup policy, and audit hardening.

Next phase: 2.5 Agent Workflow Productionization. Match Scoring and Project Rewrite have 2.4 trustworthy foundation, but remain deterministic and not production-ready.
