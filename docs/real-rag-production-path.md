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

v3.2 adds:

- `LocalSemanticEmbeddingProvider` / `EMBEDDING_PROVIDER=local_semantic` as an offline semantic-provider-shaped foundation.
- OpenAI-compatible embedding retry and provider config metadata.
- non-secret embedding metadata: provider/model/dim/version/provider_config_id/vector_source/semantic/input_hash/created_at.

The offline semantic provider is still not a production semantic model. Real OpenAI/Qwen/bge-m3 style providers must be enabled with runtime secrets and benchmarked separately.

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

Default RAG answer generation is still deterministic grounded summary.
v3.2 adds optional `answer_mode=llm_grounded`, which uses a schema-validated provider output contract, citation validation, prompt/model metadata and no-evidence refusal. With default settings it falls back through the deterministic provider and does not call the network.

Responses include:

- `sources`
- `citations`
- `source_refs`
- `uncertainty`
- `retrieval_mode`
- `evidence_used`
- `retrieval_debug`

v3.2 `retrieval_debug` also includes reranker mode/model/applied, answer mode and safe run config metadata.

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

v3.2 benchmark foundation:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_evals.py --dataset benchmark --module rag --output-dir /tmp/careeragent-evals-benchmark-rag-v32
```

Benchmark RAG metrics include `recall_at_k`, `mrr`, `precision_at_k`, `citation_coverage`, `source_type_match`, `no_evidence_refusal_accuracy`, `reranker_improvement_rate`, `groundedness`, `unsupported_claim_rate`, `citation_required_pass_rate`, `refusal_accuracy` and `answer_schema_pass_rate`.

## Still Not Production-Ready

- Local bag-of-words vectorizer is not final semantic embedding.
- SQLite JSON vectors are not a production-scale vector DB.
- No pgvector/FAISS application path is enabled as production default.
- Reranker exists as a contract/foundation path, not a calibrated production reranker.
- LLM grounded answer exists as optional schema-validated path, not default production answer generation.
- Benchmark is larger synthetic foundation, not real anonymized production benchmark.
- v3.0 encrypts RAG document `raw_text`, chunk `text` and persisted answer-run private fields at the repository write path, but KMS, key rotation backfill, retention, backup purge, legal hold and centralized audit hardening remain production blockers.

v3.2 Production AI Quality Foundation is completed as foundation candidate. Next phase should be v3.3 Frontend Productization & End-to-End Experience. Match Scoring, Project Rewrite and current RAG retrieval remain foundation quality and not production-ready semantic AI.
