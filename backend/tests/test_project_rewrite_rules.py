from conftest import get_data, make_client


def _create_project(client, **overrides):
    payload = {
        "name": "Backend Search Platform",
        "role": "Backend Engineer",
        "period": "2026-01 to 2026-04",
        "background": "Local learning project for search workflow experiments.",
        "tech_stack": ["Python", "FastAPI"],
        "responsibilities": [
            "Built FastAPI APIs for indexing documents.",
            "Designed Python services for deterministic search workflow.",
        ],
        "results": [
            "Reduced API latency by 30% in synthetic local tests.",
            "Prepared deployment checklist but did not run production launch.",
        ],
        "evidence": [],
        "status": "active",
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return get_data(response)


def _create_job(client):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Synthetic Platform Co",
            "job_title": "Backend Platform Engineer",
            "location": "Shanghai",
            "raw_text": (
                "Required Python FastAPI SQL backend API design. "
                "Preferred Docker React for platform tooling."
            ),
            "source_url": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _run_rewrite(client, project_id: str, jd_id: str):
    response = client.post(
        f"/api/projects/{project_id}/rewrite",
        json={"jd_id": jd_id},
    )
    assert response.status_code == 201
    return get_data(response)


def test_rewrite_rules_match_required_skills_and_missing_required_skills():
    client = make_client()
    project = _create_project(client)
    job = _create_job(client)

    rewrite = _run_rewrite(client, project["id"], job["jd_id"])

    matched_skills = {point["skill"] for point in rewrite["matched_points"]}
    assert {"Python", "FastAPI"}.issubset(matched_skills)
    assert any(
        point["skill"] == "FastAPI"
        and point["source_field"] in {"tech_stack", "responsibilities"}
        and point["match_type"] == "required_skill"
        for point in rewrite["matched_points"]
    )
    assert any(
        point["requirement"] == "SQL"
        and point["requirement_type"] == "required_skill"
        and point["priority"] == "high"
        for point in rewrite["missing_points"]
    )


def test_rewrite_rules_generate_evidence_required_and_risk_flags_for_metrics():
    client = make_client()
    project = _create_project(client)
    job = _create_job(client)

    rewrite = _run_rewrite(client, project["id"], job["jd_id"])

    assert any(
        item["type"] == "unsupported_metric" and "30%" in item["project_text"]
        for item in rewrite["evidence_required"]
    )
    risk_types = {flag["type"] for flag in rewrite["risk_flags"]}
    assert {"unsupported_metric", "missing_evidence", "overclaim"}.issubset(
        risk_types
    )
    assert any(
        bullet["risk_level"] in {"medium", "high"}
        and "evidence" in bullet["evidence_required"].lower()
        and bullet["forbidden_changes"]
        and isinstance(bullet["confidence"], float)
        for bullet in rewrite["rewritten_bullets"]
    )


def test_rewritten_bullets_do_not_fabricate_absent_metrics_or_skills():
    client = make_client()
    project = _create_project(
        client,
        tech_stack=["Python"],
        responsibilities=["Built Python batch scripts for document cleanup."],
        results=["Created repeatable local smoke tests."],
        evidence=[{"type": "test", "description": "Synthetic tests"}],
    )
    job = _create_job(client)

    rewrite = _run_rewrite(client, project["id"], job["jd_id"])

    rewritten_text = " ".join(
        bullet["after"] for bullet in rewrite["rewritten_bullets"]
    )
    assert "30%" not in rewritten_text
    assert "SQL" not in rewritten_text
    assert "million" not in rewritten_text.lower()
    assert any(
        flag["type"] == "fabricated_skill" and "FastAPI" in flag["message"]
        for flag in rewrite["risk_flags"]
    )


def test_rewrite_rules_flag_learning_to_business_overclaim():
    client = make_client()
    project = _create_project(
        client,
        background="Local learning project for backend architecture practice.",
        results=["Launched a commercial production platform for million users."],
        evidence=[],
    )
    job = _create_job(client)

    rewrite = _run_rewrite(client, project["id"], job["jd_id"])

    assert any(
        item["type"] == "timeline_or_scope_evidence"
        for item in rewrite["evidence_required"]
    )
    assert any(
        flag["type"] == "learning_to_business_overclaim"
        and flag["severity"] == "high"
        for flag in rewrite["risk_flags"]
    )


def test_forbidden_changes_include_project_fabrication_boundaries():
    client = make_client()
    project = _create_project(client)
    job = _create_job(client)

    rewrite = _run_rewrite(client, project["id"], job["jd_id"])

    assert {
        "company",
        "user_count",
        "revenue",
        "accuracy",
        "production_status",
        "business_scale",
        "tech_stack_not_in_facts",
        "unsupported_metric",
    }.issubset(set(rewrite["forbidden_changes"]))


def test_rewrite_rules_generate_conservative_bullet_when_original_bullet_empty():
    client = make_client()
    project = _create_project(
        client,
        background=None,
        tech_stack=["Python", "RAG"],
        responsibilities=[],
        results=[],
        evidence=[{"type": "notes", "description": "RAG experiment notes"}],
    )
    job = _create_job(client)

    rewrite = _run_rewrite(client, project["id"], job["jd_id"])

    assert rewrite["rewritten_bullets"]
    bullet = rewrite["rewritten_bullets"][0]
    assert bullet["before"] == ""
    assert bullet["after"]
    assert bullet["risk_level"] in {"medium", "high"}
    assert bullet["evidence_required"]
    assert bullet["forbidden_changes"]
