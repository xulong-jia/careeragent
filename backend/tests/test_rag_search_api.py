from conftest import get_data, get_error, make_client
from app.ai.embedding_provider import LocalVectorEmbeddingProvider


def _create_and_index_document(
    client,
    *,
    title: str,
    source_type: str = "manual",
    raw_text: str,
    metadata: dict[str, object],
):
    document_response = client.post(
        "/api/rag/documents",
        json={
            "title": title,
            "source_type": source_type,
            "source_uri": f"synthetic://{title.lower().replace(' ', '-')}",
            "raw_text": raw_text,
            "metadata": metadata,
        },
    )
    assert document_response.status_code == 201
    document = get_data(document_response)
    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 160, "overlap_chars": 0},
    )
    assert index_response.status_code == 200
    return document


def test_search_returns_relevant_sources_with_snippets_and_scores():
    client = make_client()
    document = _create_and_index_document(
        client,
        title="Synthetic Backend Notes",
        raw_text=(
            "# Backend\n\n"
            "FastAPI pytest coverage protects CareerAgent service contracts.\n\n"
            "React dashboard text is unrelated."
        ),
        metadata={"tags": ["backend", "testing"], "topic": "quality"},
    )

    response = client.post(
        "/api/rag/search",
        json={"query": "FastAPI pytest contracts", "top_k": 5},
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["query"] == "FastAPI pytest contracts"
    assert result["top_k"] == 5
    assert result["uncertainty"] is None
    assert len(result["sources"]) >= 1
    source = result["sources"][0]
    assert source["doc_id"] == document["doc_id"]
    assert source["chunk_id"]
    assert source["title"] == "Synthetic Backend Notes"
    assert source["source_type"] == "manual"
    assert source["score"] > 0
    assert "FastAPI" in source["snippet"]
    assert source["metadata"]["topic"] == "quality"
    assert "text" not in source
    assert "raw_text" not in source


def test_search_respects_top_k_and_source_type_filter():
    client = make_client()
    _create_and_index_document(
        client,
        title="Manual Backend",
        source_type="manual",
        raw_text="FastAPI pytest backend testing notes.",
        metadata={"tags": ["backend"]},
    )
    _create_and_index_document(
        client,
        title="Markdown Backend",
        source_type="markdown",
        raw_text="# Backend\n\nFastAPI pytest markdown notes.",
        metadata={"tags": ["backend"]},
    )

    response = client.post(
        "/api/rag/search",
        json={
            "query": "FastAPI pytest",
            "top_k": 1,
            "filters": {"source_type": "markdown"},
        },
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["top_k"] == 1
    assert len(result["sources"]) == 1
    assert result["sources"][0]["source_type"] == "markdown"


def test_search_orders_clear_keyword_match_above_weaker_match():
    client = make_client()
    strong = _create_and_index_document(
        client,
        title="Strong FastAPI Notes",
        raw_text=(
            "FastAPI FastAPI pytest API contracts require evidence-backed "
            "backend interview examples."
        ),
        metadata={"tags": ["backend"]},
    )
    _create_and_index_document(
        client,
        title="Weak FastAPI Notes",
        raw_text="FastAPI backend notes mention interviews only briefly.",
        metadata={"tags": ["backend"]},
    )

    response = client.post(
        "/api/rag/search",
        json={"query": "FastAPI pytest API contracts", "top_k": 2},
    )

    assert response.status_code == 200
    result = get_data(response)
    assert len(result["sources"]) == 2
    assert result["sources"][0]["doc_id"] == strong["doc_id"]
    assert result["sources"][0]["score"] > result["sources"][1]["score"]


def test_search_respects_doc_id_and_metadata_filters():
    client = make_client()
    target = _create_and_index_document(
        client,
        title="Target Notes",
        raw_text="FastAPI testing notes for SyntheticCo interview preparation.",
        metadata={
            "tags": ["backend", "interview"],
            "topic": "interview",
            "company": "SyntheticCo",
            "domain": "career",
            "role_category": "AI Application Engineer",
        },
    )
    _create_and_index_document(
        client,
        title="Other Notes",
        raw_text="FastAPI testing notes for another company.",
        metadata={
            "tags": ["backend"],
            "topic": "quality",
            "company": "OtherCo",
            "domain": "career",
        },
    )

    response = client.post(
        "/api/rag/search",
        json={
            "query": "FastAPI interview testing",
            "filters": {
                "doc_id": target["doc_id"],
                "tags": ["interview"],
                "topic": "interview",
                "company": "SyntheticCo",
                "domain": "career",
                "role_category": "AI Application Engineer",
            },
        },
    )

    assert response.status_code == 200
    result = get_data(response)
    assert {source["doc_id"] for source in result["sources"]} == {target["doc_id"]}


def test_search_returns_uncertainty_when_no_relevant_source():
    client = make_client()
    _create_and_index_document(
        client,
        title="Frontend Notes",
        raw_text="React dashboard rendering and local UI state.",
        metadata={"tags": ["frontend"]},
    )

    response = client.post(
        "/api/rag/search",
        json={"query": "kubernetes distributed tracing"},
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["sources"] == []
    assert result["uncertainty"] == "no_relevant_source"


def test_search_rejects_empty_query_and_caps_top_k():
    client = make_client()

    empty_response = client.post("/api/rag/search", json={"query": "   "})
    assert empty_response.status_code == 400
    assert get_error(empty_response)["code"] == "rag_search_validation_error"

    _create_and_index_document(
        client,
        title="Backend Notes",
        raw_text="FastAPI pytest backend testing notes.",
        metadata={"tags": ["backend"]},
    )
    capped_response = client.post(
        "/api/rag/search",
        json={"query": "FastAPI", "top_k": 100},
    )
    assert capped_response.status_code == 200
    assert get_data(capped_response)["top_k"] == 20


def test_search_supports_vector_mode_without_full_text():
    client = make_client()
    document = _create_and_index_document(
        client,
        title="Vector Backend Notes",
        raw_text="FastAPI pytest retrieval testing notes.",
        metadata={"tags": ["backend"], "topic": "retrieval"},
    )

    response = client.post(
        "/api/rag/search",
        json={
            "query": "FastAPI retrieval",
            "top_k": 3,
            "retrieval_mode": "vector",
            "score_threshold": 0,
        },
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["retrieval_debug"]["retrieval_mode"] == "vector"
    assert result["retrieval_debug"]["embedding_provider"] == "local_bow"
    assert result["retrieval_debug"]["embedding_model"] == "local-bow-v1"
    assert result["retrieval_debug"]["vector_index_used"] is True
    assert result["sources"][0]["doc_id"] == document["doc_id"]
    assert result["sources"][0]["retrieval_mode"] == "vector"
    assert result["sources"][0]["embedding_provider"] == "local_bow"
    assert result["sources"][0]["embedding_model"] == "local-bow-v1"
    assert result["sources"][0]["vector_index_used"] is True
    assert "text" not in result["sources"][0]
    assert "raw_text" not in str(result)


def test_index_writes_embedding_metadata_without_raw_chunk_text():
    client = make_client()
    document_response = client.post(
        "/api/rag/documents",
        json={
            "title": "Embedding Metadata Notes",
            "source_type": "manual",
            "raw_text": "FastAPI embedding metadata should store provider details only.",
            "metadata": {"topic": "embedding"},
        },
    )
    assert document_response.status_code == 201
    document = get_data(document_response)

    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 160, "overlap_chars": 0},
    )

    assert index_response.status_code == 200
    chunk = get_data(index_response)["chunks"][0]
    embedding_metadata = chunk["metadata"]["embedding"]
    assert embedding_metadata["provider"] == "local_bow"
    assert embedding_metadata["provider_config_id"] == "local-bow-default"
    assert embedding_metadata["vector_source"] == "local_bow_hash"
    assert embedding_metadata["semantic"] is False
    assert embedding_metadata["input_hash"]
    assert "FastAPI embedding metadata" not in str(embedding_metadata)
    assert "text" not in embedding_metadata


def test_vector_search_uses_persisted_chunk_vector(monkeypatch):
    client = make_client()
    document = _create_and_index_document(
        client,
        title="Persisted Vector Notes",
        raw_text="FastAPI persisted vector retrieval keeps chunk embeddings in storage.",
        metadata={"tags": ["backend"], "topic": "retrieval"},
    )
    calls = []
    original_embed = LocalVectorEmbeddingProvider.embed_text

    def spy_embed(self, text):
        calls.append(text)
        return original_embed(self, text)

    monkeypatch.setattr(LocalVectorEmbeddingProvider, "embed_text", spy_embed)

    response = client.post(
        "/api/rag/search",
        json={"query": "FastAPI persisted vector", "retrieval_mode": "vector"},
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["sources"][0]["doc_id"] == document["doc_id"]
    assert calls == ["FastAPI persisted vector"]


def test_search_supports_hybrid_mode_and_legacy_alias():
    client = make_client()
    document = _create_and_index_document(
        client,
        title="Hybrid Backend Notes",
        raw_text="Hybrid retrieval combines FastAPI lexical evidence with persisted vectors.",
        metadata={"tags": ["backend"], "topic": "retrieval"},
    )

    response = client.post(
        "/api/rag/search",
        json={
            "query": "FastAPI persisted vectors",
            "retrieval_mode": "deterministic_hybrid",
        },
    )

    assert response.status_code == 200
    result = get_data(response)
    assert result["retrieval_debug"]["retrieval_mode"] == "hybrid"
    assert result["retrieval_debug"]["vector_index_used"] is True
    assert result["sources"][0]["doc_id"] == document["doc_id"]


def test_search_rejects_unsupported_retrieval_mode():
    client = make_client()

    response = client.post(
        "/api/rag/search",
        json={"query": "FastAPI", "retrieval_mode": "unsupported"},
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "rag_search_validation_error"
