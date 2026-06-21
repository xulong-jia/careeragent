from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.rag.answering import build_deterministic_answer
from app.rag.chunking import chunk_document_text
from app.rag.retriever import rank_chunks
from app.repositories import rag_repository
from app.schemas.rag import (
    RagChunkRecord,
    RagAnswerRequest,
    RagAnswerResult,
    RagDocumentCreateRequest,
    RagDocumentIndexRequest,
    RagDocumentIndexResult,
    RagDocumentRecord,
    RagSearchRequest,
    RagSearchResult,
    RagSearchSource,
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

    candidates = rag_repository.list_indexed_chunks_for_search(
        db,
        source_type=source_type,
        doc_id=str(doc_id) if doc_id else None,
    )
    ranked_sources = rank_chunks(
        query,
        candidates,
        top_k=top_k,
        filters=filters,
    )
    sources = [RagSearchSource(**source) for source in ranked_sources]
    return RagSearchResult(
        query=query,
        top_k=top_k,
        sources=sources,
        uncertainty=None if sources else "no_relevant_source",
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
        ),
    )
    answer_payload = build_deterministic_answer(question, search_result.sources)
    return RagAnswerResult(**answer_payload)
