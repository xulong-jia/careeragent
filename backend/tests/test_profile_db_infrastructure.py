from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


def test_orm_metadata_contains_profiles_table():
    assert "profiles" in Base.metadata.tables


def test_alembic_migration_creates_profiles_table(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_profiles.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("profiles")}
    foreign_keys = inspector.get_foreign_keys("profiles")

    assert "profiles" in table_names
    assert {
        "id",
        "user_id",
        "target_roles",
        "target_industries",
        "target_locations",
        "skill_map",
        "preferences",
        "source_resume_version_id",
        "created_at",
        "updated_at",
    }.issubset(columns)
    assert any(
        key["referred_table"] == "resume_versions"
        and key["constrained_columns"] == ["source_resume_version_id"]
        for key in foreign_keys
    )
    get_settings.cache_clear()


def test_profiles_table_does_not_copy_resume_raw_text():
    table = Base.metadata.tables.get("profiles")
    columns = set(table.columns.keys()) if table is not None else set()

    assert columns.isdisjoint(
        {"raw_text", "raw_text_preview", "resume_text", "full_text"}
    )
