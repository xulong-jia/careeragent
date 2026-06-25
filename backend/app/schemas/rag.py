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


class RagAnswerRequest(BaseModel):
    question: str
    top_k: int = 5
    filters: RagSearchFilters | None = None
    persist: bool = True


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


class RagCitation(BaseModel):
    source_type: str
    document_id: str
    chunk_id: str
    title: str
    section: str | None = None
    label: str
    snippet: str
    score: float | None = None
    metadata_preview: dict[str, object] = Field(default_factory=dict)


class RagSourceRef(BaseModel):
    source_type: str
    source_id: str
    document_id: str | None = None
    chunk_id: str | None = None
    field: str
    label: str
    preview: str
    score: float | None = None


class RagRetrievalDebug(BaseModel):
    retrieval_mode: str
    query_tokens: list[str] = Field(default_factory=list)
    candidate_count: int
    selected_chunk_ids: list[str] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    top_k: int
    filters: dict[str, object] = Field(default_factory=dict)
    insufficient_reason: str | None = None


class RagSearchResult(BaseModel):
    query: str
    top_k: int
    sources: list[RagSearchSource] = Field(default_factory=list)
    uncertainty: str | None = None
    retrieval_debug: RagRetrievalDebug | None = None


class RagAnswerResult(BaseModel):
    answer_run_id: str | None = None
    question: str
    answer: str
    sources: list[RagSearchSource] = Field(default_factory=list)
    uncertainty: str | None = None
    grounded: bool
    answer_type: str = "deterministic_summary"
    evidence_summary: list[str] = Field(default_factory=list)
    citations: list[RagCitation] = Field(default_factory=list)
    source_refs: list[RagSourceRef] = Field(default_factory=list)
    retrieval_debug: RagRetrievalDebug


class RagAnswerRunRecord(BaseModel):
    answer_run_id: str
    question: str
    filters: dict[str, object] = Field(default_factory=dict)
    top_k: int
    retrieval_mode: str
    answer: str
    answer_type: str
    grounded: bool
    uncertainty: str
    evidence_summary: list[str] = Field(default_factory=list)
    citations: list[RagCitation] = Field(default_factory=list)
    source_refs: list[RagSourceRef] = Field(default_factory=list)
    retrieval_debug: RagRetrievalDebug
    created_at: datetime
    updated_at: datetime


class RagStatsResponse(BaseModel):
    total_documents: int
    indexed_documents: int
    total_chunks: int
    total_answer_runs: int
    grounded_answer_runs: int
    ungrounded_answer_runs: int
    latest_answer_run_id: str | None = None
    latest_answer_question_preview: str | None = None
    latest_answer_uncertainty: str | None = None
    latest_answer_created_at: datetime | None = None
