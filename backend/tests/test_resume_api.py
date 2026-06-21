from conftest import get_data, get_error, make_client


def test_resume_upload_accepts_supported_file_and_returns_mock_result():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 mock content", "application/pdf")},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["resume_id"].startswith("resume_")
    assert data["filename"] == "resume.pdf"
    assert data["file_type"] == "pdf"
    assert data["parse_status"] == "mock_parsed"
    assert data["raw_text"]
    assert data["structured_resume"]["projects"] == []
    assert data["risk_flags"] == []


def test_resume_upload_rejects_unsupported_file_type():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.exe", b"not allowed", "application/octet-stream")},
    )

    assert response.status_code == 400
    error = get_error(response)
    assert error["code"] == "unsupported_resume_file_type"


def test_resume_upload_rejects_empty_file():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "resume_file_empty"


def test_resume_upload_rejects_file_that_is_too_large():
    client = make_client()
    too_large_content = b"x" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("large.pdf", too_large_content, "application/pdf")},
    )

    assert response.status_code == 413
    assert get_error(response)["code"] == "resume_file_too_large"


def test_resume_upload_rejects_mime_extension_mismatch():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", b"not really pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "resume_file_mime_mismatch"


def test_resume_upload_without_file_returns_validation_error():
    client = make_client()

    response = client.post("/api/resumes/upload")

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"


def test_resume_upload_extracts_mock_skills_from_markdown_text():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "candidate.md",
                b"# Resume\nBuilt Python FastAPI and React tools.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201
    skills = get_data(response)["structured_resume"]["skills"]
    assert "Python" in skills["programming"]
    assert "FastAPI" in skills["backend"]
    assert "React" in skills["frontend"]


def test_resume_list_and_detail_return_uploaded_resume():
    client = make_client()
    upload = client.post(
        "/api/resumes/upload",
        files={"file": ("candidate.md", b"# Mock Resume", "text/markdown")},
    )
    resume_id = get_data(upload)["resume_id"]

    list_response = client.get("/api/resumes")
    detail_response = client.get(f"/api/resumes/{resume_id}")

    assert list_response.status_code == 200
    assert any(item["resume_id"] == resume_id for item in get_data(list_response)["items"])
    assert detail_response.status_code == 200
    assert get_data(detail_response)["resume_id"] == resume_id
