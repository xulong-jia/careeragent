from datetime import datetime

from pydantic import BaseModel, Field


class RagDocumentCreateRequest(BaseModel):
    title: str
    source_type: str
    source_uri: str | None = None
    raw_text: str
    metadata: dict[str, object] = Field(default_factory=dict)


class RagDocumentIndexRequest(BaseModel):
    max_chars: int = Field(default=1200, ge=1, le=5000)
    overlap_chars: int = Field(default=0, ge=0, le=1000)


class RagSearchFilters(BaseModel):
    source_type: str | None = None
    doc_id: str | None = None
    tags: list[str] | None = None
    role_category: str | None = None
    company: str | None = None
    topic: str | None = None
    domain: str | None = None


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: RagSearchFilters | None = None


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


class RagDocumentIndexResult(BaseModel):
    doc_id: str
    index_status: str
    chunk_count: int
    chunks: list[RagChunkRecord] = Field(default_factory=list)


class RagSearchSource(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    source_type: str
    section: str | None = None
    snippet: str
    score: float
    metadata: dict[str, object] = Field(default_factory=dict)


class RagSearchResult(BaseModel):
    query: str
    top_k: int
    sources: list[RagSearchSource] = Field(default_factory=list)
    uncertainty: str | None = None
