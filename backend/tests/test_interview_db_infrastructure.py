from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


INTERVIEW_PRIVATE_TEXT_COLUMNS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "jd_raw_text",
    "full_text",
    "source_text",
}


def test_orm_metadata_contains_interview_tables():
    assert "interview_questions" in Base.metadata.tables
    assert "interview_answers" in Base.metadata.tables


def test_alembic_migration_creates_interview_tables(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_interviews.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    question_columns = {
        column["name"] for column in inspector.get_columns("interview_questions")
    }
    answer_columns = {
        column["name"] for column in inspector.get_columns("interview_answers")
    }
    question_foreign_keys = inspector.get_foreign_keys("interview_questions")
    answer_foreign_keys = inspector.get_foreign_keys("interview_answers")

    assert {"interview_questions", "interview_answers"}.issubset(table_names)
    assert {
        "id",
        "user_id",
        "jd_id",
        "resume_version_id",
        "project_id",
        "project_rewrite_id",
        "question_type",
        "question",
        "expected_points",
        "source_refs",
        "difficulty",
        "created_at",
    }.issubset(question_columns)
    assert {
        "id",
        "question_id",
        "user_id",
        "answer_text",
        "answer_text_preview",
        "scores",
        "feedback",
        "weakness_tags",
        "created_at",
    }.issubset(answer_columns)
    assert any(
        key["referred_table"] == "job_descriptions"
        and key["constrained_columns"] == ["jd_id"]
        for key in question_foreign_keys
    )
    assert any(
        key["referred_table"] == "resume_versions"
        and key["constrained_columns"] == ["resume_version_id"]
        for key in question_foreign_keys
    )
    assert any(
        key["referred_table"] == "projects"
        and key["constrained_columns"] == ["project_id"]
        for key in question_foreign_keys
    )
    assert any(
        key["referred_table"] == "project_rewrites"
        and key["constrained_columns"] == ["project_rewrite_id"]
        for key in question_foreign_keys
    )
    assert any(
        key["referred_table"] == "interview_questions"
        and key["constrained_columns"] == ["question_id"]
        for key in answer_foreign_keys
    )
    get_settings.cache_clear()


def test_interview_tables_do_not_copy_resume_or_jd_raw_text():
    question_table = Base.metadata.tables.get("interview_questions")
    answer_table = Base.metadata.tables.get("interview_answers")
    question_columns = set(question_table.columns.keys()) if question_table is not None else set()
    answer_columns = set(answer_table.columns.keys()) if answer_table is not None else set()

    assert question_columns.isdisjoint(INTERVIEW_PRIVATE_TEXT_COLUMNS)
    assert answer_columns.isdisjoint(
        INTERVIEW_PRIVATE_TEXT_COLUMNS - {"answer_text", "answer_text_preview"}
    )
