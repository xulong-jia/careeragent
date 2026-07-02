from uuid import uuid4
import time

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.agents import router as agents_router
from app.api.applications import router as applications_router
from app.api.auth import router as auth_router
from app.api.db import router as db_router
from app.api.dependencies import require_active_user
from app.api.evaluations import bad_cases_router, router as evaluations_router
from app.api.health import router as health_router
from app.api.interviews import router as interviews_router
from app.api.jobs import router as jobs_router
from app.api.matches import router as matches_router
from app.api.observability import router as observability_router
from app.api.privacy import router as privacy_router
from app.api.profiles import router as profiles_router
from app.api.project_rewrites import router as project_rewrites_router
from app.api.projects import router as projects_router
from app.api.rag import router as rag_router
from app.api.resume_versions import router as resume_versions_router
from app.api.resumes import router as resumes_router
from app.api.study_plans import router as study_plans_router
from app.core.config import get_settings, validate_runtime_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging, log_event
from app.core.metrics import record_http_request
from app.core.observability import initialize_sentry


def _validate_startup_security(settings) -> None:
    validate_runtime_settings(settings)


def create_app() -> FastAPI:
    settings = get_settings()
    _validate_startup_security(settings)
    configure_logging()
    initialize_sentry(settings)
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        record_http_request(response.status_code, duration_ms)
        log_event(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    # ponytail: in-memory per-process limiter; replace with Redis/WAF when scaling.
    request_counts: dict[tuple[str, int], int] = {}

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if settings.rate_limit_per_minute <= 0:
            return await call_next(request)
        import time

        minute = int(time.time() // 60)
        client_host = request.client.host if request.client else "unknown"
        key = (client_host, minute)
        request_counts[key] = request_counts.get(key, 0) + 1
        if request_counts[key] > settings.rate_limit_per_minute:
            from app.core.errors import build_error_response

            return build_error_response(
                request,
                429,
                "rate_limit_exceeded",
                "Too many requests.",
            )
        return await call_next(request)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    protected = [Depends(require_active_user)]
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(db_router, dependencies=protected)
    app.include_router(profiles_router, dependencies=protected)
    app.include_router(projects_router, dependencies=protected)
    app.include_router(project_rewrites_router, dependencies=protected)
    app.include_router(interviews_router, dependencies=protected)
    app.include_router(study_plans_router, dependencies=protected)
    app.include_router(resumes_router, dependencies=protected)
    app.include_router(resume_versions_router, dependencies=protected)
    app.include_router(jobs_router, dependencies=protected)
    app.include_router(matches_router, dependencies=protected)
    app.include_router(privacy_router, dependencies=protected)
    app.include_router(rag_router, dependencies=protected)
    app.include_router(agents_router, dependencies=protected)
    app.include_router(applications_router, dependencies=protected)
    app.include_router(evaluations_router, dependencies=protected)
    app.include_router(bad_cases_router, dependencies=protected)
    if settings.enable_observability_test_endpoint:
        app.include_router(observability_router)

    return app


app = create_app()
