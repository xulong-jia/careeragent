from datetime import datetime

from pydantic import BaseModel, Field


class RagDocumentRecord(BaseModel):
    doc_id: str
    title: str
    source_type: str
    source_uri: str | None = None
    raw_text_preview: str
    metadata: dict[str, object] = Field(default_factory=dict)
    index_status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class RagChunkRecord(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_index: int
    section: str | None = None
    text_preview: str
    token_count: int
    metadata: dict[str, object] = Field(default_factory=dict)
    embedding_id: str | None = None
    created_at: datetime
