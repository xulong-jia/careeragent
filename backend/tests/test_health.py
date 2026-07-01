def get_client():
    from app.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_health_returns_success_envelope(monkeypatch):
    from app.core.config import get_settings

    for name in (
        "AI_PROVIDER_MODE",
        "LLM_PROVIDER",
        "LLM_API_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_API_BASE_URL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_MODEL",
        "VECTOR_STORE",
        "RAG_RETRIEVAL_MODE",
        "ENABLE_REAL_LLM",
        "ENABLE_REAL_EMBEDDING",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    response = get_client().get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"data", "request_id"}
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "CareerAgent API"
    assert payload["data"]["llm_provider"] == "deterministic"
    assert payload["data"]["embedding_provider"] == "local"
    assert payload["data"]["vector_store"] == "local"
    assert payload["data"]["rag_retrieval_mode"] == "lexical"
    assert payload["data"]["real_llm_enabled"] is False
    assert payload["data"]["real_embedding_enabled"] is False
    assert "api_key" not in str(payload["data"]).lower()
    assert "sk-" not in str(payload["data"])
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]
    get_settings.cache_clear()


def test_unknown_route_returns_error_envelope():
    response = get_client().get("/missing")

    assert response.status_code == 404
    payload = response.json()
    assert set(payload) == {"error", "request_id"}
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"]
    assert isinstance(payload["error"]["details"], dict)
    assert payload["request_id"]
