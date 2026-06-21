from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
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


def make_client():
    return TestClient(app)


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
