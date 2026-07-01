from conftest import get_data, get_error, make_client


def _create_document(
    client,
    title="Synthetic RAG Notes",
    source_type="manual",
    raw_text=None,
):
    return client.post(
        "/api/rag/documents",
        json={
            "title": title,
            "source_type": source_type,
            "source_uri": "synthetic://rag-notes",
            "raw_text": raw_text
            or (
                "# CareerAgent\n\n"
                "Resume workflows use persistent records.\n\n"
                "## Matching\n\n"
                "Match reports keep version and job identifiers."
            ),
            "metadata": {"fixture": "synthetic", "category": "rag-test"},
        },
    )


def test_create_list_and_get_rag_document_preview_only():
    client = make_client()

    response = _create_document(client)
    assert response.status_code == 201
    document = get_data(response)
    assert document["doc_id"].startswith("rag_doc_")
    assert document["title"] == "Synthetic RAG Notes"
    assert document["index_status"] == "pending"
    assert document["chunk_count"] == 0
    assert "raw_text" not in document
    assert "Resume workflows" in document["raw_text_preview"]

    list_response = client.get("/api/rag/documents")
    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 1
    assert listed["items"][0]["doc_id"] == document["doc_id"]

    detail_response = client.get(f"/api/rag/documents/{document['doc_id']}")
    assert detail_response.status_code == 200
    detail = get_data(detail_response)
    assert detail["doc_id"] == document["doc_id"]
    assert "raw_text" not in detail


def test_create_rag_document_rejects_invalid_input():
    client = make_client()

    empty_response = client.post(
        "/api/rag/documents",
        json={
            "title": "Empty",
            "source_type": "manual",
            "raw_text": "   ",
            "metadata": {},
        },
    )
    assert empty_response.status_code == 400
    assert get_error(empty_response)["code"] == "rag_document_validation_error"

    invalid_type_response = client.post(
        "/api/rag/documents",
        json={
            "title": "Invalid",
            "source_type": "unknown",
            "raw_text": "Synthetic notes only.",
            "metadata": {},
        },
    )
    assert invalid_type_response.status_code == 400
    assert get_error(invalid_type_response)["code"] == "rag_document_validation_error"


def test_index_document_creates_and_replaces_chunks():
    client = make_client()
    document = get_data(
        _create_document(
            client,
            raw_text="# Long Notes\n\n" + " ".join(["deterministic indexing"] * 80),
        )
    )

    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 80, "overlap_chars": 0},
    )
    assert index_response.status_code == 200
    index_result = get_data(index_response)
    assert index_result["doc_id"] == document["doc_id"]
    assert index_result["index_status"] == "indexed"
    assert index_result["chunk_count"] == len(index_result["chunks"])
    assert index_result["chunk_count"] > 0
    assert all("text" not in chunk for chunk in index_result["chunks"])

    chunks_response = client.get(f"/api/rag/chunks?doc_id={document['doc_id']}")
    assert chunks_response.status_code == 200
    chunks = get_data(chunks_response)
    first_count = chunks["total"]
    assert first_count == index_result["chunk_count"]
    assert all(item["doc_id"] == document["doc_id"] for item in chunks["items"])
    assert all("text" not in item for item in chunks["items"])
    assert all(item["embedding_id"] for item in chunks["items"])
    assert all(item["embedding_provider"] == "local_bow" for item in chunks["items"])
    assert all(item["embedding_model"] == "local-bow-v1" for item in chunks["items"])
    assert all(item["embedding_dim"] == 384 for item in chunks["items"])
    assert all(item["embedding_version"] == "local-bow-v1" for item in chunks["items"])
    assert all(item["embedding_created_at"] for item in chunks["items"])
    assert all("embedding_vector" not in item for item in chunks["items"])

    reindex_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 400, "overlap_chars": 0},
    )
    assert reindex_response.status_code == 200
    reindex_result = get_data(reindex_response)
    assert reindex_result["chunk_count"] < first_count

    replaced_chunks = get_data(client.get(f"/api/rag/chunks?doc_id={document['doc_id']}"))
    assert replaced_chunks["total"] == reindex_result["chunk_count"]


def test_list_rag_documents_and_chunks_support_filters():
    client = make_client()
    manual_doc = get_data(_create_document(client, "Manual Notes", "manual"))
    markdown_doc = get_data(_create_document(client, "Markdown Notes", "markdown"))

    client.post(f"/api/rag/documents/{manual_doc['doc_id']}/index", json={"max_chars": 120})
    client.post(f"/api/rag/documents/{markdown_doc['doc_id']}/index", json={"max_chars": 120})

    docs_response = client.get("/api/rag/documents?source_type=markdown&index_status=indexed")
    assert docs_response.status_code == 200
    docs = get_data(docs_response)
    assert docs["total"] == 1
    assert docs["items"][0]["doc_id"] == markdown_doc["doc_id"]

    chunks_response = client.get("/api/rag/chunks?source_type=markdown")
    assert chunks_response.status_code == 200
    chunks = get_data(chunks_response)
    assert chunks["total"] > 0
    assert {chunk["doc_id"] for chunk in chunks["items"]} == {markdown_doc["doc_id"]}


def test_missing_rag_document_returns_unified_error():
    client = make_client()

    detail_response = client.get("/api/rag/documents/missing-doc")
    assert detail_response.status_code == 404
    assert get_error(detail_response)["code"] == "rag_document_not_found"

    index_response = client.post(
        "/api/rag/documents/missing-doc/index",
        json={"max_chars": 120},
    )
    assert index_response.status_code == 404
    assert get_error(index_response)["code"] == "rag_document_not_found"
