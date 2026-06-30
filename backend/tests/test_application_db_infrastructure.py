from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


def test_orm_metadata_contains_applications_table():
    assert "applications" in Base.metadata.tables


def test_alembic_migration_creates_applications_table(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_applications.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    table_names = set(inspect(engine).get_table_names())
    columns = {column["name"] for column in inspect(engine).get_columns("applications")}

    assert "applications" in table_names
    assert {
        "id",
        "company",
        "role_title",
        "role_category",
        "jd_id",
        "resume_version_id",
        "match_report_id",
        "agent_run_id",
        "status",
        "apply_date",
        "next_step_date",
        "interview_notes",
        "reflection",
        "tags",
        "created_at",
        "updated_at",
    }.issubset(columns)
    get_settings.cache_clear()


def test_applications_table_does_not_copy_resume_or_jd_raw_text():
    table = Base.metadata.tables.get("applications")
    columns = set(table.columns.keys()) if table is not None else set()

    assert columns.isdisjoint(
        {"raw_text", "jd_raw_text", "resume_text", "job_text", "full_text"}
    )
