from app.rag.retriever import rank_chunks, tokenize_text


def test_tokenize_text_handles_english_and_cjk_terms():
    tokens = tokenize_text("FastAPI 简历 matching, RAG!")

    assert "fastapi" in tokens
    assert "matching" in tokens
    assert "rag" in tokens
    assert "简历" in tokens


def test_rank_chunks_scores_and_sorts_relevant_sources():
    candidates = [
        {
            "doc_id": "rag_doc_0001",
            "chunk_id": "chunk_1",
            "title": "Backend Notes",
            "source_type": "manual",
            "section": "FastAPI",
            "text": "FastAPI services need pytest coverage and stable API contracts.",
            "metadata": {"tags": ["backend"], "topic": "testing"},
        },
        {
            "doc_id": "rag_doc_0002",
            "chunk_id": "chunk_2",
            "title": "Frontend Notes",
            "source_type": "manual",
            "section": "React",
            "text": "React pages display dashboard lists.",
            "metadata": {"tags": ["frontend"], "topic": "ui"},
        },
    ]

    ranked = rank_chunks("FastAPI pytest", candidates, top_k=5, filters={})

    assert [source["chunk_id"] for source in ranked] == ["chunk_1"]
    assert ranked[0]["score"] > 0
    assert "FastAPI" in ranked[0]["snippet"]
    assert "text" not in ranked[0]


def test_rank_chunks_applies_metadata_filters_and_top_k():
    candidates = [
        {
            "doc_id": "rag_doc_0001",
            "chunk_id": "chunk_1",
            "title": "Backend Notes",
            "source_type": "manual",
            "section": "Testing",
            "text": "pytest FastAPI testing notes",
            "metadata": {
                "tags": ["backend", "testing"],
                "topic": "quality",
                "company": "SyntheticCo",
                "domain": "career",
            },
        },
        {
            "doc_id": "rag_doc_0002",
            "chunk_id": "chunk_2",
            "title": "Backend Notes 2",
            "source_type": "manual",
            "section": "Testing",
            "text": "pytest FastAPI testing notes",
            "metadata": {
                "tags": ["backend"],
                "topic": "quality",
                "company": "OtherCo",
                "domain": "career",
            },
        },
    ]

    ranked = rank_chunks(
        "pytest FastAPI",
        candidates,
        top_k=1,
        filters={"tags": ["testing"], "company": "SyntheticCo", "domain": "career"},
    )

    assert len(ranked) == 1
    assert ranked[0]["chunk_id"] == "chunk_1"


def test_rank_chunks_returns_empty_when_no_relevant_source():
    ranked = rank_chunks(
        "golang distributed tracing",
        [
            {
                "doc_id": "rag_doc_0001",
                "chunk_id": "chunk_1",
                "title": "Resume Notes",
                "source_type": "manual",
                "section": None,
                "text": "React dashboard state only.",
                "metadata": {},
            }
        ],
        top_k=5,
        filters={},
    )

    assert ranked == []
