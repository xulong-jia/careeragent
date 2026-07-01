# CareerAgent v1.6 AI Providers

v1.6 adds a provider boundary, not a mandatory production LLM rollout.

## Default Mode

- `AI_PROVIDER_MODE=deterministic`
- `LLM_PROVIDER=deterministic`
- `EMBEDDING_PROVIDER=local`
- `ENABLE_REAL_LLM=false`
- `ENABLE_REAL_EMBEDDING=false`

This mode needs no API key and is what tests, Docker Compose, and local demos use by default.

## LLM Provider

Backend providers live under `backend/app/ai/`.

- `DeterministicLLMProvider` validates caller-provided fallback JSON with a Pydantic schema.
- `OpenAICompatibleLLMProvider` can call `/chat/completions` only when explicitly enabled and fully configured.

Required real-provider env:

```bash
ENABLE_REAL_LLM=true
LLM_PROVIDER=openai_compatible
LLM_API_BASE_URL=https://provider.example/v1
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT_SECONDS=30
LLM_TEMPERATURE=0.0
```

All structured output must pass Pydantic validation through `validate_structured_output`.

## Embedding Provider

- `LocalVectorEmbeddingProvider` uses stable local bag-of-words vectors and has no network dependency.
- `LocalSemanticEmbeddingProvider` is a v3.2 offline semantic-provider-shaped foundation. It is useful for contract tests and metadata, not a production semantic model.
- `DeterministicEmbeddingProvider` remains as a backwards-compatible alias for older local tests/config.
- `OpenAICompatibleEmbeddingProvider` can call `/embeddings` only when explicitly enabled and fully configured. v3.2 adds one retry and provider config metadata.

Phase 2.2 persists chunk vectors in `rag_chunks`. v3.2 also stores non-secret embedding metadata such as provider config id, vector source, semantic flag and input hash. Local vector search is a production foundation, not a final semantic embedding provider.

Required real-provider env:

```bash
ENABLE_REAL_EMBEDDING=true
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_BASE_URL=https://provider.example/v1
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_DIMENSION=384
EMBEDDING_PROVIDER_CONFIG_ID=prod-embedding-provider-v1
```

## RAG v3.2 Controls

```bash
RAG_RERANKER_MODE=none
RAG_RERANKER_MODEL=local-score-v1
RAG_ANSWER_MODE=deterministic_summary
```

Supported answer modes:

- `deterministic_summary`
- `llm_grounded`

Supported reranker modes:

- `none`
- `local_score`
- `provider`

`llm_grounded` is schema-validated and citation-checked, but it is still an
optional foundation path until real providers, real anonymized datasets and human
review gates are completed.

## Safety Rules

- Do not commit `.env` or real API keys.
- Do not log prompts, full resume/JD raw text, chunk full text, `reflection`, `interview_notes`, or provider keys.
- Tests must not call external APIs.
- Real provider mode should be enabled only after running the smoke evals and reviewing cost/rate limits.
- Real provider outputs must be written to `/tmp` or ignored artifacts until privacy, redaction and review are complete.
