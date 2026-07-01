from __future__ import annotations

from typing import Any

from app.rag.retriever import score_chunk, tokenize_text


SUPPORTED_RERANKER_MODES = {"none", "local_score", "provider"}


def normalize_reranker_mode(mode: str | None) -> str:
    normalized = (mode or "none").strip().lower()
    return normalized if normalized in SUPPORTED_RERANKER_MODES else "none"


def rerank_sources(
    query: str,
    sources: list[dict[str, Any]],
    *,
    reranker_mode: str = "none",
    reranker_model: str | None = None,
    provider_scores: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    mode = normalize_reranker_mode(reranker_mode)
    model = reranker_model or ("none" if mode == "none" else "local-score-v1")
    query_tokens = tokenize_text(query)
    ranked: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        original_score = float(source.get("score") or 0.0)
        if mode == "local_score":
            rerank_score = _local_rerank_score(query_tokens, source)
        elif mode == "provider":
            rerank_score = float((provider_scores or {}).get(str(source["chunk_id"]), 0.0))
        else:
            rerank_score = 0.0
        final_score = (
            original_score
            if mode == "none"
            else round((0.7 * original_score) + (0.3 * rerank_score), 6)
        )
        ranked.append(
            {
                **source,
                "original_score": original_score,
                "rerank_score": rerank_score,
                "final_score": final_score,
                "reranker_mode": mode,
                "reranker_model": model,
                "score": final_score,
                "_original_index": index,
            }
        )

    ranked.sort(
        key=lambda item: (
            -float(item["final_score"]),
            int(item["_original_index"]),
            str(item["doc_id"]),
            str(item["chunk_id"]),
        )
    )
    for item in ranked:
        item.pop("_original_index", None)
    return ranked


def _local_rerank_score(query_tokens: list[str], source: dict[str, Any]) -> float:
    snippet_score = score_chunk(query_tokens, str(source.get("snippet") or ""))
    title_score = score_chunk(query_tokens, str(source.get("title") or ""))
    metadata_score = score_chunk(query_tokens, " ".join(_metadata_terms(source)))
    return round((0.55 * snippet_score) + (0.25 * title_score) + (0.2 * metadata_score), 6)


def _metadata_terms(source: dict[str, Any]) -> list[str]:
    metadata = source.get("metadata") or {}
    if not isinstance(metadata, dict):
        return []
    terms: list[str] = []
    for value in metadata.values():
        if isinstance(value, str):
            terms.append(value)
        elif isinstance(value, list):
            terms.extend(str(item) for item in value[:8])
    return terms
