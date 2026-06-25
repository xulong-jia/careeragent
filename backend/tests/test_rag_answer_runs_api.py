from conftest import get_data, get_error, make_client


SENSITIVE_KEYS = {"raw_text", "text", "answer_text", "chunk_text", "full_text"}


def _create_and_index_document(
    client,
    *,
    title: str = "Synthetic RAG Answer Notes",
    source_type: str = "manual",
    raw_text: str = "FastAPI interview answers need pytest evidence and API contract examples.",
    metadata: dict[str, object] | None = None,
):
    create_response = client.post(
        "/api/rag/documents",
        json={
            "title": title,
            "source_type": source_type,
            "source_uri": f"synthetic://{title.lower().replace(' ', '-')}",
            "raw_text": raw_text,
            "metadata": metadata or {"tags": ["backend"], "topic": "interview"},
        },
    )
    assert create_response.status_code == 201
    document = get_data(create_response)
    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 180, "overlap_chars": 0},
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


def test_answer_persists_run_by_default_and_can_fetch_detail():
    client = make_client()
    document = _create_and_index_document(client)

    response = client.post(
        "/api/rag/answer",
        json={"question": "FastAPI pytest API contract examples", "top_k": 1},
    )

    assert response.status_code == 200
    answer = get_data(response)
    assert answer["answer_run_id"]
    assert answer["grounded"] is True
    assert answer["citations"]
    assert answer["source_refs"]
    assert answer["evidence_summary"]

    list_response = client.get("/api/rag/answers")
    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 1
    answer_run = listed["items"][0]
    assert answer_run["answer_run_id"] == answer["answer_run_id"]
    assert answer_run["question"] == "FastAPI pytest API contract examples"
    assert answer_run["grounded"] is True
    assert answer_run["uncertainty"] == "grounded"
    assert answer_run["citations"][0]["document_id"] == document["doc_id"]
    assert answer_run["source_refs"][0]["source_type"] == "rag_chunk"

    detail_response = client.get(f"/api/rag/answers/{answer['answer_run_id']}")
    assert detail_response.status_code == 200
    detail = get_data(detail_response)
    assert detail["answer_run_id"] == answer["answer_run_id"]
    assert detail["retrieval_debug"]["selected_chunk_ids"]
    assert detail["retrieval_debug"]["candidate_count"] >= 1


def test_answer_with_persist_false_does_not_create_answer_run():
    client = make_client()
    _create_and_index_document(client)

    response = client.post(
        "/api/rag/answer",
        json={
            "question": "FastAPI pytest API contract examples",
            "top_k": 1,
            "persist": False,
        },
    )

    assert response.status_code == 200
    answer = get_data(response)
    assert answer["answer_run_id"] is None

    list_response = client.get("/api/rag/answers")
    assert list_response.status_code == 200
    assert get_data(list_response) == {"items": [], "total": 0}


def test_answer_run_list_filters_and_missing_detail_error():
    client = make_client()
    _create_and_index_document(client)
    grounded_response = client.post(
        "/api/rag/answer",
        json={"question": "FastAPI pytest API contract examples"},
    )
    assert grounded_response.status_code == 200
    no_source_response = client.post(
        "/api/rag/answer",
        json={"question": "kubernetes tracing observability"},
    )
    assert no_source_response.status_code == 200

    grounded_list = get_data(client.get("/api/rag/answers?grounded=true"))
    assert grounded_list["total"] == 1
    assert grounded_list["items"][0]["grounded"] is True

    no_source_list = get_data(client.get("/api/rag/answers?uncertainty=no_relevant_source"))
    assert no_source_list["total"] == 1
    assert no_source_list["items"][0]["grounded"] is False

    mode_list = get_data(client.get("/api/rag/answers?retrieval_mode=deterministic_lexical"))
    assert mode_list["total"] == 2

    invalid_filter = client.get("/api/rag/answers?uncertainty=unsupported")
    assert invalid_filter.status_code == 400
    assert get_error(invalid_filter)["code"] == "rag_answer_run_filter_validation_error"

    missing_response = client.get("/api/rag/answers/missing-run")
    assert missing_response.status_code == 404
    assert get_error(missing_response)["code"] == "rag_answer_run_not_found"


def test_persisted_answer_run_privacy_contract():
    client = make_client()
    private_marker = "PRIVATE_FULL_CHUNK_MARKER"
    _create_and_index_document(
        client,
        title="Synthetic Privacy RAG Notes",
        raw_text="FastAPI citations should stay snippet-first. " + " ".join([private_marker] * 80),
        metadata={
            "topic": "privacy",
            "raw_text": "must not persist",
            "answer_text": "must not persist",
            "text": "must not persist",
        },
    )

    response = client.post(
        "/api/rag/answer",
        json={"question": "FastAPI citations snippet", "top_k": 1},
    )
    assert response.status_code == 200
    answer = get_data(response)
    detail = get_data(client.get(f"/api/rag/answers/{answer['answer_run_id']}"))

    serialized = str(detail)
    assert "must not persist" not in serialized
    assert "raw_text" not in detail
    assert "chunk_text" not in serialized
    assert "answer_text" not in serialized
    assert len(detail["citations"][0]["snippet"]) <= 240
    assert len(detail["source_refs"][0]["preview"]) <= 240
    _assert_no_sensitive_keys(detail["citations"])
    _assert_no_sensitive_keys(detail["source_refs"])
    _assert_no_sensitive_keys(detail["retrieval_debug"])
