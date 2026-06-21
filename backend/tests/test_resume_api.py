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
