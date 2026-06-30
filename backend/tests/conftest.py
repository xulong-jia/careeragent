import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AUTH_JWT_SECRET", "test-auth-secret-for-careeragent-p1")

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.security import create_access_token, hash_password
from app.core.tenant import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID
from app.models.auth import User, Workspace, WorkspaceMembership
import app.models as app_models  # noqa: F401
from app.services.mock_store import store


@pytest.fixture(autouse=True)
def isolated_test_state():
    store.resumes.clear()
    store.jobs.clear()
    store.matches.clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    store.resumes.clear()
    store.jobs.clear()
    store.matches.clear()


def get_data(response):
    payload = response.json()
    assert set(payload) == {"data", "request_id"}
    assert payload["request_id"]
    return payload["data"]


def get_error(response):
    payload = response.json()
    assert set(payload) == {"error", "request_id"}
    assert payload["request_id"]
    return payload["error"]


def _seed_test_user(
    user_id: str = DEFAULT_USER_ID,
    email: str = "test@example.com",
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> None:
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        if db.get(User, user_id) is None:
            db.add(
                User(
                    id=user_id,
                    email=email,
                    password_hash=hash_password("TestPassword123!"),
                    display_name="Test User",
                    role="user",
                    is_active=True,
                )
            )
        if db.get(Workspace, workspace_id) is None:
            db.add(
                Workspace(
                    id=workspace_id,
                    owner_user_id=user_id,
                    name="Test Workspace",
                )
            )
        if db.get(WorkspaceMembership, (workspace_id, user_id)) is None:
            db.add(
                WorkspaceMembership(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role="owner",
                )
            )
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def make_client(
    *,
    authenticated: bool = True,
    user_id: str = DEFAULT_USER_ID,
    email: str = "test@example.com",
    workspace_id: str = DEFAULT_WORKSPACE_ID,
):
    client = TestClient(app)
    if authenticated:
        _seed_test_user(user_id=user_id, email=email, workspace_id=workspace_id)
        token, _ = create_access_token(
            subject=user_id,
            email=email,
            role="user",
            workspace_id=workspace_id,
        )
        client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def db_session():
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        yield db
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
