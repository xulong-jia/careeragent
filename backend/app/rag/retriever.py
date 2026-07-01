from __future__ import annotations

import re
from collections import Counter
from typing import Any

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "for",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def tokenize_text(text: str) -> list[str]:
    lowered = text.lower()
    latin_tokens = re.findall(r"[a-z0-9]+", lowered)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    cjk_bigrams: list[str] = []
    for term in cjk_terms:
        cjk_bigrams.extend(term[index : index + 2] for index in range(len(term) - 1))
    tokens = [token for token in latin_tokens + cjk_terms + cjk_bigrams if token not in STOPWORDS]
    return tokens


def metadata_matches(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True

    for key, expected in filters.items():
        if expected in (None, "", []):
            continue
        if key in {"source_type", "doc_id"}:
            continue

        actual = metadata.get(key)
        if key == "tags":
            actual_tags = actual if isinstance(actual, list) else []
            expected_tags = expected if isinstance(expected, list) else [expected]
            if not set(str(tag) for tag in expected_tags).issubset(
                set(str(tag) for tag in actual_tags)
            ):
                return False
            continue

        if str(actual).lower() != str(expected).lower():
            return False
    return True


def score_chunk(query_tokens: list[str], chunk_text: str) -> float:
    if not query_tokens:
        return 0.0
    chunk_tokens = tokenize_text(chunk_text)
    if not chunk_tokens:
        return 0.0

    query_counts = Counter(query_tokens)
    chunk_counts = Counter(chunk_tokens)
    matched_terms = [token for token in query_counts if token in chunk_counts]
    if not matched_terms:
        return 0.0

    overlap_ratio = len(matched_terms) / len(query_counts)
    frequency_score = sum(min(chunk_counts[token], 3) for token in matched_terms) / (
        len(chunk_tokens) + len(query_counts)
    )
    return round(overlap_ratio + frequency_score, 6)


def build_snippet(
    chunk_text: str,
    query_tokens: list[str],
    max_length: int = 240,
) -> str:
    cleaned = re.sub(r"\s+", " ", chunk_text).strip()
    if len(cleaned) <= max_length:
        return cleaned

    lowered = cleaned.lower()
    first_match = min(
        (lowered.find(token) for token in query_tokens if lowered.find(token) >= 0),
        default=0,
    )
    start = max(0, first_match - max_length // 3)
    end = min(len(cleaned), start + max_length)
    snippet = cleaned[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(cleaned):
        snippet = f"{snippet}..."
    return snippet


def rank_chunks(
    query: str,
    chunk_candidates: list[dict[str, Any]],
    *,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    query_tokens = tokenize_text(query)
    ranked: list[dict[str, Any]] = []
    for candidate in chunk_candidates:
        metadata = dict(candidate.get("metadata") or {})
        if not metadata_matches(metadata, filters):
            continue
        chunk_text = str(candidate.get("text") or "")
        score = score_chunk(query_tokens, chunk_text)
        if score <= 0:
            continue
        ranked.append(
            {
                "doc_id": str(candidate["doc_id"]),
                "chunk_id": str(candidate["chunk_id"]),
                "title": str(candidate["title"]),
                "source_type": str(candidate["source_type"]),
                "section": candidate.get("section"),
                "snippet": build_snippet(chunk_text, query_tokens),
                "score": score,
                "metadata": metadata,
            }
        )

    ranked.sort(
        key=lambda source: (
            -float(source["score"]),
            str(source["doc_id"]),
            str(source["chunk_id"]),
        )
    )
    return ranked[:top_k]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return round(sum(a * b for a, b in zip(left, right)), 6)


def normalize_retrieval_mode(mode: str | None) -> str:
    normalized = (mode or "lexical").strip().lower()
    aliases = {
        "lexical": "lexical",
        "deterministic_lexical": "lexical",
        "vector": "vector",
        "deterministic_vector": "vector",
        "hybrid": "hybrid",
        "deterministic_hybrid": "hybrid",
    }
    return aliases.get(normalized, normalized)


def rank_chunks_by_mode(
    query: str,
    chunk_candidates: list[dict[str, Any]],
    *,
    top_k: int,
    filters: dict[str, Any] | None = None,
    retrieval_mode: str = "lexical",
    score_threshold: float | None = None,
    embedding_provider: Any | None = None,
) -> list[dict[str, Any]]:
    mode = normalize_retrieval_mode(retrieval_mode)
    query_tokens = tokenize_text(query)
    provider = embedding_provider
    query_embedding = (
        provider.embed_text(query) if provider and mode in {"vector", "hybrid"} else []
    )
    threshold = 0.0 if score_threshold is None else score_threshold
    ranked: list[dict[str, Any]] = []

    for candidate in chunk_candidates:
        metadata = dict(candidate.get("metadata") or {})
        if not metadata_matches(metadata, filters):
            continue

        chunk_text = str(candidate.get("text") or "")
        lexical_score = score_chunk(query_tokens, chunk_text)
        vector_score = 0.0
        persisted_vector = candidate.get("embedding_vector")
        vector_index_used = (
            mode in {"vector", "hybrid"}
            and isinstance(persisted_vector, list)
            and bool(persisted_vector)
        )
        if vector_index_used:
            vector_score = cosine_similarity(
                query_embedding,
                [float(value) for value in persisted_vector],
            )

        if mode == "lexical":
            score = lexical_score
        elif mode == "vector":
            score = vector_score
        else:
            score = round((0.4 * lexical_score) + (0.6 * vector_score), 6)

        if score <= threshold:
            continue

        ranked.append(
            {
                "doc_id": str(candidate["doc_id"]),
                "chunk_id": str(candidate["chunk_id"]),
                "title": str(candidate["title"]),
                "source_type": str(candidate["source_type"]),
                "section": candidate.get("section"),
                "snippet": build_snippet(chunk_text, query_tokens),
                "score": score,
                "metadata": metadata,
                "retrieval_mode": mode,
                "embedding_provider": candidate.get("embedding_provider")
                if mode in {"vector", "hybrid"}
                else None,
                "embedding_model": candidate.get("embedding_model")
                if mode in {"vector", "hybrid"}
                else None,
                "vector_index_used": vector_index_used,
            }
        )

    ranked.sort(
        key=lambda source: (
            -float(source["score"]),
            str(source["doc_id"]),
            str(source["chunk_id"]),
        )
    )
    return ranked[:top_k]
