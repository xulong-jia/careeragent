from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_json, decrypt_text, encrypt_json, encrypt_text
from app.core.errors import AppError
from app.core.privacy import safe_preview
from app.core.tenant import (
    current_user_id,
    current_workspace_id,
    owner_filter,
    require_owned,
)
from app.models.rag import RagAnswerRun, RagChunk, RagDocument
from app.schemas.rag import (
    RagAnswerRunRecord,
    RagChunkRecord,
    RagDocumentRecord,
    RagStatsResponse,
)


PREVIEW_CHARS = 120


def _next_document_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(RagDocument)) or 0
    return f"rag_doc_{count + 1:04d}"


def _chunk_id(document_id: str, chunk_index: int) -> str:
    return f"{document_id}_chunk_{chunk_index + 1:04d}"


def _next_answer_run_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(RagAnswerRun)) or 0
    return f"rag_answer_run_{count + 1:04d}"


def _preview(text: str) -> str:
    return safe_preview(text, PREVIEW_CHARS)


def _to_document_record(document: RagDocument) -> RagDocumentRecord:
    raw_text = decrypt_text(document.raw_text)
    return RagDocumentRecord(
        doc_id=document.id,
        title=document.title,
        source_type=document.source_type,
        source_uri=document.source_uri,
        raw_text_preview=_preview(raw_text),
        metadata=dict(document.metadata_json or {}),
        index_status=document.index_status,
        chunk_count=document.chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _to_chunk_record(chunk: RagChunk) -> RagChunkRecord:
    text = decrypt_text(chunk.text)
    return RagChunkRecord(
        chunk_id=chunk.id,
        doc_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        section=chunk.section,
        text_preview=_preview(text),
        token_count=chunk.token_count,
        metadata=dict(chunk.metadata_json or {}),
        embedding_id=chunk.embedding_id,
        embedding_provider=chunk.embedding_provider,
        embedding_model=chunk.embedding_model,
        embedding_dim=chunk.embedding_dim,
        embedding_version=chunk.embedding_version,
        embedding_created_at=chunk.embedding_created_at,
        created_at=chunk.created_at,
    )


def _to_answer_run_record(answer_run: RagAnswerRun) -> RagAnswerRunRecord:
    evidence_summary = decrypt_json(answer_run.evidence_summary or [])
    citations = decrypt_json(answer_run.citations_json or [])
    source_refs = decrypt_json(answer_run.source_refs_json or [])
    retrieval_debug = dict(answer_run.retrieval_debug_json or {})
    return RagAnswerRunRecord(
        answer_run_id=answer_run.id,
        question=decrypt_text(answer_run.question),
        filters=dict(answer_run.filters_json or {}),
        top_k=answer_run.top_k,
        retrieval_mode=answer_run.retrieval_mode,
        answer=decrypt_text(answer_run.answer),
        answer_type=answer_run.answer_type,
        answer_mode=str(retrieval_debug.get("answer_mode") or answer_run.answer_type),
        grounded=answer_run.grounded,
        uncertainty=answer_run.uncertainty,
        evidence_summary=list(evidence_summary or []),
        citations=list(citations or []),
        source_refs=list(source_refs or []),
        retrieval_debug=retrieval_debug,
        created_at=answer_run.created_at,
        updated_at=answer_run.updated_at,
    )


def create_document(
    db: Session,
    *,
    title: str,
    source_type: str,
    raw_text: str,
    metadata: dict[str, object],
    source_uri: str | None = None,
) -> RagDocumentRecord:
    document = RagDocument(
        id=_next_document_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        title=title,
        source_type=source_type,
        source_uri=source_uri,
        raw_text=encrypt_text(raw_text),
        metadata_json=metadata,
        index_status="pending",
        chunk_count=0,
    )
    try:
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(document)
    return _to_document_record(document)


def list_documents(
    db: Session,
    *,
    source_type: str | None = None,
    index_status: str | None = None,
) -> list[RagDocumentRecord]:
    statement = select(RagDocument).where(*owner_filter(RagDocument))
    if source_type:
        statement = statement.where(RagDocument.source_type == source_type)
    if index_status:
        statement = statement.where(RagDocument.index_status == index_status)
    documents = db.scalars(statement.order_by(RagDocument.created_at, RagDocument.id)).all()
    return [_to_document_record(document) for document in documents]


def get_document_model(db: Session, doc_id: str) -> RagDocument:
    document = db.get(RagDocument, doc_id)
    require_owned(
        document,
        code="rag_document_not_found",
        message="RAG document was not found.",
        details={"doc_id": doc_id},
    )
    if not document:
        raise AppError(
            code="rag_document_not_found",
            message="RAG document was not found.",
            status_code=404,
            details={"doc_id": doc_id},
        )
    return document


def get_document(db: Session, doc_id: str) -> RagDocumentRecord:
    return _to_document_record(get_document_model(db, doc_id))


def delete_document(db: Session, doc_id: str) -> dict[str, object]:
    document = get_document_model(db, doc_id)
    chunk_count = document.chunk_count
    try:
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "doc_id": doc_id,
        "status": "deleted",
        "deleted_chunk_count": chunk_count,
    }


def replace_chunks_for_document(
    db: Session,
    *,
    document: RagDocument,
    chunks: list[dict[str, object]],
) -> list[RagChunkRecord]:
    try:
        db.execute(delete(RagChunk).where(RagChunk.document_id == document.id))
        chunk_models: list[RagChunk] = []
        for chunk in chunks:
            chunk_index = int(chunk["chunk_index"])
            chunk_model = RagChunk(
                id=_chunk_id(document.id, chunk_index),
                document_id=document.id,
                chunk_index=chunk_index,
                section=chunk.get("section") if isinstance(chunk.get("section"), str) else None,
                text=encrypt_text(str(chunk["text"])),
                token_count=int(chunk["token_count"]),
                metadata_json=dict(chunk.get("metadata") or {}),
                embedding_id=str(chunk["embedding_id"]) if chunk.get("embedding_id") else None,
                embedding_vector=chunk.get("embedding_vector")
                if isinstance(chunk.get("embedding_vector"), list)
                else None,
                embedding_provider=str(chunk["embedding_provider"])
                if chunk.get("embedding_provider")
                else None,
                embedding_model=str(chunk["embedding_model"])
                if chunk.get("embedding_model")
                else None,
                embedding_dim=int(chunk["embedding_dim"]) if chunk.get("embedding_dim") else None,
                embedding_version=str(chunk["embedding_version"])
                if chunk.get("embedding_version")
                else None,
                embedding_created_at=chunk.get("embedding_created_at")
                if chunk.get("embedding_created_at")
                else None,
            )
            chunk_models.append(chunk_model)
            db.add(chunk_model)
        document.index_status = "indexed"
        document.chunk_count = len(chunk_models)
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(document)
    return [
        _to_chunk_record(chunk)
        for chunk in db.scalars(
            select(RagChunk)
            .where(RagChunk.document_id == document.id)
            .order_by(RagChunk.chunk_index)
        ).all()
    ]


def list_chunks(
    db: Session,
    *,
    doc_id: str | None = None,
    source_type: str | None = None,
) -> list[RagChunkRecord]:
    statement = select(RagChunk).join(RagDocument).where(*owner_filter(RagDocument))
    if doc_id:
        statement = statement.where(RagChunk.document_id == doc_id)
    if source_type:
        statement = statement.where(RagDocument.source_type == source_type)
    chunks = db.scalars(
        statement.order_by(RagChunk.document_id, RagChunk.chunk_index)
    ).all()
    return [_to_chunk_record(chunk) for chunk in chunks]


def list_indexed_chunks_for_search(
    db: Session,
    *,
    source_type: str | None = None,
    doc_id: str | None = None,
) -> list[dict[str, object]]:
    statement = (
        select(RagChunk, RagDocument)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .where(RagDocument.index_status == "indexed")
        .where(*owner_filter(RagDocument))
    )
    if source_type:
        statement = statement.where(RagDocument.source_type == source_type)
    if doc_id:
        statement = statement.where(RagDocument.id == doc_id)

    rows = db.execute(
        statement.order_by(RagDocument.id, RagChunk.chunk_index)
    ).all()
    return [
        {
            "doc_id": document.id,
            "chunk_id": chunk.id,
            "title": document.title,
            "source_type": document.source_type,
            "section": chunk.section,
            "text": decrypt_text(chunk.text),
            "metadata": dict(document.metadata_json or {}) | dict(chunk.metadata_json or {}),
            "embedding_vector": list(chunk.embedding_vector or []),
            "embedding_provider": chunk.embedding_provider,
            "embedding_model": chunk.embedding_model,
            "embedding_dim": chunk.embedding_dim,
            "embedding_version": chunk.embedding_version,
        }
        for chunk, document in rows
    ]


def count_chunks_for_document(db: Session, doc_id: str) -> int:
    return (
        db.scalar(select(func.count()).select_from(RagChunk).where(RagChunk.document_id == doc_id))
        or 0
    )


def update_document_index_status(
    db: Session,
    *,
    document: RagDocument,
    index_status: str,
    chunk_count: int | None = None,
) -> RagDocumentRecord:
    try:
        document.index_status = index_status
        if chunk_count is not None:
            document.chunk_count = chunk_count
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(document)
    return _to_document_record(document)


def create_answer_run(
    db: Session,
    *,
    question: str,
    filters: dict[str, object],
    top_k: int,
    retrieval_mode: str,
    answer: str,
    answer_type: str,
    grounded: bool,
    uncertainty: str,
    evidence_summary: list[str],
    citations: list[dict[str, object]],
    source_refs: list[dict[str, object]],
    retrieval_debug: dict[str, object],
) -> RagAnswerRunRecord:
    answer_run = RagAnswerRun(
        id=_next_answer_run_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        question=encrypt_text(question),
        filters_json=filters,
        top_k=top_k,
        retrieval_mode=retrieval_mode,
        answer=encrypt_text(answer),
        answer_type=answer_type,
        grounded=grounded,
        uncertainty=uncertainty,
        evidence_summary=encrypt_json(evidence_summary),
        citations_json=encrypt_json(citations),
        source_refs_json=encrypt_json(source_refs),
        retrieval_debug_json=retrieval_debug,
    )
    try:
        db.add(answer_run)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(answer_run)
    return _to_answer_run_record(answer_run)


def list_answer_runs(
    db: Session,
    *,
    grounded: bool | None = None,
    uncertainty: str | None = None,
    retrieval_mode: str | None = None,
) -> list[RagAnswerRunRecord]:
    statement = select(RagAnswerRun).where(*owner_filter(RagAnswerRun))
    if grounded is not None:
        statement = statement.where(RagAnswerRun.grounded == grounded)
    if uncertainty:
        statement = statement.where(RagAnswerRun.uncertainty == uncertainty)
    if retrieval_mode:
        legacy_mode = f"deterministic_{retrieval_mode}"
        statement = statement.where(
            RagAnswerRun.retrieval_mode.in_([retrieval_mode, legacy_mode])
        )
    answer_runs = db.scalars(
        statement.order_by(RagAnswerRun.created_at.desc(), RagAnswerRun.id.desc())
    ).all()
    return [_to_answer_run_record(answer_run) for answer_run in answer_runs]


def get_answer_run(db: Session, answer_run_id: str) -> RagAnswerRunRecord:
    answer_run = db.get(RagAnswerRun, answer_run_id)
    require_owned(
        answer_run,
        code="rag_answer_run_not_found",
        message="RAG answer run was not found.",
        details={"answer_run_id": answer_run_id},
    )
    if not answer_run:
        raise AppError(
            code="rag_answer_run_not_found",
            message="RAG answer run was not found.",
            status_code=404,
            details={"answer_run_id": answer_run_id},
        )
    return _to_answer_run_record(answer_run)


def get_stats(db: Session) -> RagStatsResponse:
    latest_answer_run = db.scalars(
        select(RagAnswerRun).where(*owner_filter(RagAnswerRun)).order_by(
            RagAnswerRun.created_at.desc(),
            RagAnswerRun.id.desc(),
        )
    ).first()
    total_answer_runs = (
        db.scalar(
            select(func.count())
            .select_from(RagAnswerRun)
            .where(*owner_filter(RagAnswerRun))
        )
        or 0
    )
    grounded_answer_runs = (
        db.scalar(
            select(func.count())
            .select_from(RagAnswerRun)
            .where(*owner_filter(RagAnswerRun))
            .where(RagAnswerRun.grounded.is_(True))
        )
        or 0
    )
    return RagStatsResponse(
        total_documents=db.scalar(
            select(func.count()).select_from(RagDocument).where(*owner_filter(RagDocument))
        )
        or 0,
        indexed_documents=db.scalar(
            select(func.count())
            .select_from(RagDocument)
            .where(*owner_filter(RagDocument))
            .where(RagDocument.index_status == "indexed")
        )
        or 0,
        total_chunks=db.scalar(
            select(func.count())
            .select_from(RagChunk)
            .join(RagDocument)
            .where(*owner_filter(RagDocument))
        )
        or 0,
        total_answer_runs=total_answer_runs,
        grounded_answer_runs=grounded_answer_runs,
        ungrounded_answer_runs=total_answer_runs - grounded_answer_runs,
        latest_answer_run_id=latest_answer_run.id if latest_answer_run else None,
        latest_answer_question_preview=(
            _preview(decrypt_text(latest_answer_run.question)) if latest_answer_run else None
        ),
        latest_answer_uncertainty=(
            latest_answer_run.uncertainty if latest_answer_run else None
        ),
        latest_answer_created_at=(
            latest_answer_run.created_at if latest_answer_run else None
        ),
    )
