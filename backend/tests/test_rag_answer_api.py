from conftest import get_data, get_error, make_client


def _create_and_index_document(
    client,
    *,
    title: str,
    raw_text: str,
    metadata: dict[str, object],
    source_type: str = "manual",
):
    create_response = client.post(
        "/api/rag/documents",
        json={
            "title": title,
            "source_type": source_type,
            "source_uri": f"synthetic://{title.lower().replace(' ', '-')}",
            "raw_text": raw_text,
            "metadata": metadata,
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


def test_answer_returns_grounded_result_with_citations():
    client = make_client()
    document = _create_and_index_document(
        client,
        title="Synthetic Interview Notes",
        raw_text=(
            "Backend interviews should discuss FastAPI service contracts, "
            "pytest coverage, and evidence-backed tradeoffs. "
            "This sentence should not appear when snippet limits apply."
        ),
        metadata={"tags": ["backend", "interview"], "topic": "interview"},
    )

    response = client.post(
        "/api/rag/answer",
        json={
            "question": "How should I prepare for FastAPI backend interviews?",
            "top_k": 1,
            "filters": {"tags": ["interview"]},
        },
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["question"] == "How should I prepare for FastAPI backend interviews?"
    assert result["grounded"] is True
    assert result["uncertainty"] is None
    assert result["answer_type"] == "deterministic_summary"
    assert "基于检索来源" in result["answer"]
    assert len(result["sources"]) == 1
    source = result["sources"][0]
    assert source["doc_id"] == document["doc_id"]
    assert source["chunk_id"]
    assert source["snippet"]
    assert source["score"] > 0
    assert source["metadata"]["topic"] == "interview"
    assert "raw_text" not in result
    assert "text" not in source


def test_answer_respects_filters_and_top_k():
    client = make_client()
    _create_and_index_document(
        client,
        title="Target Notes",
        raw_text="FastAPI interview preparation needs API contracts and pytest evidence.",
        metadata={"tags": ["backend"], "company": "SyntheticCo", "topic": "interview"},
    )
    _create_and_index_document(
        client,
        title="Other Notes",
        raw_text="FastAPI interview preparation for another company.",
        metadata={"tags": ["backend"], "company": "OtherCo", "topic": "interview"},
    )

    response = client.post(
        "/api/rag/answer",
        json={
            "question": "FastAPI interview preparation",
            "top_k": 1,
            "filters": {"company": "SyntheticCo"},
        },
    )

    assert response.status_code == 200
    result = get_data(response)
    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Target Notes"


def test_answer_returns_no_source_behavior():
    client = make_client()
    _create_and_index_document(
        client,
        title="Frontend Notes",
        raw_text="React dashboard state and CSS layout.",
        metadata={"tags": ["frontend"]},
    )

    response = client.post(
        "/api/rag/answer",
        json={"question": "Kubernetes distributed tracing"},
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["answer"] == ""
    assert result["sources"] == []
    assert result["uncertainty"] == "no_relevant_source"
    assert result["grounded"] is False


def test_answer_rejects_empty_question():
    client = make_client()

    response = client.post("/api/rag/answer", json={"question": "   "})

    assert response.status_code == 400
    assert get_error(response)["code"] == "rag_answer_validation_error"
