from datetime import datetime
from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    id: str
    email: str
    display_name: str | None
    role: str
    is_active: bool


class AuthWorkspace(BaseModel):
    id: str
    name: str
    role: str


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=160)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    session_id: str
    user: AuthUser
    workspace: AuthWorkspace


class AuthMeResponse(BaseModel):
    user: AuthUser
    workspace: AuthWorkspace


class AuthSessionRecord(BaseModel):
    session_id: str
    device_label: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    revoke_reason: str | None = None
    current: bool = False


class AuthSessionListResponse(BaseModel):
    items: list[AuthSessionRecord]
    total: int
