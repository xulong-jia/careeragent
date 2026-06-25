from __future__ import annotations

from typing import Any

from app.schemas.rag import (
    RagCitation,
    RagRetrievalDebug,
    RagSearchSource,
    RagSourceRef,
)


ANSWER_TYPE = "deterministic_summary"
MIN_GROUNDED_SCORE = 0.01
METADATA_PREVIEW_CHARS = 120


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _label_for_source(source: RagSearchSource) -> str:
    return f"{source.title} / {source.section}" if source.section else source.title


def _safe_metadata_preview(metadata: dict[str, object]) -> dict[str, object]:
    preview: dict[str, object] = {}
    blocked_key_parts = {"raw_text", "answer_text", "chunk_text", "full_text", "text"}
    for key, value in metadata.items():
        lowered = key.lower()
        if any(part in lowered for part in blocked_key_parts):
            continue
        if isinstance(value, str):
            preview[key] = _truncate(value, METADATA_PREVIEW_CHARS)
        elif isinstance(value, (int, float, bool)) or value is None:
            preview[key] = value
        elif isinstance(value, list):
            safe_values: list[Any] = []
            for item in value[:8]:
                if isinstance(item, str):
                    safe_values.append(_truncate(item, METADATA_PREVIEW_CHARS))
                elif isinstance(item, (int, float, bool)) or item is None:
                    safe_values.append(item)
            preview[key] = safe_values
    return preview


def _build_citations(sources: list[RagSearchSource]) -> list[RagCitation]:
    return [
        RagCitation(
            source_type=source.source_type,
            document_id=source.doc_id,
            chunk_id=source.chunk_id,
            title=source.title,
            section=source.section,
            label=_label_for_source(source),
            snippet=_truncate(source.snippet, 240),
            score=source.score,
            metadata_preview=_safe_metadata_preview(source.metadata),
        )
        for source in sources
    ]


def _build_source_refs(sources: list[RagSearchSource]) -> list[RagSourceRef]:
    return [
        RagSourceRef(
            source_type="rag_chunk",
            source_id=source.chunk_id,
            document_id=source.doc_id,
            chunk_id=source.chunk_id,
            field="snippet",
            label=_label_for_source(source),
            preview=_truncate(source.snippet, 240),
            score=source.score,
        )
        for source in sources
    ]


def _build_evidence_summary(sources: list[RagSearchSource]) -> list[str]:
    return [
        f"{_label_for_source(source)}: {_truncate(source.snippet, 220)}"
        for source in sources
    ]


def _default_debug(
    sources: list[RagSearchSource],
    *,
    top_k: int | None = None,
    insufficient_reason: str | None = None,
) -> RagRetrievalDebug:
    return RagRetrievalDebug(
        retrieval_mode="deterministic_lexical",
        query_tokens=[],
        candidate_count=len(sources),
        selected_chunk_ids=[source.chunk_id for source in sources],
        scores=[source.score for source in sources],
        top_k=top_k or len(sources),
        filters={},
        insufficient_reason=insufficient_reason,
    )


def build_deterministic_answer(
    question: str,
    sources: list[RagSearchSource],
    *,
    max_chars: int = 1000,
    retrieval_debug: RagRetrievalDebug | None = None,
) -> dict[str, object]:
    if not sources:
        debug = retrieval_debug or _default_debug(
            sources,
            insufficient_reason="no_relevant_source",
        )
        debug.insufficient_reason = debug.insufficient_reason or "no_relevant_source"
        return {
            "question": question,
            "answer": "",
            "sources": [],
            "uncertainty": "no_relevant_source",
            "grounded": False,
            "answer_type": ANSWER_TYPE,
            "evidence_summary": [],
            "citations": [],
            "source_refs": [],
            "retrieval_debug": debug,
        }

    citations = _build_citations(sources)
    source_refs = _build_source_refs(sources)
    evidence_summary = _build_evidence_summary(sources)
    debug = retrieval_debug or _default_debug(sources)
    max_score = max((source.score for source in sources), default=0.0)
    if max_score < MIN_GROUNDED_SCORE:
        debug.insufficient_reason = debug.insufficient_reason or "insufficient_evidence"
        return {
            "question": question,
            "answer": "Insufficient retrieved evidence to answer safely.",
            "sources": sources,
            "uncertainty": "insufficient_evidence",
            "grounded": False,
            "answer_type": ANSWER_TYPE,
            "evidence_summary": [],
            "citations": citations,
            "source_refs": source_refs,
            "retrieval_debug": debug,
        }

    lines = ["Based on retrieved evidence, the grounded answer is:"]
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. [{_label_for_source(source)}] {source.snippet}")
    answer = _truncate(" ".join(lines), max_chars)
    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "uncertainty": "grounded",
        "grounded": True,
        "answer_type": ANSWER_TYPE,
        "evidence_summary": evidence_summary,
        "citations": citations,
        "source_refs": source_refs,
        "retrieval_debug": debug,
    }
