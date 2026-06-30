from typing import Any

from sqlalchemy.orm import Session

from app.ai.embedding_provider import (
    DeterministicEmbeddingProvider,
    build_embedding_provider,
    embedding_id_for_text,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.versioning import MODEL_VERSION, RETRIEVAL_VERSION, SCHEMA_VERSION
from app.rag.answering import build_deterministic_answer
from app.rag.chunking import chunk_document_text
from app.rag.retriever import normalize_retrieval_mode, rank_chunks_by_mode, tokenize_text
from app.repositories import rag_repository
from app.schemas.rag import (
    RagChunkRecord,
    RagAnswerRequest,
    RagAnswerResult,
    RagAnswerRunRecord,
    RagDocumentCreateRequest,
    RagDocumentIndexRequest,
    RagDocumentIndexResult,
    RagDocumentRecord,
    RagRetrievalDebug,
    RagSearchRequest,
    RagSearchResult,
    RagSearchSource,
    RagStatsResponse,
)


ALLOWED_SOURCE_TYPES = {
    "manual",
    "markdown",
    "text",
    "jd",
    "interview",
    "project",
    "learning",
    "company",
}
MAX_SEARCH_TOP_K = 20
ALLOWED_ANSWER_UNCERTAINTIES = {
    "grounded",
    "no_relevant_source",
    "insufficient_evidence",
}
ALLOWED_RETRIEVAL_MODES = {
    "deterministic_lexical",
    "deterministic_vector",
    "deterministic_hybrid",
}
STORED_TEXT_PREVIEW_CHARS = 240
SENSITIVE_KEY_PARTS = {
    "raw_text",
    "answer_text",
    "chunk_text",
    "full_text",
}


def _validation_error(message: str, field: str) -> AppError:
    return AppError(
        code="rag_document_validation_error",
        message=message,
        status_code=400,
        details={"field": field},
    )


def _normalize_source_type(source_type: str) -> str:
    normalized = source_type.strip().lower()
    if normalized not in ALLOWED_SOURCE_TYPES:
        raise _validation_error("Unsupported RAG source_type.", "source_type")
    return normalized


def _validate_answer_run_filter(
    *,
    uncertainty: str | None = None,
    retrieval_mode: str | None = None,
) -> None:
    if uncertainty and uncertainty not in ALLOWED_ANSWER_UNCERTAINTIES:
        raise AppError(
            code="rag_answer_run_filter_validation_error",
            message="Unsupported RAG answer uncertainty filter.",
            status_code=400,
            details={"field": "uncertainty"},
        )
    normalized_mode = normalize_retrieval_mode(retrieval_mode) if retrieval_mode else None
    if normalized_mode and normalized_mode not in ALLOWED_RETRIEVAL_MODES:
        raise AppError(
            code="rag_answer_run_filter_validation_error",
            message="Unsupported RAG retrieval_mode filter.",
            status_code=400,
            details={"field": "retrieval_mode"},
        )


def _truncate_stored_text(value: str) -> str:
    if len(value) <= STORED_TEXT_PREVIEW_CHARS:
        return value
    return f"{value[: STORED_TEXT_PREVIEW_CHARS - 3].rstrip()}..."


def _sanitize_for_answer_run(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested_value in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                continue
            sanitized[key] = _sanitize_for_answer_run(nested_value)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_answer_run(item) for item in value]
    if isinstance(value, str):
        return _truncate_stored_text(value)
    return value


def _validate_document_payload(
    payload: RagDocumentCreateRequest,
) -> tuple[str, str, str, dict[str, object], str | None]:
    title = payload.title.strip()
    if not title:
        raise _validation_error("RAG document title is required.", "title")

    source_type = _normalize_source_type(payload.source_type)
    raw_text = payload.raw_text.strip()
    if not raw_text:
        raise _validation_error("RAG document raw_text is required.", "raw_text")

    return title, source_type, raw_text, dict(payload.metadata or {}), payload.source_uri


def create_document(db: Session, payload: RagDocumentCreateRequest) -> RagDocumentRecord:
    title, source_type, raw_text, metadata, source_uri = _validate_document_payload(payload)
    return rag_repository.create_document(
        db,
        title=title,
        source_type=source_type,
        source_uri=source_uri,
        raw_text=raw_text,
        metadata=metadata,
    )


def list_documents(
    db: Session,
    *,
    source_type: str | None = None,
    index_status: str | None = None,
) -> list[RagDocumentRecord]:
    normalized_source_type = _normalize_source_type(source_type) if source_type else None
    return rag_repository.list_documents(
        db,
        source_type=normalized_source_type,
        index_status=index_status,
    )


def get_document(db: Session, doc_id: str) -> RagDocumentRecord:
    return rag_repository.get_document(db, doc_id)


def delete_document(db: Session, doc_id: str) -> dict[str, object]:
    return rag_repository.delete_document(db, doc_id)


def index_document(
    db: Session,
    doc_id: str,
    payload: RagDocumentIndexRequest,
) -> RagDocumentIndexResult:
    if payload.overlap_chars >= payload.max_chars:
        raise AppError(
            code="rag_chunk_validation_error",
            message="overlap_chars must be lower than max_chars.",
            status_code=400,
            details={"field": "overlap_chars"},
        )

    document = rag_repository.get_document_model(db, doc_id)
    try:
        chunks = chunk_document_text(
            document.raw_text,
            source_type=document.source_type,
            metadata=document.metadata_json,
            max_chars=payload.max_chars,
            overlap_chars=payload.overlap_chars,
        )
        embedding_provider = build_embedding_provider(get_settings())
        for chunk in chunks:
            chunk["embedding_id"] = embedding_id_for_text(
                str(chunk["text"]),
                model=embedding_provider.model,
            )
        if not chunks:
            raise AppError(
                code="rag_chunk_validation_error",
                message="RAG document did not produce any chunks.",
                status_code=400,
                details={"doc_id": doc_id},
            )
        records = rag_repository.replace_chunks_for_document(
            db,
            document=document,
            chunks=chunks,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            code="rag_index_failed",
            message="RAG document indexing failed.",
            status_code=500,
            details={"doc_id": doc_id},
        ) from exc

    return RagDocumentIndexResult(
        doc_id=doc_id,
        index_status="indexed",
        chunk_count=len(records),
        chunks=records,
    )


def list_chunks(
    db: Session,
    *,
    doc_id: str | None = None,
    source_type: str | None = None,
) -> list[RagChunkRecord]:
    normalized_source_type = _normalize_source_type(source_type) if source_type else None
    if doc_id:
        rag_repository.get_document_model(db, doc_id)
    return rag_repository.list_chunks(
        db,
        doc_id=doc_id,
        source_type=normalized_source_type,
    )


def search_documents(db: Session, payload: RagSearchRequest) -> RagSearchResult:
    query = payload.query.strip()
    if not query:
        raise AppError(
            code="rag_search_validation_error",
            message="RAG search query is required.",
            status_code=400,
            details={"field": "query"},
        )

    requested_top_k = payload.top_k
    if requested_top_k <= 0:
        raise AppError(
            code="rag_search_validation_error",
            message="top_k must be greater than zero.",
            status_code=400,
            details={"field": "top_k"},
        )
    top_k = min(requested_top_k, MAX_SEARCH_TOP_K)

    filters_model = payload.filters
    filters = filters_model.model_dump(exclude_none=True) if filters_model else {}
    source_type = _normalize_source_type(filters["source_type"]) if filters.get("source_type") else None
    doc_id = filters.get("doc_id")

    settings = get_settings()
    retrieval_mode = normalize_retrieval_mode(
        payload.retrieval_mode or settings.rag_retrieval_mode
    )
    if retrieval_mode not in ALLOWED_RETRIEVAL_MODES:
        raise AppError(
            code="rag_search_validation_error",
            message="Unsupported RAG retrieval_mode.",
            status_code=400,
            details={"field": "retrieval_mode"},
        )
    if retrieval_mode in {"deterministic_vector", "deterministic_hybrid"}:
        embedding_provider = build_embedding_provider(settings)
        if not isinstance(embedding_provider, DeterministicEmbeddingProvider):
            # ponytail: vector retrieval stays local until real embedding storage is added.
            embedding_provider = DeterministicEmbeddingProvider(
                dimension=settings.embedding_dimension,
                model=settings.embedding_model,
            )
    else:
        embedding_provider = DeterministicEmbeddingProvider(
            dimension=settings.embedding_dimension,
            model=settings.embedding_model,
        )

    candidates = rag_repository.list_indexed_chunks_for_search(
        db,
        source_type=source_type,
        doc_id=str(doc_id) if doc_id else None,
    )
    ranked_sources = rank_chunks_by_mode(
        query,
        candidates,
        top_k=top_k,
        filters=filters,
        retrieval_mode=retrieval_mode,
        score_threshold=payload.score_threshold,
        embedding_provider=embedding_provider,
    )
    sources = [RagSearchSource(**source) for source in ranked_sources]
    retrieval_debug = RagRetrievalDebug(
        retrieval_mode=retrieval_mode,
        retrieval_version=RETRIEVAL_VERSION,
        schema_version=SCHEMA_VERSION,
        model_version=MODEL_VERSION,
        embedding_model=embedding_provider.model
        if retrieval_mode in {"deterministic_vector", "deterministic_hybrid"}
        else None,
        query_tokens=tokenize_text(query),
        candidate_count=len(candidates),
        selected_chunk_ids=[source.chunk_id for source in sources],
        scores=[source.score for source in sources],
        top_k=top_k,
        filters=filters,
        score_threshold=payload.score_threshold,
        insufficient_reason=None if sources else "no_relevant_source",
    )
    return RagSearchResult(
        query=query,
        top_k=top_k,
        sources=sources,
        uncertainty=None if sources else "no_relevant_source",
        retrieval_debug=retrieval_debug,
    )


def answer_question(db: Session, payload: RagAnswerRequest) -> RagAnswerResult:
    question = payload.question.strip()
    if not question:
        raise AppError(
            code="rag_answer_validation_error",
            message="RAG answer question is required.",
            status_code=400,
            details={"field": "question"},
        )

    search_result = search_documents(
        db,
        RagSearchRequest(
            query=question,
            top_k=payload.top_k,
            filters=payload.filters,
            retrieval_mode=payload.retrieval_mode,
            score_threshold=payload.score_threshold,
        ),
    )
    answer_payload = build_deterministic_answer(
        question,
        search_result.sources,
        retrieval_debug=search_result.retrieval_debug,
    )
    result = RagAnswerResult(**answer_payload)
    if not payload.persist:
        return result

    filters = payload.filters.model_dump(exclude_none=True) if payload.filters else {}
    retrieval_debug = result.retrieval_debug.model_dump()
    answer_run = rag_repository.create_answer_run(
        db,
        question=question,
        filters=dict(_sanitize_for_answer_run(filters)),
        top_k=search_result.top_k,
        retrieval_mode=result.retrieval_debug.retrieval_mode,
        answer=result.answer,
        answer_type=result.answer_type,
        grounded=result.grounded,
        uncertainty=result.uncertainty or "grounded",
        evidence_summary=list(_sanitize_for_answer_run(result.evidence_summary)),
        citations=list(
            _sanitize_for_answer_run(
                [citation.model_dump() for citation in result.citations]
            )
        ),
        source_refs=list(
            _sanitize_for_answer_run(
                [source_ref.model_dump() for source_ref in result.source_refs]
            )
        ),
        retrieval_debug=dict(_sanitize_for_answer_run(retrieval_debug)),
    )
    result.answer_run_id = answer_run.answer_run_id
    return result


def list_answer_runs(
    db: Session,
    *,
    grounded: bool | None = None,
    uncertainty: str | None = None,
    retrieval_mode: str | None = None,
) -> list[RagAnswerRunRecord]:
    _validate_answer_run_filter(
        uncertainty=uncertainty,
        retrieval_mode=retrieval_mode,
    )
    normalized_retrieval_mode = (
        normalize_retrieval_mode(retrieval_mode) if retrieval_mode else None
    )
    return rag_repository.list_answer_runs(
        db,
        grounded=grounded,
        uncertainty=uncertainty,
        retrieval_mode=normalized_retrieval_mode,
    )


def get_answer_run(db: Session, answer_run_id: str) -> RagAnswerRunRecord:
    return rag_repository.get_answer_run(db, answer_run_id)


def get_stats(db: Session) -> RagStatsResponse:
    return rag_repository.get_stats(db)
