from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.ai.llm_provider import build_llm_provider
from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.rag import (
    RagCitation,
    RagRetrievalDebug,
    RagSearchSource,
    RagSourceRef,
)


ANSWER_TYPE = "deterministic_summary"
LLM_GROUNDED_ANSWER_TYPE = "llm_grounded"
RAG_LLM_PROMPT_VERSION = "rag-llm-grounded-v3.2"
MIN_GROUNDED_SCORE = 0.01
METADATA_PREVIEW_CHARS = 120


class GroundedRagCitationOutput(BaseModel):
    chunk_id: str
    label: str | None = None
    snippet: str


class GroundedRagProviderOutput(BaseModel):
    answer: str
    citations: list[GroundedRagCitationOutput] = Field(default_factory=list)
    uncertainty: str = "grounded"
    evidence_used: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    refused_due_to_no_evidence: bool = False


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
        retrieval_mode="lexical",
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
            "retrieval_mode": debug.retrieval_mode,
            "evidence_used": [],
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
            "retrieval_mode": debug.retrieval_mode,
            "evidence_used": [],
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
        "answer_mode": ANSWER_TYPE,
        "retrieval_mode": debug.retrieval_mode,
        "evidence_used": evidence_summary,
        "evidence_summary": evidence_summary,
        "citations": citations,
        "source_refs": source_refs,
        "retrieval_debug": debug,
    }


def build_llm_grounded_answer(
    question: str,
    sources: list[RagSearchSource],
    *,
    retrieval_debug: RagRetrievalDebug | None = None,
    provider: Any | None = None,
    max_chars: int = 1000,
) -> dict[str, object]:
    debug = retrieval_debug or _default_debug(
        sources,
        insufficient_reason=None if sources else "no_relevant_source",
    )
    if not sources:
        debug.insufficient_reason = debug.insufficient_reason or "no_relevant_source"
        return {
            "question": question,
            "answer": "",
            "sources": [],
            "uncertainty": "no_relevant_source",
            "grounded": False,
            "answer_type": LLM_GROUNDED_ANSWER_TYPE,
            "answer_mode": LLM_GROUNDED_ANSWER_TYPE,
            "retrieval_mode": debug.retrieval_mode,
            "prompt_version": RAG_LLM_PROMPT_VERSION,
            "model_provider": getattr(provider, "name", None) if provider else None,
            "model_name": getattr(provider, "model", None) if provider else None,
            "groundedness_flags": ["no_relevant_source"],
            "refused_due_to_no_evidence": True,
            "run_config": _answer_run_config(provider, fallback_used=False),
            "evidence_used": [],
            "evidence_summary": [],
            "citations": [],
            "source_refs": [],
            "retrieval_debug": debug,
        }

    fallback = _fallback_grounded_output(question, sources)
    provider_error: AppError | None = None
    if provider is None:
        try:
            provider = build_llm_provider(get_settings())
        except AppError as exc:
            provider_error = exc
    if provider_error is not None:
        parsed = GroundedRagProviderOutput.model_validate(fallback)
        fallback_used = True
        fallback_reason = provider_error.code
    else:
        try:
            parsed = provider.generate_structured(
                prompt=_build_grounded_prompt(question, sources),
                schema=GroundedRagProviderOutput,
                fallback=fallback,
            )
            fallback_used = getattr(provider, "name", "") == "deterministic"
            fallback_reason = (
                "llm_disabled_or_not_configured" if fallback_used else None
            )
        except AppError as exc:
            parsed = GroundedRagProviderOutput.model_validate(fallback)
            fallback_used = True
            fallback_reason = exc.code

    return _grounded_provider_output_to_answer(
        question,
        sources,
        parsed,
        debug=debug,
        provider=provider,
        max_chars=max_chars,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )


def _build_grounded_prompt(question: str, sources: list[RagSearchSource]) -> str:
    evidence_lines = []
    for source in sources:
        evidence_lines.append(
            "\n".join(
                [
                    f"chunk_id: {source.chunk_id}",
                    f"label: {_label_for_source(source)}",
                    f"snippet: {_truncate(source.snippet, 500)}",
                ]
            )
        )
    return "\n\n".join(
        [
            "Return one JSON object matching the GroundedRagProviderOutput schema.",
            "Use only the supplied snippets. Cite chunk_id values for every claim.",
            "If evidence is insufficient, refuse with refused_due_to_no_evidence=true.",
            f"Prompt version: {RAG_LLM_PROMPT_VERSION}",
            f"Question: {question}",
            "Evidence:",
            "\n---\n".join(evidence_lines),
        ]
    )


def _fallback_grounded_output(
    question: str,
    sources: list[RagSearchSource],
) -> dict[str, object]:
    deterministic = build_deterministic_answer(question, sources)
    return {
        "answer": str(deterministic["answer"]),
        "citations": [
            {
                "chunk_id": source.chunk_id,
                "label": _label_for_source(source),
                "snippet": _truncate(source.snippet, 240),
            }
            for source in sources
        ],
        "uncertainty": str(deterministic["uncertainty"]),
        "evidence_used": list(deterministic["evidence_used"]),
        "unsupported_claims": [],
        "refused_due_to_no_evidence": False,
    }


def _grounded_provider_output_to_answer(
    question: str,
    sources: list[RagSearchSource],
    parsed: GroundedRagProviderOutput,
    *,
    debug: RagRetrievalDebug,
    provider: Any,
    max_chars: int,
    fallback_used: bool,
    fallback_reason: str | None,
) -> dict[str, object]:
    source_by_chunk_id = {source.chunk_id: source for source in sources}
    cited_ids = [citation.chunk_id for citation in parsed.citations]
    invalid_ids = [chunk_id for chunk_id in cited_ids if chunk_id not in source_by_chunk_id]
    groundedness_flags: list[str] = []
    if invalid_ids:
        groundedness_flags.append("citation_not_in_retrieved_sources")
    if parsed.unsupported_claims:
        groundedness_flags.append("unsupported_claims_reported")
    if not cited_ids and not parsed.refused_due_to_no_evidence:
        groundedness_flags.append("missing_citations")

    valid_sources = [
        source_by_chunk_id[chunk_id]
        for chunk_id in cited_ids
        if chunk_id in source_by_chunk_id
    ]
    if not valid_sources and not parsed.refused_due_to_no_evidence:
        valid_sources = sources[:1]
    citations = _build_citations(valid_sources)
    source_refs = _build_source_refs(valid_sources)
    evidence_summary = _build_evidence_summary(valid_sources)
    uncertainty = _normalize_grounded_uncertainty(parsed.uncertainty, groundedness_flags)
    grounded = uncertainty == "grounded" and not groundedness_flags
    if parsed.refused_due_to_no_evidence:
        debug.insufficient_reason = debug.insufficient_reason or "no_relevant_source"
        grounded = False
        uncertainty = "no_relevant_source"
    return {
        "question": question,
        "answer": "" if parsed.refused_due_to_no_evidence else _truncate(parsed.answer, max_chars),
        "sources": sources,
        "uncertainty": uncertainty,
        "grounded": grounded,
        "answer_type": LLM_GROUNDED_ANSWER_TYPE,
        "answer_mode": LLM_GROUNDED_ANSWER_TYPE,
        "retrieval_mode": debug.retrieval_mode,
        "prompt_version": RAG_LLM_PROMPT_VERSION,
        "model_provider": getattr(provider, "name", None),
        "model_name": getattr(provider, "model", None),
        "groundedness_flags": groundedness_flags,
        "refused_due_to_no_evidence": parsed.refused_due_to_no_evidence,
        "run_config": _answer_run_config(
            provider,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        ),
        "evidence_used": parsed.evidence_used or evidence_summary,
        "evidence_summary": evidence_summary,
        "citations": citations,
        "source_refs": source_refs,
        "retrieval_debug": debug,
    }


def _normalize_grounded_uncertainty(
    uncertainty: str,
    groundedness_flags: list[str],
) -> str:
    normalized = uncertainty.strip().lower() if uncertainty else "grounded"
    if normalized not in {"grounded", "no_relevant_source", "insufficient_evidence"}:
        normalized = "insufficient_evidence"
    if groundedness_flags and normalized == "grounded":
        return "insufficient_evidence"
    return normalized


def _answer_run_config(
    provider: Any | None,
    *,
    fallback_used: bool,
    fallback_reason: str | None = None,
) -> dict[str, object]:
    return {
        "prompt_version": RAG_LLM_PROMPT_VERSION,
        "answer_mode": LLM_GROUNDED_ANSWER_TYPE,
        "provider": getattr(provider, "name", None) if provider else None,
        "model": getattr(provider, "model", None) if provider else None,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "foundation_only": True,
    }
