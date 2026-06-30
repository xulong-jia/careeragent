from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="default_workspace", nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_uri: Mapped[str | None] = mapped_column(String(500))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    index_status: Mapped[str] = mapped_column(
        String(40), default="pending", nullable=False, index=True
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    chunks: Mapped[list["RagChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_rag_chunks_document_id_chunk_index",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("rag_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(240))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    embedding_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    document: Mapped[RagDocument] = relationship(back_populates="chunks")


class RagAnswerRun(Base):
    __tablename__ = "rag_answer_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        default="default",
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="default_workspace", nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(
        String(40),
        default="deterministic_lexical",
        nullable=False,
        index=True,
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    answer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    uncertainty: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    evidence_summary: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    citations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retrieval_debug_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
