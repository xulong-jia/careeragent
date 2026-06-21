from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
from app.models.evaluation import BadCase
from conftest import get_data, make_client


BAD_CASE_TABLES = {"bad_cases"}
PRIVATE_TEXT_COLUMNS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}
BAD_CASE_INDEXES = {
    "ix_bad_cases_source_type",
    "ix_bad_cases_source_id",
    "ix_bad_cases_status",
    "ix_bad_cases_severity",
    "ix_bad_cases_category",
    "ix_bad_cases_source_type_source_id",
}


def test_orm_metadata_contains_bad_cases_table():
    assert BAD_CASE_TABLES.issubset(set(Base.metadata.tables))


def test_alembic_migration_creates_bad_cases_table(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_bad_cases_test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert BAD_CASE_TABLES.issubset(set(inspector.get_table_names()))
    assert {
        "source_type",
        "source_id",
        "category",
        "severity",
        "title",
        "description",
        "expected_behavior",
        "actual_behavior",
        "suggested_fix",
        "status",
        "resolved_at",
    }.issubset({column["name"] for column in inspector.get_columns("bad_cases")})
    assert BAD_CASE_INDEXES.issubset(
        {index["name"] for index in inspector.get_indexes("bad_cases")}
    )

    get_settings.cache_clear()


def test_bad_case_insert_defaults_and_text_fields(db_session):
    bad_case = BadCase(
        id="bad_case_0001",
        source_type="match_report",
        source_id="match_report_0001",
        category="match_score_inaccurate",
        title="Synthetic score mismatch",
        description="Synthetic summary of a score issue.",
        expected_behavior="Expected a lower score for missing Python evidence.",
        actual_behavior="Actual score stayed high despite missing evidence.",
        suggested_fix="Adjust deterministic scoring around missing required skills.",
    )

    db_session.add(bad_case)
    db_session.commit()

    persisted = db_session.get(BadCase, "bad_case_0001")
    assert persisted is not None
    assert persisted.user_id == "default"
    assert persisted.status == "open"
    assert persisted.severity == "medium"
    assert persisted.source_type == "match_report"
    assert persisted.source_id == "match_report_0001"
    assert persisted.category == "match_score_inaccurate"
    assert persisted.description == "Synthetic summary of a score issue."
    assert persisted.expected_behavior == (
        "Expected a lower score for missing Python evidence."
    )
    assert persisted.actual_behavior == (
        "Actual score stayed high despite missing evidence."
    )
    assert persisted.suggested_fix == (
        "Adjust deterministic scoring around missing required skills."
    )
    assert persisted.resolved_at is None


def test_bad_cases_table_does_not_include_private_text_columns():
    columns = set(BadCase.__table__.columns.keys())

    assert columns.isdisjoint(PRIVATE_TEXT_COLUMNS)


def test_db_health_still_returns_reachable_status():
    client = make_client()

    response = client.get("/api/db/health")

    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "ok"
    assert data["database_reachable"] is True
