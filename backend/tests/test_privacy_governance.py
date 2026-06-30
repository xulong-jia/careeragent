import json

from app.core.privacy import redact_mapping, redact_text, safe_preview
from app.core.versioning import (
    EVALUATION_VERSION,
    MODEL_VERSION,
    PROMPT_VERSION,
    RETRIEVAL_VERSION,
    SCHEMA_VERSION,
)
from conftest import get_data, get_error, make_client


PRIVATE_RESUME_TEXT = (
    "PRIVATE_RESUME_FULL_TEXT Alice Candidate alice@example.com +1 415 555 1212 "
    "Python FastAPI RAG delivery evidence. "
    + "resume-private-filler " * 80
    + "RESUME_PRIVATE_UNIQUE_TAIL"
)
PRIVATE_JD_TEXT = (
    "PRIVATE_JD_FULL_TEXT Platform role needs Python FastAPI RAG React testing. "
    + "jd-private-filler " * 80
    + "JD_PRIVATE_UNIQUE_TAIL"
)
PRIVATE_RAG_TEXT = (
    "PRIVATE_RAG_FULL_CHUNK_TEXT FastAPI interview prep and source-backed answers. "
    + "rag-private-filler " * 80
    + "RAG_PRIVATE_UNIQUE_TAIL"
)


def _create_resume(client):
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.md", PRIVATE_RESUME_TEXT.encode(), "text/markdown")},
    )
    assert response.status_code == 201
    resume = get_data(response)
    versions = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))
    return resume, versions["items"][0]["resume_version_id"]


def _create_job(client):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Privacy Co",
            "job_title": "AI Application Engineer",
            "location": "Remote",
            "raw_text": PRIVATE_JD_TEXT,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_application(client, *, jd_id: str, resume_version_id: str):
    response = client.post(
        "/api/applications",
        json={
            "company": "Privacy Co",
            "role_title": "AI Application Engineer",
            "jd_id": jd_id,
            "resume_version_id": resume_version_id,
            "notes": "short operational note",
            "interview_notes": "brief interview summary only",
            "reflection": "brief reflection only",
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_rag_document(client):
    response = client.post(
        "/api/rag/documents",
        json={
            "title": "Privacy RAG Notes",
            "source_type": "manual",
            "raw_text": PRIVATE_RAG_TEXT,
            "metadata": {"topic": "privacy"},
        },
    )
    assert response.status_code == 201
    document = get_data(response)
    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 300},
    )
    assert index_response.status_code == 200
    return document


def test_redaction_helpers_mask_sensitive_values():
    secret = "OPENAI_API_KEY=sk-testsecret123456789 alice@example.com +1 415 555 1212"
    assert "alice@example.com" not in safe_preview(secret)
    assert "sk-testsecret" not in safe_preview(secret)

    redacted_text = redact_text(secret)
    assert "length=" in redacted_text
    assert "sha256=" in redacted_text
    assert "sk-testsecret" not in redacted_text

    payload = {
        "raw_text": PRIVATE_RESUME_TEXT,
        "nested": {
            "api_key": "sk-nestedsecret123456789",
            "summary": "contact alice@example.com",
        },
    }
    redacted = redact_mapping(payload)
    redacted_dump = json.dumps(redacted)
    assert "RESUME_PRIVATE_UNIQUE_TAIL" not in redacted_dump
    assert "sk-nestedsecret" not in redacted_dump
    assert "alice@example.com" not in redacted_dump
    assert "redacted" in redacted_dump


def test_default_api_responses_do_not_expose_full_private_text():
    client = make_client()
    resume, _version_id = _create_resume(client)
    job = _create_job(client)
    document = _create_rag_document(client)

    responses = [
        client.get("/api/resumes"),
        client.get(f"/api/resumes/{resume['resume_id']}"),
        client.get("/api/jobs"),
        client.get(f"/api/jobs/{job['jd_id']}"),
        client.get("/api/rag/documents"),
        client.get(f"/api/rag/documents/{document['doc_id']}"),
        client.get(f"/api/rag/chunks?doc_id={document['doc_id']}"),
    ]
    for response in responses:
        assert response.status_code == 200
        body = response.text
        assert '"raw_text":' not in body
        assert "RESUME_PRIVATE_UNIQUE_TAIL" not in body
        assert "JD_PRIVATE_UNIQUE_TAIL" not in body
        assert "RAG_PRIVATE_UNIQUE_TAIL" not in body


def test_delete_resume_soft_deletes_and_keeps_linked_application_safe():
    client = make_client()
    resume, resume_version_id = _create_resume(client)
    job = _create_job(client)
    application = _create_application(
        client,
        jd_id=job["jd_id"],
        resume_version_id=resume_version_id,
    )

    response = client.delete(f"/api/resumes/{resume['resume_id']}")
    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "deleted"
    assert data["archived_version_count"] == 1

    listed = get_data(client.get("/api/resumes"))
    assert listed["items"] == []
    detail_response = client.get(f"/api/resumes/{resume['resume_id']}")
    assert detail_response.status_code == 404
    assert get_error(detail_response)["code"] == "resume_not_found"
    versions_response = client.get(f"/api/resumes/{resume['resume_id']}/versions")
    assert versions_response.status_code == 404

    application_detail = client.get(f"/api/applications/{application['application_id']}")
    assert application_detail.status_code == 200
    assert get_data(application_detail)["resume_version_id"] == resume_version_id


def test_delete_job_archives_and_hides_from_default_list():
    client = make_client()
    job = _create_job(client)

    response = client.delete(f"/api/jobs/{job['jd_id']}")
    assert response.status_code == 200
    assert get_data(response)["status"] == "archived"

    listed = get_data(client.get("/api/jobs"))
    assert listed["items"] == []
    detail_response = client.get(f"/api/jobs/{job['jd_id']}")
    assert detail_response.status_code == 404
    assert get_error(detail_response)["code"] == "job_not_found"


def test_delete_application_archives_and_excludes_default_list():
    client = make_client()
    _resume, resume_version_id = _create_resume(client)
    job = _create_job(client)
    application = _create_application(
        client,
        jd_id=job["jd_id"],
        resume_version_id=resume_version_id,
    )

    response = client.delete(f"/api/applications/{application['application_id']}")
    assert response.status_code == 200
    archived = get_data(response)
    assert archived["status"] == "archived"
    assert archived["status_history"][-1]["to_status"] == "archived"

    default_list = get_data(client.get("/api/applications"))
    assert default_list["items"] == []
    archived_list = get_data(client.get("/api/applications?status=archived"))
    assert [item["application_id"] for item in archived_list["items"]] == [
        application["application_id"]
    ]
    stats = get_data(client.get("/api/applications/stats"))
    assert stats["total_applications"] == 0


def test_delete_rag_document_removes_document_and_chunks():
    client = make_client()
    document = _create_rag_document(client)

    response = client.delete(f"/api/rag/documents/{document['doc_id']}")
    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "deleted"
    assert data["deleted_chunk_count"] > 0

    listed = get_data(client.get("/api/rag/documents"))
    assert listed["items"] == []
    detail_response = client.get(f"/api/rag/documents/{document['doc_id']}")
    assert detail_response.status_code == 404
    chunks = get_data(client.get("/api/rag/chunks"))
    assert chunks["items"] == []


def test_delete_missing_records_return_clear_errors():
    client = make_client()

    checks = [
        (client.delete("/api/resumes/missing_resume"), "resume_not_found"),
        (client.delete("/api/jobs/missing_jd"), "job_not_found"),
        (client.delete("/api/applications/missing_application"), "application_not_found"),
        (client.delete("/api/rag/documents/missing_doc"), "rag_document_not_found"),
    ]
    for response, code in checks:
        assert response.status_code == 404
        assert get_error(response)["code"] == code


def test_version_metadata_is_exposed_without_secrets():
    client = make_client()
    document = _create_rag_document(client)

    search = get_data(
        client.post(
            "/api/rag/search",
            json={"query": "FastAPI interview", "top_k": 3},
        )
    )
    debug = search["retrieval_debug"]
    assert debug["retrieval_version"] == RETRIEVAL_VERSION
    assert debug["schema_version"] == SCHEMA_VERSION
    assert debug["model_version"] == MODEL_VERSION

    answer = get_data(
        client.post(
            "/api/rag/answer",
            json={"question": "How should I prepare for FastAPI?", "top_k": 3},
        )
    )
    answer_run = get_data(client.get(f"/api/rag/answers/{answer['answer_run_id']}"))
    assert answer_run["retrieval_debug"]["retrieval_version"] == RETRIEVAL_VERSION

    eval_run = get_data(
        client.post("/api/evaluations/runs", json={"module": "rag"})
    )["run"]
    run_config = eval_run["run_config"]
    assert run_config["prompt_version"] == PROMPT_VERSION
    assert run_config["schema_version"] == SCHEMA_VERSION
    assert run_config["retrieval_version"] == RETRIEVAL_VERSION
    assert run_config["model_version"] == MODEL_VERSION
    assert run_config["evaluation_version"] == EVALUATION_VERSION
    assert "OPENAI_API_KEY" not in json.dumps(run_config)
    assert "sk-" not in json.dumps(run_config)

    assert document["doc_id"] in [source["doc_id"] for source in search["sources"]]
