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
- `DeterministicEmbeddingProvider` remains as a backwards-compatible alias for older local tests/config.
- `OpenAICompatibleEmbeddingProvider` can call `/embeddings` only when explicitly enabled and fully configured.

Phase 2.2 persists chunk vectors in `rag_chunks`. Local vector search is a production foundation, not a final semantic embedding provider.

Required real-provider env:

```bash
ENABLE_REAL_EMBEDDING=true
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_BASE_URL=https://provider.example/v1
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_DIMENSION=384
```

## Safety Rules

- Do not commit `.env` or real API keys.
- Do not log prompts, full resume/JD raw text, chunk full text, `reflection`, `interview_notes`, or provider keys.
- Tests must not call external APIs.
- Real provider mode should be enabled only after running the smoke evals and reviewing cost/rate limits.
