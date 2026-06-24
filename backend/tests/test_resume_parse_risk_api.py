from conftest import get_data, get_error, make_client


def upload_markdown_resume(client, content: str = "Python FastAPI resume"):
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("candidate.md", content.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 201
    return get_data(response)


def first_version_id(client, resume_id: str) -> str:
    versions = get_data(client.get(f"/api/resumes/{resume_id}/versions"))
    return versions["items"][0]["resume_version_id"]


def clean_structured_resume() -> dict[str, object]:
    return {
        "basic_info": {
            "name": "Candidate",
            "email": "candidate@example.com",
            "phone": None,
            "location": None,
            "links": [],
        },
        "education": [],
        "projects": [
            {
                "name": "CareerAgent",
                "tech_stack": ["Python", "FastAPI"],
                "responsibilities": ["Built deterministic parser APIs"],
                "results": [],
                "evidence": ["pytest API coverage"],
                "start_date": "2023-01",
                "end_date": "2023-06",
            }
        ],
        "experience": [],
        "skills": {
            "programming": ["Python"],
            "backend": ["FastAPI"],
            "frontend": [],
            "ai": [],
            "database": [],
            "tools": [],
        },
        "certificates": [],
        "awards": [],
    }


def test_parse_existing_resume_success():
    client = make_client()
    resume = upload_markdown_resume(
        client,
        "\n".join(
            [
                "Candidate Name",
                "candidate@example.com",
                "Location: Sydney",
                "## Education",
                "University of Sydney | Master of IT | 2021 - 2023 | Courses: AI, Databases",
                "## Projects",
                "CareerAgent",
                "Role: Backend Engineer",
                "Period: 2023-01 - 2023-06",
                "Tech: Python, FastAPI, React",
                "Evidence: pytest coverage",
                "## Skills",
                "Python, FastAPI, React, SQL",
            ]
        ),
    )

    response = client.post(f"/api/resumes/{resume['resume_id']}/parse")

    assert response.status_code == 200
    data = get_data(response)
    structured = data["structured_resume"]
    assert data["resume_id"] == resume["resume_id"]
    assert data["source_version_id"].endswith("version_0001")
    assert data["extraction_method"] == "deterministic_resume_parser_v1"
    assert "raw_text_preview" in data
    assert structured["basic_info"]["email"] == "candidate@example.com"
    assert structured["education"]
    assert structured["projects"]
    assert "FastAPI" in structured["skills"]["backend"]


def test_parse_specific_version_success():
    client = make_client()
    resume = upload_markdown_resume(client, "Python FastAPI resume")
    version_id = first_version_id(client, resume["resume_id"])

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/parse",
        json={"resume_version_id": version_id},
    )

    assert response.status_code == 200
    assert get_data(response)["source_version_id"] == version_id


def test_parse_missing_resume_returns_404():
    client = make_client()

    response = client.post("/api/resumes/missing_resume/parse")

    assert response.status_code == 404
    assert get_error(response)["code"] == "resume_not_found"


def test_parse_version_not_belonging_to_resume_returns_error():
    client = make_client()
    first = upload_markdown_resume(client, "First resume")
    second = upload_markdown_resume(client, "Second resume")
    second_version_id = first_version_id(client, second["resume_id"])

    response = client.post(
        f"/api/resumes/{first['resume_id']}/parse",
        json={"resume_version_id": second_version_id},
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "resume_version_resume_mismatch"


def test_risk_check_clean_resume_returns_no_flags():
    client = make_client()
    resume = upload_markdown_resume(client)

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"structured_resume": clean_structured_resume()},
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["risk_flags"] == []
    assert data["risk_report"]["passed"] is True


def test_risk_check_detects_unsupported_metric_and_missing_evidence():
    client = make_client()
    resume = upload_markdown_resume(client)
    structured = clean_structured_resume()
    structured["projects"][0]["results"] = ["Improved API accuracy by 35%"]
    structured["projects"][0]["evidence"] = []

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"structured_resume": structured},
    )

    assert response.status_code == 200
    risk_types = {flag["type"] for flag in get_data(response)["risk_flags"]}
    assert "unsupported_metric" in risk_types
    assert "missing_evidence" in risk_types


def test_risk_check_detects_timeline_conflict():
    client = make_client()
    resume = upload_markdown_resume(client)
    structured = clean_structured_resume()
    structured["projects"][0]["start_date"] = "2024-01"
    structured["projects"][0]["end_date"] = "2023-12"

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"structured_resume": structured},
    )

    assert response.status_code == 200
    risk_types = {flag["type"] for flag in get_data(response)["risk_flags"]}
    assert "timeline_conflict" in risk_types


def test_risk_check_detects_overclaim():
    client = make_client()
    resume = upload_markdown_resume(client)
    structured = clean_structured_resume()
    structured["projects"][0]["results"] = [
        "Launched production platform for 1 million users"
    ]
    structured["projects"][0]["evidence"] = []

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"structured_resume": structured},
    )

    assert response.status_code == 200
    risk_types = {flag["type"] for flag in get_data(response)["risk_flags"]}
    assert "overclaim" in risk_types


def test_risk_check_detects_project_skill_not_declared():
    client = make_client()
    resume = upload_markdown_resume(client)
    structured = clean_structured_resume()
    structured["projects"][0]["tech_stack"] = ["Python", "Kubernetes"]

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"structured_resume": structured},
    )

    assert response.status_code == 200
    risk_types = {flag["type"] for flag in get_data(response)["risk_flags"]}
    assert "fabricated_skill" in risk_types


def test_risk_check_source_version_success():
    client = make_client()
    resume = upload_markdown_resume(
        client,
        "\n".join(
            [
                "Risky Candidate",
                "## Projects",
                "CareerAgent",
                "Tech: Python, FastAPI",
                "Results: Launched production platform for 1 million users",
            ]
        ),
    )
    version_id = first_version_id(client, resume["resume_id"])

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"resume_version_id": version_id},
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["source_version_id"] == version_id
    assert data["risk_flags"]


def test_risk_check_invalid_structured_resume_returns_validation_error():
    client = make_client()
    resume = upload_markdown_resume(client)

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/risk-check",
        json={"structured_resume": "not a structured resume"},
    )

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"


def test_save_confirmed_version_creates_incremented_version_with_risk_report():
    client = make_client()
    resume = upload_markdown_resume(client)
    source_version_id = first_version_id(client, resume["resume_id"])
    risk_report = {
        "passed": True,
        "summary": "No deterministic resume risks detected.",
        "flag_count": 0,
        "flags": [],
    }

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/versions",
        json={
            "version_name": "Backend confirmed",
            "target_role": "Backend Engineer",
            "structured_resume": clean_structured_resume(),
            "risk_report": risk_report,
            "source_version_id": source_version_id,
        },
    )

    assert response.status_code == 201
    created = get_data(response)
    assert created["version_number"] == 2
    assert created["version_name"] == "Backend confirmed"
    assert created["target_role"] == "Backend Engineer"
    assert created["status"] == "confirmed"
    assert created["risk_report"] == risk_report

    versions = get_data(client.get(f"/api/resumes/{resume['resume_id']}/versions"))
    assert versions["total"] == 2
    assert versions["items"][0]["version_number"] == 1


def test_save_confirmed_version_validates_source_version_belongs_to_resume():
    client = make_client()
    first = upload_markdown_resume(client, "First resume")
    second = upload_markdown_resume(client, "Second resume")
    second_version_id = first_version_id(client, second["resume_id"])

    response = client.post(
        f"/api/resumes/{first['resume_id']}/versions",
        json={
            "version_name": "Invalid source",
            "target_role": "Backend Engineer",
            "structured_resume": clean_structured_resume(),
            "source_version_id": second_version_id,
        },
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "resume_version_resume_mismatch"


def test_save_confirmed_version_invalid_payload_returns_validation_error():
    client = make_client()
    resume = upload_markdown_resume(client)

    response = client.post(
        f"/api/resumes/{resume['resume_id']}/versions",
        json={"version_name": "Missing structured resume"},
    )

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"
