from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


def test_orm_metadata_contains_projects_table():
    assert "projects" in Base.metadata.tables


def test_alembic_migration_creates_projects_table(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_projects.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("projects")}
    foreign_keys = inspector.get_foreign_keys("projects")

    assert "projects" in table_names
    assert {
        "id",
        "user_id",
        "profile_id",
        "resume_version_id",
        "name",
        "role",
        "period",
        "background",
        "tech_stack",
        "responsibilities",
        "results",
        "evidence",
        "status",
        "created_at",
        "updated_at",
    }.issubset(columns)
    assert any(
        key["referred_table"] == "profiles"
        and key["constrained_columns"] == ["profile_id"]
        for key in foreign_keys
    )
    assert any(
        key["referred_table"] == "resume_versions"
        and key["constrained_columns"] == ["resume_version_id"]
        for key in foreign_keys
    )
    get_settings.cache_clear()


def test_projects_table_does_not_copy_resume_raw_text():
    table = Base.metadata.tables.get("projects")
    columns = set(table.columns.keys()) if table is not None else set()

    assert columns.isdisjoint(
        {"raw_text", "raw_text_preview", "resume_text", "full_text"}
    )
