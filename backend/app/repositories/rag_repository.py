from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.rag import RagChunk, RagDocument
from app.schemas.rag import RagChunkRecord, RagDocumentRecord


PREVIEW_CHARS = 500


def _next_document_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(RagDocument)) or 0
    return f"rag_doc_{count + 1:04d}"


def _chunk_id(document_id: str, chunk_index: int) -> str:
    return f"{document_id}_chunk_{chunk_index + 1:04d}"


def _preview(text: str) -> str:
    return text[:PREVIEW_CHARS]


def _to_document_record(document: RagDocument) -> RagDocumentRecord:
    return RagDocumentRecord(
        doc_id=document.id,
        title=document.title,
        source_type=document.source_type,
        source_uri=document.source_uri,
        raw_text_preview=_preview(document.raw_text),
        metadata=dict(document.metadata_json or {}),
        index_status=document.index_status,
        chunk_count=document.chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _to_chunk_record(chunk: RagChunk) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=chunk.id,
        doc_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        section=chunk.section,
        text_preview=_preview(chunk.text),
        token_count=chunk.token_count,
        metadata=dict(chunk.metadata_json or {}),
        embedding_id=chunk.embedding_id,
        created_at=chunk.created_at,
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
        user_id="default",
        title=title,
        source_type=source_type,
        source_uri=source_uri,
        raw_text=raw_text,
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
    statement = select(RagDocument)
    if source_type:
        statement = statement.where(RagDocument.source_type == source_type)
    if index_status:
        statement = statement.where(RagDocument.index_status == index_status)
    documents = db.scalars(statement.order_by(RagDocument.created_at, RagDocument.id)).all()
    return [_to_document_record(document) for document in documents]


def get_document_model(db: Session, doc_id: str) -> RagDocument:
    document = db.get(RagDocument, doc_id)
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
                text=str(chunk["text"]),
                token_count=int(chunk["token_count"]),
                metadata_json=dict(chunk.get("metadata") or {}),
                embedding_id=None,
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
    statement = select(RagChunk).join(RagDocument)
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
            "text": chunk.text,
            "metadata": dict(document.metadata_json or {}) | dict(chunk.metadata_json or {}),
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
