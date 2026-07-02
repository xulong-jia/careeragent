import argparse

import pytest
from sqlalchemy import create_engine, text

from scripts import verify_restore_after_delete


def test_restore_verifier_requires_restore_database_url():
    with pytest.raises(verify_restore_after_delete.RestoreVerifierError):
        verify_restore_after_delete._restore_url_from_env({})


def test_restore_verifier_rejects_production_database_url_match():
    env = {
        "RESTORE_DATABASE_URL": "postgresql+psycopg://user:pass@restore.example/db",
        "DATABASE_URL": "postgresql+psycopg://user:pass@restore.example/db",
    }

    with pytest.raises(verify_restore_after_delete.RestoreVerifierError):
        verify_restore_after_delete._restore_url_from_env(env)


def test_restore_verifier_requires_isolated_confirmation_for_apply():
    args = argparse.Namespace(apply_redaction=True, confirm_isolated_restore_db="")

    with pytest.raises(verify_restore_after_delete.RestoreVerifierError):
        verify_restore_after_delete._validate_apply_safety(args)


def test_restore_verifier_allows_safe_apply_confirmation():
    args = argparse.Namespace(
        apply_redaction=True,
        confirm_isolated_restore_db="careeragent-postgres-restore-test-20260702",
    )

    verify_restore_after_delete._validate_apply_safety(args)


def test_execute_count_without_workspace_ids_does_not_bind_expanding_param():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY)"))
        conn.execute(text("INSERT INTO users (id) VALUES ('user-1')"))

        count = verify_restore_after_delete._execute_count(
            conn,
            "SELECT count(*) FROM users WHERE id = :user_id",
            {"user_id": "user-1", "workspace_ids": ["workspace-1"]},
        )

    assert count == 1


def test_execute_count_with_workspace_ids_uses_expanding_param():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE profiles (user_id TEXT, workspace_id TEXT)"))
        conn.execute(
            text(
                "INSERT INTO profiles (user_id, workspace_id) "
                "VALUES ('other-user', 'workspace-1')"
            )
        )

        count = verify_restore_after_delete._execute_count(
            conn,
            "SELECT count(*) FROM profiles "
            "WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
            {"user_id": "missing-user", "workspace_ids": ["workspace-1"]},
        )
        empty_count = verify_restore_after_delete._execute_count(
            conn,
            "SELECT count(*) FROM profiles "
            "WHERE user_id = :user_id OR workspace_id IN :workspace_ids",
            {"user_id": "missing-user", "workspace_ids": []},
        )

    assert count == 1
    assert empty_count == 0


def test_restore_after_delete_payload_is_redacted():
    payload = verify_restore_after_delete.build_restore_after_delete_payload(
        subject_email="test@example.com",
        restore_url="postgresql+psycopg://user:password@restore.example/restore_db",
        confirmation_label="careeragent-postgres-restore-test-20260702",
        mode="apply_redaction",
        pre_counts={"users": 1, "workspace_memberships": 1, "profiles": 1, "projects": 1},
        post_counts={"users": 1, "workspace_memberships": 1, "profiles": 0, "projects": 0},
        deleted_rows=2,
    )

    rendered = str(payload)
    assert payload["test_subject_hash_sha256"]
    assert payload["database_url_included"] is False
    assert payload["raw_private_data_included"] is False
    assert payload["restore_after_delete_blocked_or_redacted"] is True
    assert "test@example.com" not in rendered
    assert "password" not in rendered
    assert "restore.example" not in rendered


def test_restore_verifier_default_output_is_private_outputs():
    assert str(verify_restore_after_delete.DEFAULT_OUTPUT).endswith(
        "evidence/private_outputs/backup_purge_restore_after_delete_20260702.json"
    )
