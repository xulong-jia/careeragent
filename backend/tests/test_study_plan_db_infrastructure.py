from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


STUDY_PLAN_PRIVATE_TEXT_COLUMNS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "jd_raw_text",
    "answer_text",
    "full_text",
    "source_text",
}


def test_orm_metadata_contains_study_plan_table():
    assert "study_plans" in Base.metadata.tables


def test_alembic_migration_creates_study_plan_table(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_study_plans.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("study_plans")}
    foreign_keys = inspector.get_foreign_keys("study_plans")

    assert "study_plans" in table_names
    assert {
        "id",
        "user_id",
        "match_report_id",
        "profile_id",
        "project_rewrite_id",
        "target_role",
        "source_refs",
        "phases",
        "status",
        "created_at",
        "updated_at",
    }.issubset(columns)
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
    assert any(
        key["referred_table"] == "project_rewrites"
        and key["constrained_columns"] == ["project_rewrite_id"]
        for key in foreign_keys
    )
    get_settings.cache_clear()


def test_study_plan_table_does_not_copy_private_text_columns():
    table = Base.metadata.tables.get("study_plans")
    columns = set(table.columns.keys()) if table is not None else set()

    assert columns.isdisjoint(STUDY_PLAN_PRIVATE_TEXT_COLUMNS)
