from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.schemas.common import ApiResponse
from app.db.session import engine


router = APIRouter(prefix="/api/db", tags=["database"])

CORE_TABLES = {
    "resumes",
    "resume_versions",
    "job_descriptions",
    "job_profiles",
    "match_reports",
}


def get_database_type(database_url: str) -> str:
    return make_url(database_url).drivername


@router.get("/health", response_model=ApiResponse[dict[str, object]])
def db_health(request: Request) -> dict[str, object]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        table_names = set(inspect(connection).get_table_names())

    missing_tables = sorted(CORE_TABLES - table_names)
    return {
        "data": {
            "status": "ok",
            "database_reachable": True,
            "database_type": get_database_type(get_settings().database_url),
            "core_tables_present": not missing_tables,
            "missing_tables": missing_tables,
        },
        "request_id": request.state.request_id,
    }
