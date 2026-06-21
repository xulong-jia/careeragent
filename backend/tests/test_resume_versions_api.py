from conftest import get_data, get_error, make_client


def upload_markdown_resume(client, content: str = "Python FastAPI resume"):
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("candidate.md", content.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 201
    return get_data(response)


def test_resume_upload_creates_initial_version_and_lists_versions():
    client = make_client()
    resume = upload_markdown_resume(client)

    response = client.get(f"/api/resumes/{resume['resume_id']}/versions")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total"] == 1
    version = data["items"][0]
    assert version["resume_id"] == resume["resume_id"]
    assert version["resume_version_id"].endswith("version_0001")
    assert version["version_name"] == "Initial version"
    assert version["version_number"] == 1
    assert version["status"] == "active"
    assert version["is_archived"] is False


def test_resume_version_detail_returns_initial_version():
    client = make_client()
    resume = upload_markdown_resume(client, "Python and React")
    versions = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))
    version_id = versions["items"][0]["resume_version_id"]

    response = client.get(f"/api/resume-versions/{version_id}")

    assert response.status_code == 200
    data = get_data(response)
    assert data["resume_version_id"] == version_id
    assert data["raw_text"] == "Python and React"
    assert data["structured_resume"]["skills"]["programming"] == ["Python"]


def test_clone_resume_version_creates_new_version_without_overwriting_source():
    client = make_client()
    resume = upload_markdown_resume(client, "Python FastAPI original")
    initial = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))[
        "items"
    ][0]

    response = client.post(
        f"/api/resume-versions/{initial['resume_version_id']}/clone",
        json={"version_name": "Backend target", "target_role": "Backend Engineer"},
    )

    assert response.status_code == 201
    cloned = get_data(response)
    assert cloned["resume_version_id"] != initial["resume_version_id"]
    assert cloned["version_name"] == "Backend target"
    assert cloned["target_role"] == "Backend Engineer"
    assert cloned["version_number"] == 2
    assert cloned["raw_text"] == initial["raw_text"]
    assert cloned["structured_resume"] == initial["structured_resume"]
    assert cloned["extraction_status"] == initial["extraction_status"]
    assert cloned["risk_flags"] == initial["risk_flags"]

    versions = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))
    assert versions["total"] == 2
    source_after_clone = client.get(
        f"/api/resume-versions/{initial['resume_version_id']}"
    )
    assert get_data(source_after_clone)["version_number"] == 1


def test_clone_resume_version_generates_default_name():
    client = make_client()
    resume = upload_markdown_resume(client)
    initial = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))[
        "items"
    ][0]

    response = client.post(f"/api/resume-versions/{initial['resume_version_id']}/clone")

    assert response.status_code == 201
    cloned = get_data(response)
    assert cloned["version_name"] == "Copy of Initial version"
    assert cloned["version_number"] == 2


def test_archive_resume_version_soft_archives_and_keeps_detail_available():
    client = make_client()
    resume = upload_markdown_resume(client)
    version = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))[
        "items"
    ][0]

    response = client.patch(f"/api/resume-versions/{version['resume_version_id']}/archive")

    assert response.status_code == 200
    archived = get_data(response)
    assert archived["status"] == "archived"
    assert archived["is_archived"] is True
    assert archived["archived_at"] is not None

    detail = client.get(f"/api/resume-versions/{version['resume_version_id']}")
    assert detail.status_code == 200
    assert get_data(detail)["status"] == "archived"

    versions = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))
    assert versions["total"] == 1
    assert versions["items"][0]["is_archived"] is True


def test_resume_versions_for_missing_resume_returns_unified_error():
    client = make_client()

    response = client.get("/api/resumes/missing_resume/versions")

    assert response.status_code == 404
    assert get_error(response)["code"] == "resume_not_found"


def test_missing_resume_version_operations_return_unified_error():
    client = make_client()

    detail = client.get("/api/resume-versions/missing_version")
    clone = client.post("/api/resume-versions/missing_version/clone")
    archive = client.patch("/api/resume-versions/missing_version/archive")

    assert detail.status_code == 404
    assert clone.status_code == 404
    assert archive.status_code == 404
    assert get_error(detail)["code"] == "resume_version_not_found"
    assert get_error(clone)["code"] == "resume_version_not_found"
    assert get_error(archive)["code"] == "resume_version_not_found"
