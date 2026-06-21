from app.rag.answering import build_deterministic_answer
from app.schemas.rag import RagSearchSource


def test_build_deterministic_answer_returns_no_source_behavior():
    result = build_deterministic_answer("How should I prepare?", [])

    assert result["answer"] == ""
    assert result["sources"] == []
    assert result["uncertainty"] == "no_relevant_source"
    assert result["grounded"] is False
    assert result["answer_type"] == "deterministic_summary"


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
    assert result["uncertainty"] is None
    assert result["answer_type"] == "deterministic_summary"
    assert "基于检索来源" in result["answer"]
    assert "FastAPI pytest coverage" in result["answer"]
    assert result["sources"][0].chunk_id == source.chunk_id
    assert "full chunk text" not in result["answer"]
