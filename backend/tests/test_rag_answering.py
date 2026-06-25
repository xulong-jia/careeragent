from app.rag.answering import build_deterministic_answer
from app.schemas.rag import RagSearchSource


def test_build_deterministic_answer_returns_no_source_behavior():
    result = build_deterministic_answer("How should I prepare?", [])

    assert result["answer"] == ""
    assert result["sources"] == []
    assert result["uncertainty"] == "no_relevant_source"
    assert result["grounded"] is False
    assert result["answer_type"] == "deterministic_summary"
    assert result["evidence_summary"] == []
    assert result["citations"] == []
    assert result["source_refs"] == []
    assert result["retrieval_debug"].insufficient_reason == "no_relevant_source"


def test_build_deterministic_answer_uses_only_source_snippets():
    source = RagSearchSource(
        doc_id="rag_doc_0001",
        chunk_id="rag_doc_0001_chunk_0001",
        title="Synthetic Backend Notes",
        source_type="manual",
        section="Backend",
        snippet="FastAPI pytest coverage protects API contracts.",
        score=0.9,
        metadata={"topic": "quality"},
    )

    result = build_deterministic_answer(
        "How can I prepare for backend interviews?",
        [source],
        max_chars=300,
    )

    assert result["grounded"] is True
    assert result["uncertainty"] == "grounded"
    assert result["answer_type"] == "deterministic_summary"
    assert "Based on retrieved evidence" in result["answer"]
    assert "FastAPI pytest coverage" in result["answer"]
    assert result["sources"][0].chunk_id == source.chunk_id
    assert result["citations"][0].chunk_id == source.chunk_id
    assert result["source_refs"][0].source_id == source.chunk_id
    assert result["evidence_summary"]
    assert "full chunk text" not in result["answer"]


def test_build_deterministic_answer_marks_low_score_as_insufficient_evidence():
    source = RagSearchSource(
        doc_id="rag_doc_0001",
        chunk_id="rag_doc_0001_chunk_0001",
        title="Synthetic Weak Notes",
        source_type="manual",
        section=None,
        snippet="Weak incidental overlap.",
        score=0.001,
        metadata={"topic": "weak"},
    )

    result = build_deterministic_answer("How should I prepare?", [source])

    assert result["grounded"] is False
    assert result["uncertainty"] == "insufficient_evidence"
    assert result["answer"] == "Insufficient retrieved evidence to answer safely."
    assert result["citations"][0].chunk_id == source.chunk_id
    assert result["retrieval_debug"].insufficient_reason == "insufficient_evidence"
