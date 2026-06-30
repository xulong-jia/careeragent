from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import (
    AuthLoginRequest,
    AuthMeResponse,
    AuthRegisterRequest,
    AuthTokenResponse,
)
from app.schemas.common import ApiResponse
from app.services import auth_service


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[AuthTokenResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    payload: AuthRegisterRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = auth_service.register_user(db, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.post("/login", response_model=ApiResponse[AuthTokenResponse])
async def login(
    request: Request,
    payload: AuthLoginRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = auth_service.login_user(db, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.get("/me", response_model=ApiResponse[AuthMeResponse])
async def me(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = auth_service.build_me_response(db, user)
    return {"data": result, "request_id": request.state.request_id}


@router.post("/logout", response_model=ApiResponse[dict[str, object]])
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    del user
    return {"data": {"status": "logged_out"}, "request_id": request.state.request_id}
