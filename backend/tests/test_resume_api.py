from conftest import get_data, get_error, make_client
from app.models.resume import Resume, ResumeVersion


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
    assert data["extraction_status"] == "parser_placeholder"
    assert data["extraction_method"] == "pdf_parser_placeholder"
    assert data["extraction_warnings"]
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


def test_resume_upload_extracts_real_markdown_text_and_mock_skills():
    client = make_client()
    content = "# Resume\nBuilt Python FastAPI and React tools."

    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "candidate.md",
                content.encode("utf-8"),
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["raw_text"] == content
    assert data["raw_text_preview"] == content
    assert data["extraction_status"] == "extracted"
    assert data["extraction_method"] == "utf8_md_decode"
    assert data["extraction_warnings"] == []
    skills = data["structured_resume"]["skills"]
    assert "Python" in skills["programming"]
    assert "FastAPI" in skills["backend"]
    assert "React" in skills["frontend"]


def test_resume_upload_extracts_real_txt_text():
    client = make_client()
    content = "Python engineer with SQL and Docker experience."

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("candidate.txt", content.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["file_type"] == "text"
    assert data["raw_text"] == content
    assert data["extraction_status"] == "extracted"
    assert data["extraction_method"] == "utf8_txt_decode"
    assert data["extraction_warnings"] == []
    assert "SQL" in data["structured_resume"]["skills"]["database"]
    assert "Docker" in data["structured_resume"]["skills"]["tools"]


def test_resume_upload_rejects_non_utf8_text():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("candidate.txt", b"\xff\xfe\xfa", "text/plain")},
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "resume_text_decode_failed"


def test_resume_upload_returns_pdf_placeholder_extraction():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("candidate.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["raw_text"].startswith("PDF raw text extraction placeholder.")
    assert data["extraction_status"] == "parser_placeholder"
    assert data["extraction_method"] == "pdf_parser_placeholder"
    assert data["extraction_warnings"] == ["PDF parser is not connected in Phase 1C."]


def test_resume_upload_returns_docx_placeholder_extraction():
    client = make_client()

    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "candidate.docx",
                b"mock docx bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["raw_text"].startswith("DOCX raw text extraction placeholder.")
    assert data["extraction_status"] == "parser_placeholder"
    assert data["extraction_method"] == "docx_parser_placeholder"
    assert data["extraction_warnings"] == ["DOCX parser is not connected in Phase 1C."]


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


def test_resume_upload_persists_resume_and_initial_version(db_session):
    client = make_client()
    upload = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "candidate.md",
                b"Python FastAPI persistent resume.",
                "text/markdown",
            )
        },
    )
    resume_id = get_data(upload)["resume_id"]

    resume = db_session.get(Resume, resume_id)
    versions = (
        db_session.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .all()
    )

    assert resume is not None
    assert resume.original_filename == "candidate.md"
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert "Python FastAPI" in versions[0].raw_text
