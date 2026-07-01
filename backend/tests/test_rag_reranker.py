from app.rag.reranker import rerank_sources


def test_local_reranker_adds_scores_without_raw_text():
    sources = [
        {
            "doc_id": "doc_1",
            "chunk_id": "chunk_low",
            "title": "General notes",
            "source_type": "manual",
            "snippet": "General interview preparation.",
            "score": 0.9,
            "metadata": {"topic": "general"},
        },
        {
            "doc_id": "doc_1",
            "chunk_id": "chunk_high",
            "title": "FastAPI notes",
            "source_type": "manual",
            "snippet": "FastAPI service contracts and pytest coverage.",
            "score": 0.8,
            "metadata": {"topic": "FastAPI backend"},
        },
    ]

    reranked = rerank_sources(
        "FastAPI pytest",
        sources,
        reranker_mode="local_score",
        reranker_model="local-score-v1",
    )

    assert reranked[0]["chunk_id"] == "chunk_high"
    assert reranked[0]["original_score"] == 0.8
    assert reranked[0]["rerank_score"] > 0
    assert reranked[0]["final_score"] == reranked[0]["score"]
    assert reranked[0]["reranker_mode"] == "local_score"
    assert "text" not in reranked[0]


def test_provider_reranker_uses_supplied_scores():
    sources = [
        {
            "doc_id": "doc_1",
            "chunk_id": "chunk_a",
            "title": "A",
            "source_type": "manual",
            "snippet": "A",
            "score": 0.7,
            "metadata": {},
        },
        {
            "doc_id": "doc_1",
            "chunk_id": "chunk_b",
            "title": "B",
            "source_type": "manual",
            "snippet": "B",
            "score": 0.7,
            "metadata": {},
        },
    ]

    reranked = rerank_sources(
        "query",
        sources,
        reranker_mode="provider",
        provider_scores={"chunk_b": 1.0},
    )

    assert [source["chunk_id"] for source in reranked] == ["chunk_b", "chunk_a"]
    assert reranked[0]["reranker_mode"] == "provider"
