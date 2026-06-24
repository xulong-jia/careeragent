#!/usr/bin/env python3
"""Seed synthetic CareerAgent demo data through the public HTTP API."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = os.getenv("CAREERAGENT_API_BASE_URL", "http://localhost:8000").rstrip("/")


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{API_BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["data"]


def upload_resume(filename: str, content: str) -> Any:
    boundary = "careeragent-demo-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/markdown\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    request = Request(
        f"{API_BASE_URL}/api/resumes/upload",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["data"]


def main() -> None:
    try:
        health = request_json("GET", "/health")
        print(f"Backend health: {health['status']}")

        resume = upload_resume(
            "synthetic-demo-resume.md",
            "\n".join(
                [
                    "# Synthetic Demo Candidate",
                    "Python FastAPI React project experience.",
                    "Built deterministic RAG and evaluation workflow prototypes.",
                    "No real personal data is included in this demo resume.",
                ]
            ),
        )
        resume_id = resume["resume_id"]
        versions = request_json("GET", f"/api/resumes/{resume_id}/versions")
        resume_version_id = versions["items"][0]["resume_version_id"]

        job = request_json(
            "POST",
            "/api/jobs",
            {
                "company": "Synthetic Demo Labs",
                "job_title": "AI Application Engineer",
                "location": "Remote",
                "raw_text": (
                    "Build Python FastAPI services, React dashboards, deterministic "
                    "RAG workflows, evaluation tooling, and SQLite-backed prototypes."
                ),
                "source_url": None,
            },
        )
        jd_id = job["jd_id"]

        match = request_json(
            "POST",
            "/api/matches/run",
            {"resume_version_id": resume_version_id, "jd_id": jd_id},
        )
        match_report_id = match["match_report_id"]

        rag_doc = request_json(
            "POST",
            "/api/rag/documents",
            {
                "title": "Synthetic Interview Notes",
                "source_type": "interview",
                "source_uri": None,
                "raw_text": (
                    "FastAPI interviews often ask about API contracts, tests, "
                    "database migrations, and frontend integration evidence."
                ),
                "metadata": {"topic": "interview", "tags": ["demo", "synthetic"]},
            },
        )
        request_json(
            "POST",
            f"/api/rag/documents/{rag_doc['doc_id']}/index",
            {"max_chars": 320, "overlap_chars": 40},
        )

        agent = request_json(
            "POST",
            "/api/agents/runs",
            {
                "workflow_name": "job_application_preparation",
                "resume_version_id": resume_version_id,
                "jd_id": jd_id,
                "use_rag": True,
                "rag_query": "FastAPI interview preparation",
            },
        )

        application = request_json(
            "POST",
            "/api/applications",
            {
                "company": "Synthetic Demo Labs",
                "role_title": "AI Application Engineer",
                "role_category": "AI Application",
                "jd_id": jd_id,
                "resume_version_id": resume_version_id,
                "match_report_id": match_report_id,
                "status": "applied",
                "interview_notes": "Synthetic demo note only.",
                "reflection": "Synthetic demo reflection only.",
                "tags": ["demo", "synthetic"],
            },
        )

        bad_case = request_json(
            "POST",
            "/api/evaluations/bad-cases",
            {
                "source_type": "match_report",
                "source_id": match_report_id,
                "category": "match_score_inaccurate",
                "severity": "medium",
                "title": "Synthetic demo match review",
                "description": "Synthetic review record for demo regression tracking.",
                "expected_behavior": "Match report should show evidence and gaps.",
                "actual_behavior": "Synthetic demo actual behavior summary.",
                "suggested_fix": "Use deterministic evaluation smoke set.",
            },
        )
        evaluation_case = request_json(
            "POST",
            f"/api/evaluations/cases/from-bad-case/{bad_case['id']}",
        )
        evaluation = request_json(
            "POST",
            "/api/evaluations/runs",
            {"name": "Synthetic demo smoke run", "module": "all"},
        )

        print("Seeded synthetic demo data:")
        print(
            json.dumps(
                {
                    "resume_id": resume_id,
                    "resume_version_id": resume_version_id,
                    "jd_id": jd_id,
                    "match_report_id": match_report_id,
                    "rag_doc_id": rag_doc["doc_id"],
                    "agent_run_id": agent["run"]["id"],
                    "application_id": application["application_id"],
                    "bad_case_id": bad_case["id"],
                    "evaluation_case_id": evaluation_case["id"],
                    "evaluation_run_id": evaluation["run"]["id"],
                },
                indent=2,
            )
        )
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"API request failed: {exc.code} {message}") from exc
    except URLError as exc:
        raise SystemExit(
            f"Unable to reach {API_BASE_URL}. Start the backend before running this script."
        ) from exc


if __name__ == "__main__":
    main()
