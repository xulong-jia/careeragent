from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.base import Base
from app.models.agent import AgentRun, AgentStep
from conftest import get_data, make_client


AGENT_TABLES = {"agent_runs", "agent_steps"}
PRIVATE_TEXT_COLUMNS = {"raw_text", "jd_raw_text", "chunk_text"}


def test_orm_metadata_contains_agent_tables():
    assert AGENT_TABLES.issubset(set(Base.metadata.tables))


def test_alembic_migration_creates_agent_tables(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_agent_test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert AGENT_TABLES.issubset(set(inspector.get_table_names()))
    assert {
        "workflow_name",
        "status",
        "input_refs",
        "output_refs",
        "missing_slots",
        "questions",
        "duration_ms",
    }.issubset({column["name"] for column in inspector.get_columns("agent_runs")})
    assert {
        "run_id",
        "step_name",
        "step_order",
        "status",
        "input_refs",
        "output_refs",
        "duration_ms",
    }.issubset({column["name"] for column in inspector.get_columns("agent_steps")})
    assert "ix_agent_runs_workflow_name" in {
        index["name"] for index in inspector.get_indexes("agent_runs")
    }
    assert "ix_agent_runs_status" in {
        index["name"] for index in inspector.get_indexes("agent_runs")
    }
    assert "ix_agent_steps_run_id" in {
        index["name"] for index in inspector.get_indexes("agent_steps")
    }
    assert "ix_agent_steps_status" in {
        index["name"] for index in inspector.get_indexes("agent_steps")
    }
    assert "uq_agent_steps_run_id_step_order" in {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("agent_steps")
    }

    get_settings.cache_clear()


def test_agent_run_and_step_insert_with_json_refs(db_session):
    run = AgentRun(
        id="agent_run_0001",
        workflow_name="job_application_preparation",
        input_refs={"resume_version_id": "resume_version_001", "jd_id": "jd_001"},
        output_refs={},
    )
    run.steps.append(
        AgentStep(
            id="agent_step_0001",
            step_name="validate_inputs",
            step_order=1,
            input_refs={"resume_version_id": "resume_version_001", "jd_id": "jd_001"},
            output_refs={"validated": True},
            duration_ms=12,
        )
    )

    db_session.add(run)
    db_session.commit()

    persisted = db_session.get(AgentRun, "agent_run_0001")
    assert persisted is not None
    assert persisted.user_id == "default"
    assert persisted.status == "pending"
    assert persisted.input_refs["resume_version_id"] == "resume_version_001"
    assert persisted.output_refs == {}
    assert persisted.steps[0].status == "pending"
    assert persisted.steps[0].run_id == "agent_run_0001"
    assert persisted.steps[0].output_refs["validated"] is True
    assert persisted.steps[0].duration_ms == 12


def test_agent_step_run_order_unique_constraint(db_session):
    run = AgentRun(
        id="agent_run_unique",
        workflow_name="job_application_preparation",
        input_refs={},
        output_refs={},
    )
    run.steps.extend(
        [
            AgentStep(
                id="agent_step_unique_1",
                step_name="validate_inputs",
                step_order=1,
                input_refs={},
                output_refs={},
            ),
            AgentStep(
                id="agent_step_unique_2",
                step_name="load_resume_version",
                step_order=1,
                input_refs={},
                output_refs={},
            ),
        ]
    )

    db_session.add(run)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_agent_run_delete_orphan_removes_steps(db_session):
    run = AgentRun(
        id="agent_run_delete",
        workflow_name="job_application_preparation",
        input_refs={},
        output_refs={},
    )
    run.steps.append(
        AgentStep(
            id="agent_step_delete",
            step_name="validate_inputs",
            step_order=1,
            input_refs={},
            output_refs={},
        )
    )
    db_session.add(run)
    db_session.commit()

    db_session.delete(run)
    db_session.commit()

    assert db_session.get(AgentRun, "agent_run_delete") is None
    assert db_session.get(AgentStep, "agent_step_delete") is None


def test_agent_tables_do_not_include_raw_text_columns():
    run_columns = set(AgentRun.__table__.columns.keys())
    step_columns = set(AgentStep.__table__.columns.keys())

    assert run_columns.isdisjoint(PRIVATE_TEXT_COLUMNS)
    assert step_columns.isdisjoint(PRIVATE_TEXT_COLUMNS)


def test_db_health_still_returns_reachable_status():
    client = make_client()

    response = client.get("/api/db/health")

    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "ok"
    assert data["database_reachable"] is True
