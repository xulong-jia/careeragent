#!/usr/bin/env python3
"""Verify legal hold blocks privacy delete-all without exposing private data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_OUTPUT = REPO_ROOT / "evidence/private_outputs/backup_purge_legal_hold_20260702.json"

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AUTH_JWT_SECRET", "legal-hold-proof-local-auth-secret")
os.environ.setdefault(
    "DATA_ENCRYPTION_KEY",
    "MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew=",
)
os.environ.setdefault("DATA_ENCRYPTION_KEY_ID", "legal-hold-proof-test-v1")
sys.path.insert(0, str(BACKEND_ROOT))

import app.models as app_models  # noqa: E402,F401
from app.core.tenant import AuthContext, reset_auth_context, set_auth_context  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.auth import User, Workspace, WorkspaceMembership  # noqa: E402
from app.models.job import JobDescription  # noqa: E402
from app.services import privacy_service  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _job_count(db) -> int:
    return int(db.scalar(select(func.count()).select_from(JobDescription)) or 0)


def _summarize_response(response: dict[str, object]) -> dict[str, object]:
    return {
        "status": response.get("status"),
        "verification_status": response.get("verification_status"),
        "legal_hold_blocked": response.get("legal_hold_blocked"),
        "legal_hold_status": response.get("legal_hold_status"),
        "backup_purge_status": response.get("backup_purge_status"),
        "job_descriptions_deleted_count": (response.get("deleted_counts") or {}).get(
            "job_descriptions"
        ),
    }


def build_payload() -> dict[str, Any]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    token = set_auth_context(
        AuthContext(
            user_id="legal_hold_subject",
            workspace_id="legal_hold_workspace",
            email="legal-hold-subject@example.invalid",
            role="owner",
        )
    )
    try:
        with SessionLocal() as db:
            db.add(
                User(
                    id="legal_hold_subject",
                    email="legal-hold-subject@example.invalid",
                    password_hash="not-used-in-proof",
                    display_name="Legal Hold Subject",
                    role="user",
                    is_active=True,
                )
            )
            db.add(
                Workspace(
                    id="legal_hold_workspace",
                    owner_user_id="legal_hold_subject",
                    name="Legal Hold Workspace",
                )
            )
            db.add(
                WorkspaceMembership(
                    workspace_id="legal_hold_workspace",
                    user_id="legal_hold_subject",
                    role="owner",
                )
            )
            db.add(
                JobDescription(
                    id="legal_hold_job",
                    user_id="legal_hold_subject",
                    workspace_id="legal_hold_workspace",
                    company="Synthetic Proof Company",
                    job_title="Synthetic Proof Role",
                    raw_text="Synthetic legal hold proof row.",
                )
            )
            db.commit()

            pre_count = _job_count(db)
            hold_event = privacy_service.set_legal_hold_for_current_subject(
                db,
                active=True,
                reason="backup_purge_behavior_verification",
            )
            hold_event_id = hold_event.id
            db.commit()
            dry_run = privacy_service.delete_current_user_data(db, dry_run=True)
            after_dry_run_count = _job_count(db)
            execute = privacy_service.delete_current_user_data(db, dry_run=False)
            after_execute_count = _job_count(db)

    finally:
        reset_auth_context(token)

    dry_run_summary = _summarize_response(dry_run)
    execute_summary = _summarize_response(execute)
    behavior_verified = all(
        [
            pre_count == 1,
            after_dry_run_count == 1,
            after_execute_count == 1,
            dry_run_summary["verification_status"] == "legal_hold_blocked",
            execute_summary["verification_status"] == "legal_hold_blocked",
            dry_run_summary["job_descriptions_deleted_count"] == 0,
            execute_summary["job_descriptions_deleted_count"] == 0,
            execute_summary["backup_purge_status"] == "legal_hold",
        ]
    )
    return {
        "artifact_type": "backup_purge_legal_hold_behavior",
        "created_at": _utc_now(),
        "mechanism": "audit_log_policy_service",
        "scope": "current_user_workspace",
        "data_model_field_check": {
            "legal_hold_field_present": False,
            "retention_hold_field_present": False,
            "deletion_block_field_present": False,
            "policy_source": "audit_logs.metadata_json",
        },
        "legal_hold_source_audit_event_present": bool(hold_event_id),
        "pre_delete_job_description_count": pre_count,
        "after_dry_run_job_description_count": after_dry_run_count,
        "after_execute_job_description_count": after_execute_count,
        "dry_run": dry_run_summary,
        "execute": execute_summary,
        "legal_hold_behavior_verified": behavior_verified,
        "delete_all_did_not_mark_purge_complete": execute_summary["backup_purge_status"]
        == "legal_hold",
        "raw_private_data_included": False,
        "database_url_included": False,
        "limitations": [
            "local_isolated_runtime_verification",
            "legal hold policy source is audit log metadata, not a dedicated table column",
            "no legal hold management API was added",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_payload()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "legal_hold_behavior_verified": payload["legal_hold_behavior_verified"],
                "pre_delete_job_description_count": payload[
                    "pre_delete_job_description_count"
                ],
                "after_execute_job_description_count": payload[
                    "after_execute_job_description_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["legal_hold_behavior_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
