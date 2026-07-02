from pathlib import Path
import tempfile

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings, settings_summary, validate_runtime_settings
from app.core.metrics import metrics_snapshot
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.evaluation import EvaluationRun
from app.models.rag import RagAnswerRun, RagChunk, RagDocument


router = APIRouter(tags=["health"])


class HealthData(BaseModel):
    status: str
    service: str
    environment: str
    ai_provider_mode: str
    llm_provider: str
    embedding_provider: str
    vector_store: str
    rag_retrieval_mode: str
    real_llm_enabled: bool
    real_embedding_enabled: bool


class HealthResponse(BaseModel):
    data: HealthData
    request_id: str


class LivenessData(BaseModel):
    status: str
    service: str


class LivenessResponse(BaseModel):
    data: LivenessData
    request_id: str


class ReadinessData(BaseModel):
    status: str
    database_reachable: bool
    config_valid: bool
    storage_writable: bool
    migration_current: str | None = None
    migration_head: str | None = None
    migration_up_to_date: bool | None = None
    provider_summary: dict[str, object]
    rag_vector_summary: dict[str, object]
    config: dict[str, object]
    errors: list[str]


class ReadinessResponse(BaseModel):
    data: ReadinessData
    request_id: str


class MetricsResponse(BaseModel):
    data: dict[str, object]
    request_id: str


def _migration_status(db: Session) -> tuple[str | None, str | None, bool | None]:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(backend_root / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_config)
    head_revision = script.get_current_head()
    current_revision = MigrationContext.configure(db.connection()).get_current_revision()
    return current_revision, head_revision, current_revision == head_revision


def _storage_is_writable(local_data_dir: str) -> bool:
    storage_dir = Path(local_data_dir or "local_data")
    storage_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".readiness-", dir=storage_dir) as handle:
        handle.write(b"ok")
        handle.flush()
    return True


def _provider_summary(settings) -> dict[str, object]:
    return {
        "ai_provider_mode": settings.ai_provider_mode,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "real_llm_enabled": settings.enable_real_llm,
        "real_embedding_enabled": settings.enable_real_embedding,
    }


def _rag_vector_summary(settings) -> dict[str, object]:
    vector_store = settings.vector_store
    return {
        "vector_store": vector_store,
        "retrieval_mode": settings.rag_retrieval_mode,
        "embedding_dimension": settings.embedding_dimension,
        "pgvector_requested": vector_store == "pgvector",
        "production_status": (
            "deployment_profile_available"
            if vector_store == "pgvector"
            else "local_or_database_json_foundation"
        ),
    }


def _count_model(db: Session, model: type) -> int:
    return int(db.execute(select(func.count()).select_from(model)).scalar_one())


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> dict[str, object]:
    settings = get_settings()
    return {
        "data": {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.app_env,
            "ai_provider_mode": settings.ai_provider_mode,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "vector_store": settings.vector_store,
            "rag_retrieval_mode": settings.rag_retrieval_mode,
            "real_llm_enabled": settings.enable_real_llm,
            "real_embedding_enabled": settings.enable_real_embedding,
        },
        "request_id": request.state.request_id,
    }


@router.get("/live", response_model=LivenessResponse)
@router.get("/api/live", response_model=LivenessResponse)
@router.head("/live")
@router.head("/api/live")
async def get_liveness(request: Request) -> dict[str, object]:
    settings = get_settings()
    return {
        "data": {"status": "ok", "service": settings.app_name},
        "request_id": request.state.request_id,
    }


@router.get("/ready", response_model=ReadinessResponse)
@router.get("/api/ready", response_model=ReadinessResponse)
@router.head("/ready")
@router.head("/api/ready")
async def get_readiness(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    settings = get_settings()
    errors: list[str] = []
    config_valid = True
    try:
        validate_runtime_settings(settings)
    except RuntimeError as exc:
        config_valid = False
        errors.append(str(exc))

    database_reachable = False
    try:
        db.execute(text("SELECT 1"))
        database_reachable = True
    except Exception:
        errors.append("Database is not reachable.")

    storage_writable = False
    try:
        storage_writable = _storage_is_writable(settings.local_data_dir)
    except Exception:
        errors.append("Local data directory is not writable.")

    migration_current = None
    migration_head = None
    migration_up_to_date = None
    if database_reachable:
        try:
            migration_current, migration_head, migration_up_to_date = _migration_status(db)
        except Exception:
            errors.append("Database migration status could not be checked.")

    migration_ready = (
        settings.app_env != "production" or migration_up_to_date is True
    )

    return {
        "data": {
            "status": (
                "ok"
                if config_valid and database_reachable and storage_writable and migration_ready
                else "not_ready"
            ),
            "database_reachable": database_reachable,
            "config_valid": config_valid,
            "storage_writable": storage_writable,
            "migration_current": migration_current,
            "migration_head": migration_head,
            "migration_up_to_date": migration_up_to_date,
            "provider_summary": _provider_summary(settings),
            "rag_vector_summary": _rag_vector_summary(settings),
            "config": settings_summary(settings),
            "errors": errors,
        },
        "request_id": request.state.request_id,
    }


@router.get("/metrics", response_model=MetricsResponse)
@router.get("/api/metrics", response_model=MetricsResponse)
@router.head("/metrics")
@router.head("/api/metrics")
async def get_metrics(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    snapshot = metrics_snapshot()
    snapshot["runs"] = {
        "agent_runs_total": _count_model(db, AgentRun),
        "evaluation_runs_total": _count_model(db, EvaluationRun),
        "rag_documents_total": _count_model(db, RagDocument),
        "rag_chunks_total": _count_model(db, RagChunk),
        "rag_answer_runs_total": _count_model(db, RagAnswerRun),
    }
    return {"data": snapshot, "request_id": request.state.request_id}
