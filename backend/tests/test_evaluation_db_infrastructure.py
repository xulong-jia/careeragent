from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
from app.models.evaluation import EvaluationCase, EvaluationResult, EvaluationRun


EVALUATION_TABLES = {
    "evaluation_runs",
    "evaluation_cases",
    "evaluation_results",
}
PRIVATE_TEXT_COLUMNS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}


def test_orm_metadata_contains_evaluation_tables():
    assert EVALUATION_TABLES.issubset(set(Base.metadata.tables))


def test_alembic_migration_creates_evaluation_tables(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_evaluations_test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert EVALUATION_TABLES.issubset(set(inspector.get_table_names()))
    assert {
        "id",
        "name",
        "module",
        "dataset_name",
        "status",
        "metrics",
        "run_config",
        "started_at",
        "finished_at",
        "created_at",
    }.issubset({column["name"] for column in inspector.get_columns("evaluation_runs")})
    assert {
        "id",
        "module",
        "dataset_name",
        "case_name",
        "input_payload",
        "expected_output",
        "tags",
        "source_type",
        "bad_case_id",
    }.issubset({column["name"] for column in inspector.get_columns("evaluation_cases")})
    assert {
        "id",
        "run_id",
        "case_id",
        "module",
        "status",
        "actual_output",
        "expected_output",
        "passed",
        "score",
        "error",
    }.issubset({column["name"] for column in inspector.get_columns("evaluation_results")})

    get_settings.cache_clear()


def test_evaluation_tables_do_not_include_private_text_columns():
    for model in (EvaluationRun, EvaluationCase, EvaluationResult):
        columns = set(model.__table__.columns.keys())
        assert columns.isdisjoint(PRIVATE_TEXT_COLUMNS)


def test_evaluation_models_persist_json_payloads(db_session):
    run = EvaluationRun(
        id="eval_run_test",
        name="Synthetic smoke run",
        module="all",
        dataset_name="synthetic_smoke_v1",
        status="completed",
        metrics={"pass_rate": 1.0},
        run_config={"deterministic": True},
    )
    evaluation_case = EvaluationCase(
        id="eval_case_test",
        module="match",
        dataset_name="synthetic_smoke_v1",
        case_name="match smoke",
        input_payload={"resume_signals": ["python"]},
        expected_output={"required_fields": ["total_score"]},
        tags=["synthetic"],
        source_type="synthetic",
    )
    result = EvaluationResult(
        id="eval_result_test",
        run_id=run.id,
        case_id=evaluation_case.id,
        module="match",
        status="passed",
        actual_output={"total_score": 80},
        expected_output={"required_fields": ["total_score"]},
        passed=True,
        score=1.0,
    )

    db_session.add(run)
    db_session.add(evaluation_case)
    db_session.add(result)
    db_session.commit()

    persisted_run = db_session.get(EvaluationRun, "eval_run_test")
    persisted_case = db_session.get(EvaluationCase, "eval_case_test")
    persisted_result = db_session.get(EvaluationResult, "eval_result_test")

    assert persisted_run.metrics["pass_rate"] == 1.0
    assert persisted_run.run_config["deterministic"] is True
    assert persisted_case.input_payload["resume_signals"] == ["python"]
    assert persisted_case.tags == ["synthetic"]
    assert persisted_result.actual_output["total_score"] == 80
    assert persisted_result.passed is True
