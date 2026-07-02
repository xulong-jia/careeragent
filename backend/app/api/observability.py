from fastapi import APIRouter, Header

from app.core.errors import AppError


router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.post("/test-error")
async def test_error(
    x_observability_test: str | None = Header(default=None),
) -> None:
    if x_observability_test != "enabled":
        raise AppError(
            code="observability_test_forbidden",
            message="Observability test header is required.",
            status_code=403,
        )
    raise RuntimeError("Synthetic observability test error.")
