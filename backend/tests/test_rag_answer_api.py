from conftest import get_data, get_error, make_client


SENSITIVE_KEYS = {"raw_text", "text", "answer_text", "chunk_text", "full_text"}


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


def _assert_no_sensitive_keys(value):
    if isinstance(value, dict):
        for key, nested_value in value.items():
            assert key not in SENSITIVE_KEYS
            _assert_no_sensitive_keys(nested_value)
    elif isinstance(value, list):
        for item in value:
            _assert_no_sensitive_keys(item)


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
    assert result["uncertainty"] == "grounded"
    assert result["answer_type"] == "deterministic_summary"
    assert result["retrieval_mode"] == "lexical"
    assert "Based on retrieved evidence" in result["answer"]
    assert len(result["sources"]) == 1
    source = result["sources"][0]
    assert source["doc_id"] == document["doc_id"]
    assert source["chunk_id"]
    assert source["snippet"]
    assert source["score"] > 0
    assert source["metadata"]["topic"] == "interview"
    assert "raw_text" not in result
    assert "text" not in source
    assert len(result["citations"]) == 1
    citation = result["citations"][0]
    assert citation["source_type"] == "manual"
    assert citation["document_id"] == document["doc_id"]
    assert citation["chunk_id"] == source["chunk_id"]
    assert citation["label"] == "Synthetic Interview Notes"
    assert citation["snippet"] == source["snippet"]
    assert len(citation["snippet"]) <= 240
    assert citation["score"] == source["score"]
    assert citation["metadata_preview"]["topic"] == "interview"
    assert len(result["source_refs"]) == 1
    source_ref = result["source_refs"][0]
    assert source_ref["source_type"] == "rag_chunk"
    assert source_ref["source_id"] == source["chunk_id"]
    assert source_ref["document_id"] == document["doc_id"]
    assert source_ref["chunk_id"] == source["chunk_id"]
    assert source_ref["field"] == "snippet"
    assert source_ref["preview"] == source["snippet"]
    assert result["evidence_summary"]
    assert result["evidence_used"] == result["evidence_summary"]
    debug = result["retrieval_debug"]
    assert debug["retrieval_mode"] == "lexical"
    assert "fastapi" in debug["query_tokens"]
    assert debug["candidate_count"] >= 1
    assert debug["selected_chunk_ids"] == [source["chunk_id"]]
    assert debug["scores"] == [source["score"]]
    assert debug["top_k"] == 1
    assert debug["filters"] == {"tags": ["interview"]}


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
    assert result["retrieval_mode"] == "lexical"
    assert result["evidence_used"] == []
    assert result["citations"] == []
    assert result["source_refs"] == []
    assert result["evidence_summary"] == []
    assert result["retrieval_debug"]["insufficient_reason"] == "no_relevant_source"
    assert result["retrieval_debug"]["selected_chunk_ids"] == []


def test_answer_rejects_empty_question():
    client = make_client()

    response = client.post("/api/rag/answer", json={"question": "   "})

    assert response.status_code == 400
    assert get_error(response)["code"] == "rag_answer_validation_error"


def test_answer_contract_does_not_expose_full_text_in_citations_or_debug():
    client = make_client()
    full_private_marker = "PRIVATE_FULL_CHUNK_MARKER"
    document = _create_and_index_document(
        client,
        title="Synthetic Privacy Notes",
        raw_text=(
            "FastAPI evidence should use snippets and citations. "
            + " ".join([full_private_marker] * 80)
        ),
        metadata={
            "topic": "privacy",
            "raw_text": "should not appear",
            "answer_text": "should not appear",
            "text": "should not appear",
        },
    )

    response = client.post(
        "/api/rag/answer",
        json={"question": "FastAPI evidence citations", "top_k": 1},
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["citations"][0]["document_id"] == document["doc_id"]
    assert len(result["citations"][0]["snippet"]) <= 240
    assert "should not appear" not in str(result["citations"])
    assert "should not appear" not in str(result["source_refs"])
    _assert_no_sensitive_keys(result["citations"])
    _assert_no_sensitive_keys(result["source_refs"])
    _assert_no_sensitive_keys(result["retrieval_debug"])


def test_answer_persists_vector_retrieval_mode_and_filter_alias():
    client = make_client()
    _create_and_index_document(
        client,
        title="Vector Answer Notes",
        raw_text="FastAPI vector retrieval should keep citations and source refs.",
        metadata={"tags": ["backend"], "topic": "retrieval"},
    )

    answer_response = client.post(
        "/api/rag/answer",
        json={
            "question": "FastAPI vector retrieval",
            "retrieval_mode": "vector",
        },
    )

    assert answer_response.status_code == 200
    result = get_data(answer_response)
    assert result["retrieval_mode"] == "vector"
    assert result["retrieval_debug"]["retrieval_mode"] == "vector"
    assert result["retrieval_debug"]["vector_index_used"] is True
    assert result["answer_run_id"]

    list_response = client.get("/api/rag/answers?retrieval_mode=vector")
    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert [item["answer_run_id"] for item in listed["items"]] == [
        result["answer_run_id"]
    ]
