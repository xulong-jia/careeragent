from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import create_database_engine
import app.models  # noqa: F401
from conftest import get_data, make_client


CORE_TABLES = {
    "resumes",
    "resume_versions",
    "job_descriptions",
    "job_profiles",
    "match_reports",
}


def test_database_engine_can_create_session_connection():
    engine = create_database_engine("sqlite:///:memory:")

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_orm_metadata_contains_phase_two_core_tables():
    assert CORE_TABLES.issubset(set(Base.metadata.tables))


def test_alembic_initial_migration_creates_core_tables(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    table_names = set(inspect(engine).get_table_names())

    assert CORE_TABLES.issubset(table_names)
    get_settings.cache_clear()


def test_db_health_returns_reachable_status_without_sensitive_url():
    client = make_client()

    response = client.get("/api/db/health")

    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "ok"
    assert data["database_reachable"] is True
    assert data["database_type"].startswith("sqlite")
    assert "database_url" not in data
    assert set(data["missing_tables"]).issubset(CORE_TABLES)
