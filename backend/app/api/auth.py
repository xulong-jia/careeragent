from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import _extract_bearer_token, get_current_user
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import (
    AuthLoginRequest,
    AuthMeResponse,
    AuthRegisterRequest,
    AuthSessionListResponse,
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
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = auth_service.logout_user(
        db,
        token=_extract_bearer_token(authorization),
        user=user,
    )
    return {"data": result, "request_id": request.state.request_id}


@router.get("/sessions", response_model=ApiResponse[AuthSessionListResponse])
async def sessions(
    request: Request,
    user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    payload = decode_access_token(_extract_bearer_token(authorization))
    result = auth_service.list_sessions(
        db,
        user=user,
        workspace_id=str(payload.get("workspace_id") or ""),
        current_session_id=str(payload.get("sid") or ""),
    )
    return {"data": result, "request_id": request.state.request_id}


@router.post("/sessions/{session_id}/revoke", response_model=ApiResponse[dict[str, object]])
async def revoke_session(
    session_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    payload = decode_access_token(_extract_bearer_token(authorization))
    result = auth_service.revoke_session(
        db,
        user=user,
        workspace_id=str(payload.get("workspace_id") or ""),
        session_id=session_id,
    )
    return {"data": result, "request_id": request.state.request_id}
