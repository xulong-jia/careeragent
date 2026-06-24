from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


def test_orm_metadata_contains_project_rewrites_table():
    assert "project_rewrites" in Base.metadata.tables


def test_alembic_migration_creates_project_rewrites_table(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_project_rewrites.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("project_rewrites")}
    foreign_keys = inspector.get_foreign_keys("project_rewrites")

    assert "project_rewrites" in table_names
    assert {
        "id",
        "project_id",
        "jd_id",
        "resume_version_id",
        "match_report_id",
        "profile_id",
        "matched_points",
        "missing_points",
        "evidence_required",
        "rewritten_bullets",
        "forbidden_changes",
        "risk_flags",
        "rewrite_strategy",
        "created_at",
    }.issubset(columns)
    assert any(
        key["referred_table"] == "projects"
        and key["constrained_columns"] == ["project_id"]
        for key in foreign_keys
    )
    assert any(
        key["referred_table"] == "job_descriptions"
        and key["constrained_columns"] == ["jd_id"]
        for key in foreign_keys
    )
    assert any(
        key["referred_table"] == "resume_versions"
        and key["constrained_columns"] == ["resume_version_id"]
        for key in foreign_keys
    )
    assert any(
        key["referred_table"] == "match_reports"
        and key["constrained_columns"] == ["match_report_id"]
        for key in foreign_keys
    )
    assert any(
        key["referred_table"] == "profiles"
        and key["constrained_columns"] == ["profile_id"]
        for key in foreign_keys
    )
    get_settings.cache_clear()


def test_project_rewrites_table_does_not_copy_resume_raw_text():
    table = Base.metadata.tables.get("project_rewrites")
    columns = set(table.columns.keys()) if table is not None else set()

    assert columns.isdisjoint(
        {"raw_text", "raw_text_preview", "resume_text", "full_text"}
    )
