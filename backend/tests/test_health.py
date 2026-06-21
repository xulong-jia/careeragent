def get_client():
    from app.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_health_returns_success_envelope():
    response = get_client().get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"data", "request_id"}
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "CareerAgent API"
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]


def test_unknown_route_returns_error_envelope():
    response = get_client().get("/missing")

    assert response.status_code == 404
    payload = response.json()
    assert set(payload) == {"error", "request_id"}
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"]
    assert isinstance(payload["error"]["details"], dict)
    assert payload["request_id"]
