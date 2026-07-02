#!/usr/bin/env python3
"""Verify restored backup data for a deleted subject without exposing raw data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Connection


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "evidence/private_outputs/backup_purge_restore_after_delete_20260702.json"
DEFAULT_SUBJECT_EMAIL = "test@example.com"
RETAINED_TABLES = {"users", "workspace_memberships", "audit_logs", "auth_sessions", "revoked_tokens"}
DIRECT_OWNER_TABLES = [
    "profiles",
    "resumes",
    "job_descriptions",
    "match_reports",
    "projects",
    "project_rewrites",
    "interview_questions",
    "interview_answers",
    "study_plans",
    "applications",
    "rag_documents",
    "rag_answer_runs",
    "agent_runs",
    "bad_cases",
    "evaluation_runs",
    "evaluation_cases",
    "evaluation_results",
]
DEPENDENT_COUNT_QUERIES = {
    "resume_versions": "SELECT count(*) FROM resume_versions WHERE resume_id IN (SELECT id FROM resumes WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "job_profiles": "SELECT count(*) FROM job_profiles WHERE jd_id IN (SELECT id FROM job_descriptions WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "application_status_history": "SELECT count(*) FROM application_status_history WHERE application_id IN (SELECT id FROM applications WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "rag_chunks": "SELECT count(*) FROM rag_chunks WHERE document_id IN (SELECT id FROM rag_documents WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "agent_steps": "SELECT count(*) FROM agent_steps WHERE run_id IN (SELECT id FROM agent_runs WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
}
DELETE_STATEMENTS = [
    "DELETE FROM application_status_history WHERE application_id IN (SELECT id FROM applications WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM applications WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM agent_steps WHERE run_id IN (SELECT id FROM agent_runs WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM agent_runs WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM interview_answers WHERE question_id IN (SELECT id FROM interview_questions WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM interview_answers WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM interview_questions WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM study_plans WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM project_rewrites WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM projects WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM evaluation_results WHERE run_id IN (SELECT id FROM evaluation_runs WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM evaluation_results WHERE case_id IN (SELECT id FROM evaluation_cases WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM evaluation_results WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM evaluation_cases WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM evaluation_runs WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM bad_cases WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM rag_chunks WHERE document_id IN (SELECT id FROM rag_documents WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM rag_documents WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM rag_answer_runs WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM match_reports WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM job_profiles WHERE jd_id IN (SELECT id FROM job_descriptions WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM job_descriptions WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM profiles WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
    "DELETE FROM resume_versions WHERE resume_id IN (SELECT id FROM resumes WHERE user_id = :user_id OR workspace_id IN :workspace_ids)",
    "DELETE FROM resumes WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
]


class RestoreVerifierError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubjectScope:
    user_id: str | None
    workspace_ids: list[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _restore_url_from_env(env: dict[str, str]) -> str:
    restore_url = env.get("RESTORE_DATABASE_URL", "").strip()
    if not restore_url:
        raise RestoreVerifierError("RESTORE_DATABASE_URL is required in the local shell.")
    if restore_url.startswith("sqlite"):
        raise RestoreVerifierError("RESTORE_DATABASE_URL must point to the isolated PostgreSQL restore DB.")
    for key in ("DATABASE_URL", "PRODUCTION_DATABASE_URL"):
        production_url = env.get(key, "").strip()
        if production_url and production_url == restore_url:
            raise RestoreVerifierError(f"RESTORE_DATABASE_URL must not equal {key}.")
    return restore_url


def _validate_apply_safety(args: argparse.Namespace) -> None:
    if not args.apply_redaction:
        return
    label = (args.confirm_isolated_restore_db or "").strip().lower()
    if "restore" not in label or "test" not in label:
        raise RestoreVerifierError(
            "--apply-redaction requires --confirm-isolated-restore-db with a restore/test label."
        )


def _redacted_database_ref(database_url: str, confirmation_label: str | None) -> dict[str, str]:
    parsed = urlparse(database_url)
    host_hash = _hash_value(parsed.hostname or "unknown-host")
    db_name = parsed.path.lstrip("/") or "unknown-db"
    return {
        "driver": parsed.scheme.split("+")[0],
        "host_hash_sha256": host_hash,
        "database_name_hash_sha256": _hash_value(db_name),
        "operator_confirmed_restore_label_hash_sha256": _hash_value(confirmation_label or ""),
    }


def _execute_count(conn: Connection, sql: str, params: dict[str, Any]) -> int:
    statement = text(sql).bindparams(bindparam("workspace_ids", expanding=True))
    return int(conn.execute(statement, params).scalar_one() or 0)


def _table_exists(conn: Connection, table_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table_name)"
            ),
            {"table_name": table_name},
        ).scalar_one()
    )


def _subject_scope(conn: Connection, subject_email: str) -> SubjectScope:
    row = conn.execute(
        text("SELECT id FROM users WHERE lower(email) = lower(:email)"),
        {"email": subject_email},
    ).first()
    if row is None:
        return SubjectScope(user_id=None, workspace_ids=[])
    user_id = str(row[0])
    workspace_ids = [
        str(item[0])
        for item in conn.execute(
            text("SELECT workspace_id FROM workspace_memberships WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).all()
    ]
    return SubjectScope(user_id=user_id, workspace_ids=workspace_ids)


def _count_restored_subject_data(conn: Connection, scope: SubjectScope) -> dict[str, int]:
    if not scope.user_id:
        return {"users": 0, "workspace_memberships": 0}
    params = {"user_id": scope.user_id, "workspace_ids": scope.workspace_ids or ["__none__"]}
    counts: dict[str, int] = {
        "users": _execute_count(conn, "SELECT count(*) FROM users WHERE id = :user_id", params),
        "workspace_memberships": _execute_count(
            conn,
            "SELECT count(*) FROM workspace_memberships WHERE user_id = :user_id AND workspace_id IN :workspace_ids",
            params,
        ),
    }
    for table_name in DIRECT_OWNER_TABLES:
        if _table_exists(conn, table_name):
            counts[table_name] = _execute_count(
                conn,
                f"SELECT count(*) FROM {table_name} WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
                params,
            )
    for table_name, sql in DEPENDENT_COUNT_QUERIES.items():
        if _table_exists(conn, table_name):
            counts[table_name] = _execute_count(conn, sql, params)
    return dict(sorted(counts.items()))


def _business_row_count(counts: dict[str, int]) -> int:
    return sum(value for key, value in counts.items() if key not in RETAINED_TABLES)


def _apply_restore_redaction(conn: Connection, scope: SubjectScope) -> int:
    if not scope.user_id:
        return 0
    params = {"user_id": scope.user_id, "workspace_ids": scope.workspace_ids or ["__none__"]}
    deleted_rows = 0
    for sql in DELETE_STATEMENTS:
        statement = text(sql).bindparams(bindparam("workspace_ids", expanding=True))
        result = conn.execute(statement, params)
        deleted_rows += int(result.rowcount or 0)
    return deleted_rows


def build_restore_after_delete_payload(
    *,
    subject_email: str,
    restore_url: str,
    confirmation_label: str | None,
    mode: str,
    pre_counts: dict[str, int],
    post_counts: dict[str, int],
    deleted_rows: int,
) -> dict[str, Any]:
    pre_business_rows = _business_row_count(pre_counts)
    post_business_rows = _business_row_count(post_counts)
    return {
        "artifact_type": "backup_purge_restore_after_delete",
        "created_at": _utc_now(),
        "restore_database": _redacted_database_ref(restore_url, confirmation_label),
        "test_subject_hash_sha256": _hash_value(subject_email),
        "mode": mode,
        "subject_found_in_restore": pre_counts.get("users", 0) > 0,
        "pre_redaction_counts": pre_counts,
        "pre_redaction_business_record_count": pre_business_rows,
        "redaction_applied": mode == "apply_redaction",
        "redaction_deleted_rows": deleted_rows,
        "post_redaction_counts": post_counts,
        "post_redaction_business_record_count": post_business_rows,
        "restore_after_delete_blocked_or_redacted": mode == "apply_redaction" and post_business_rows == 0,
        "production_promotion_block": (
            "Restored database must not be promoted to production until deleted-subject "
            "business rows are re-deleted or redacted and post-redaction business count is zero."
        ),
        "raw_private_data_included": False,
        "database_url_included": False,
        "limitations": [
            "restore_db_verification_only",
            "auth account and workspace membership may remain by design",
            "legal_hold_behavior_requires_external_operations_evidence",
        ],
    }


def verify_restore_after_delete(args: argparse.Namespace, env: dict[str, str]) -> dict[str, Any]:
    restore_url = _restore_url_from_env(env)
    _validate_apply_safety(args)
    subject_email = env.get("RESTORE_DELETE_SUBJECT_EMAIL", DEFAULT_SUBJECT_EMAIL)
    engine = create_engine(restore_url)
    mode = "apply_redaction" if args.apply_redaction else "dry_run"
    with engine.begin() as conn:
        scope = _subject_scope(conn, subject_email)
        pre_counts = _count_restored_subject_data(conn, scope)
        deleted_rows = _apply_restore_redaction(conn, scope) if args.apply_redaction else 0
        post_counts = _count_restored_subject_data(conn, scope)
    return build_restore_after_delete_payload(
        subject_email=subject_email,
        restore_url=restore_url,
        confirmation_label=args.confirm_isolated_restore_db,
        mode=mode,
        pre_counts=pre_counts,
        post_counts=post_counts,
        deleted_rows=deleted_rows,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--apply-redaction",
        action="store_true",
        help="Run re-delete/redaction against RESTORE_DATABASE_URL. Default is read-only.",
    )
    parser.add_argument(
        "--confirm-isolated-restore-db",
        help="Required with --apply-redaction; use a label such as careeragent-postgres-restore-test-20260702.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        payload = verify_restore_after_delete(args, os.environ)
    except RestoreVerifierError as exc:
        print(f"error: {exc}", flush=True)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "mode": payload["mode"],
                "subject_found_in_restore": payload["subject_found_in_restore"],
                "pre_redaction_business_record_count": payload["pre_redaction_business_record_count"],
                "post_redaction_business_record_count": payload["post_redaction_business_record_count"],
                "restore_after_delete_blocked_or_redacted": payload["restore_after_delete_blocked_or_redacted"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
