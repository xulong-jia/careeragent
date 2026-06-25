from conftest import get_data, make_client


SENSITIVE_KEYS = {
    "raw_text",
    "text",
    "answer_text",
    "chunk_text",
    "full_text",
    "citations",
    "source_refs",
    "retrieval_debug",
}


def _assert_no_sensitive_keys(value):
    if isinstance(value, dict):
        for key, nested_value in value.items():
            assert key not in SENSITIVE_KEYS
            _assert_no_sensitive_keys(nested_value)
    elif isinstance(value, list):
        for item in value:
            _assert_no_sensitive_keys(item)


def _create_and_index_document(client):
    create_response = client.post(
        "/api/rag/documents",
        json={
            "title": "Synthetic RAG Stats Notes",
            "source_type": "manual",
            "source_uri": "synthetic://rag-stats",
            "raw_text": "FastAPI pytest evidence makes grounded RAG answers testable.",
            "metadata": {"topic": "rag_stats"},
        },
    )
    assert create_response.status_code == 201
    document = get_data(create_response)
    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 160, "overlap_chars": 0},
    )
    assert index_response.status_code == 200
    return document


def test_rag_stats_empty():
    client = make_client()

    response = client.get("/api/rag/stats")

    assert response.status_code == 200
    stats = get_data(response)
    assert stats == {
        "total_documents": 0,
        "indexed_documents": 0,
        "total_chunks": 0,
        "total_answer_runs": 0,
        "grounded_answer_runs": 0,
        "ungrounded_answer_runs": 0,
        "latest_answer_run_id": None,
        "latest_answer_question_preview": None,
        "latest_answer_uncertainty": None,
        "latest_answer_created_at": None,
    }


def test_rag_stats_after_index_and_answer_runs_is_privacy_safe():
    client = make_client()
    _create_and_index_document(client)

    grounded_response = client.post(
        "/api/rag/answer",
        json={"question": "FastAPI pytest evidence", "top_k": 1},
    )
    assert grounded_response.status_code == 200
    grounded = get_data(grounded_response)
    assert grounded["grounded"] is True

    ungrounded_response = client.post(
        "/api/rag/answer",
        json={"question": "unrelated blockchain revenue metric", "top_k": 1},
    )
    assert ungrounded_response.status_code == 200
    ungrounded = get_data(ungrounded_response)
    assert ungrounded["grounded"] is False

    response = client.get("/api/rag/stats")

    assert response.status_code == 200
    stats = get_data(response)
    assert stats["total_documents"] == 1
    assert stats["indexed_documents"] == 1
    assert stats["total_chunks"] >= 1
    assert stats["total_answer_runs"] == 2
    assert stats["grounded_answer_runs"] == 1
    assert stats["ungrounded_answer_runs"] == 1
    assert stats["latest_answer_run_id"] == ungrounded["answer_run_id"]
    assert stats["latest_answer_question_preview"] == "unrelated blockchain revenue metric"
    assert stats["latest_answer_uncertainty"] == "no_relevant_source"
    assert stats["latest_answer_created_at"]
    _assert_no_sensitive_keys(stats)
