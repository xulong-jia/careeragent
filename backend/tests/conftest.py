from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.mock_store import store


@pytest.fixture(autouse=True)
def clear_mock_store():
    store.resumes.clear()
    store.jobs.clear()
    store.matches.clear()
    yield


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
