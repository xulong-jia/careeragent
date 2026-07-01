from datetime import timedelta

from conftest import get_data, get_error, make_client
from app.agents import state
from app.core.security import create_access_token, hash_password
from app.core.tenant import DEFAULT_WORKSPACE_ID
from app.models.auth import User, Workspace, WorkspaceMembership


def _client_for(user_id: str, email: str):
    return make_client(
        user_id=user_id,
        email=email,
        workspace_id=f"workspace_{user_id}",
    )


def _create_resume_version(client) -> tuple[str, str]:
    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "resume.md",
                b"Python FastAPI React project experience.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions.status_code == 200
    version_id = get_data(versions)["items"][0]["resume_version_id"]
    return resume_id, version_id


def _create_job(client) -> str:
    response = client.post(
        "/api/jobs",
        json={
            "company": "Tenant Company",
            "job_title": "Backend Engineer",
            "location": "Sydney",
            "raw_text": "Build Python FastAPI APIs with SQL and Docker support.",
            "source_url": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)["jd_id"]


def _create_match(client) -> tuple[str, str, str]:
    _, version_id = _create_resume_version(client)
    jd_id = _create_job(client)
    response = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": jd_id},
    )
    assert response.status_code == 201
    return jd_id, version_id, get_data(response)["match_report_id"]


def _create_application(client) -> str:
    jd_id, version_id, match_id = _create_match(client)
    response = client.post(
        "/api/applications",
        json={
            "company": "Tenant Company",
            "role_title": "Backend Engineer",
            "jd_id": jd_id,
            "resume_version_id": version_id,
            "match_report_id": match_id,
            "status": "saved",
            "priority": "medium",
        },
    )
    assert response.status_code == 201
    return get_data(response)["application_id"]


def test_auth_register_login_me_and_invalid_tokens(db_session):
    client = make_client(authenticated=False)

    register = client.post(
        "/api/auth/register",
        json={
            "email": "new-user@example.com",
            "password": "Password123!",
            "display_name": "New User",
        },
    )
    assert register.status_code == 201
    registered = get_data(register)
    assert registered["access_token"]
    assert registered["user"]["email"] == "new-user@example.com"
    assert registered["workspace"]["role"] == "owner"

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "new-user@example.com", "password": "Password123!"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/auth/login",
        json={"email": "new-user@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    token = get_data(login)["access_token"]

    wrong_password = client.post(
        "/api/auth/login",
        json={"email": "new-user@example.com", "password": "wrong"},
    )
    assert wrong_password.status_code == 401
    assert get_error(wrong_password)["code"] == "invalid_credentials"

    me_without_token = client.get("/api/auth/me")
    assert me_without_token.status_code == 401

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert get_data(me)["user"]["email"] == "new-user@example.com"

    invalid = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert invalid.status_code == 401

    expired_token, _ = create_access_token(
        subject=registered["user"]["id"],
        email="new-user@example.com",
        role="user",
        workspace_id=registered["workspace"]["id"],
        expires_delta=timedelta(seconds=-1),
    )
    expired = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired.status_code == 401

    inactive = User(
        id="inactive_user",
        email="inactive@example.com",
        password_hash=hash_password("Password123!"),
        display_name="Inactive",
        role="user",
        is_active=False,
    )
    db_session.add(inactive)
    db_session.add(
        Workspace(
            id="inactive_workspace",
            owner_user_id="inactive_user",
            name="Inactive Workspace",
        )
    )
    db_session.add(
        WorkspaceMembership(
            workspace_id="inactive_workspace",
            user_id="inactive_user",
            role="owner",
        )
    )
    db_session.commit()
    inactive_login = client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert inactive_login.status_code == 401


def test_core_business_routes_require_authentication():
    client = make_client(authenticated=False)
    endpoints = [
        ("GET", "/api/profiles"),
        ("GET", "/api/resumes"),
        ("GET", "/api/jobs"),
        ("GET", "/api/matches"),
        ("GET", "/api/applications"),
        ("GET", "/api/rag/documents"),
        ("GET", "/api/agents/runs"),
        ("GET", "/api/bad-cases"),
        ("GET", "/api/evaluations/runs"),
        ("GET", "/api/privacy/audit-log"),
    ]

    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code == 401, path
        assert get_error(response)["code"] == "not_authenticated"


def test_tenant_isolation_for_core_records_and_rag_search():
    user_a = _client_for("user_a", "a@example.com")
    user_b = _client_for("user_b", "b@example.com")

    resume_id, _ = _create_resume_version(user_a)
    assert get_data(user_b.get("/api/resumes"))["total"] == 0

    jd_id = _create_job(user_a)
    assert user_b.get(f"/api/jobs/{jd_id}").status_code == 404

    _, _, match_id = _create_match(user_a)
    assert user_b.get(f"/api/matches/{match_id}").status_code == 404

    application_id = _create_application(user_a)
    blocked_update = user_b.patch(
        f"/api/applications/{application_id}",
        json={"status": "applied"},
    )
    assert blocked_update.status_code == 404
    assert user_b.delete(f"/api/applications/{application_id}").status_code == 404

    doc_response = user_a.post(
        "/api/rag/documents",
        json={
            "title": "Private RAG",
            "source_type": "manual",
            "raw_text": "private tenant keyword python fastapi",
            "metadata": {},
        },
    )
    doc_id = get_data(doc_response)["doc_id"]
    assert user_a.post(
        f"/api/rag/documents/{doc_id}/index",
        json={"max_chars": 200, "overlap_chars": 0},
    ).status_code == 200
    search = user_b.post(
        "/api/rag/search",
        json={"query": "private tenant keyword", "top_k": 5},
    )
    assert search.status_code == 200
    assert get_data(search)["sources"] == []

    agent_run = user_a.post(
        "/api/agents/runs",
        json={"workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION},
    )
    run_id = get_data(agent_run)["run"]["id"]
    assert user_b.get(f"/api/agents/runs/{run_id}/steps").status_code == 404

    bad_case = user_a.post(
        "/api/bad-cases",
        json={
            "source_type": "match_report",
            "source_id": match_id,
            "category": "match_score_inaccurate",
            "severity": "medium",
            "title": "Tenant bad case",
            "description": "Tenant scoped issue.",
        },
    )
    assert bad_case.status_code == 201
    assert get_data(user_b.get("/api/bad-cases"))["total"] == 0

    assert user_a.get(f"/api/resumes/{resume_id}").status_code == 200


def test_privacy_export_delete_all_and_audit_are_tenant_scoped():
    user_a = _client_for("privacy_a", "privacy-a@example.com")
    user_b = _client_for("privacy_b", "privacy-b@example.com")
    _create_resume_version(user_a)
    a_job_id = _create_job(user_a)
    b_job_id = _create_job(user_b)

    export = user_a.get("/api/privacy/export")
    assert export.status_code == 200
    exported = get_data(export)
    assert {item["id"] for item in exported["jobs"]} == {a_job_id}

    summary = user_a.get("/api/privacy/delete-summary")
    assert summary.status_code == 200
    summary_data = get_data(summary)
    assert summary_data["resources"]["job_descriptions"] == 1
    assert summary_data["total_records"] >= 1

    deleted = user_a.delete("/api/privacy/delete-all")
    assert deleted.status_code == 200
    deleted_data = get_data(deleted)
    assert deleted_data["deleted_counts"]["job_descriptions"] == 1
    assert deleted_data["deletion_proof_id"].startswith("deletion_")
    assert "backup" in deleted_data["retention_note"].lower()
    assert get_data(user_a.get("/api/jobs"))["total"] == 0
    assert user_a.get(f"/api/jobs/{a_job_id}").status_code == 404
    assert user_b.get(f"/api/jobs/{b_job_id}").status_code == 200

    audit = user_a.get("/api/privacy/audit-log")
    assert audit.status_code == 200
    audit_items = get_data(audit)["items"]
    assert audit_items
    assert audit_items[0]["action"] == "privacy.delete_all"
    audit_text = str(audit_items).lower()
    assert "raw_text" not in audit_text
    assert "secret" not in audit_text
    assert DEFAULT_WORKSPACE_ID not in audit_text
