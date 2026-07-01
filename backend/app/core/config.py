import os
from dataclasses import dataclass
from functools import lru_cache
from sqlalchemy.engine import make_url


FORBIDDEN_PRODUCTION_SECRET_MARKERS = (
    "dev-only",
    "local-dev-only",
    "replace-me",
    "change-me",
    "placeholder",
)
ALLOWED_APP_ENVS = {"development", "test", "production"}


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, default)
    values = [item.strip() for item in raw_value.split(",")]
    return tuple(item for item in values if item)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    backend_host: str
    backend_port: int
    cors_origins: tuple[str, ...]
    database_url: str
    auth_jwt_secret: str
    auth_token_expire_minutes: int
    rate_limit_per_minute: int
    ai_provider_mode: str
    llm_provider: str
    llm_api_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: float
    llm_temperature: float
    embedding_provider: str
    embedding_api_base_url: str
    embedding_api_key: str
    embedding_model: str
    embedding_dimension: int
    vector_store: str
    rag_retrieval_mode: str
    enable_real_llm: bool
    enable_real_embedding: bool


def is_sqlite_database_url(database_url: str) -> bool:
    return _database_driver_name(database_url).startswith("sqlite")


def _database_driver_name(database_url: str) -> str:
    try:
        return make_url(database_url).drivername
    except Exception:
        return "invalid"


def _mask_config_value(value: str) -> str:
    if not value:
        return ""
    return f"[set length={len(value)}]"


def _is_placeholder_secret(value: str) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in FORBIDDEN_PRODUCTION_SECRET_MARKERS)


def validate_runtime_settings(settings: Settings) -> None:
    if settings.app_env not in ALLOWED_APP_ENVS:
        raise RuntimeError("APP_ENV must be one of development, test, or production.")
    if _database_driver_name(settings.database_url) == "invalid":
        raise RuntimeError("DATABASE_URL is invalid.")

    if settings.app_env != "production":
        return

    secret = settings.auth_jwt_secret.strip()
    if not secret:
        raise RuntimeError("AUTH_JWT_SECRET is required in production.")
    if len(secret) < 32:
        raise RuntimeError("AUTH_JWT_SECRET must be at least 32 characters in production.")
    if _is_placeholder_secret(secret):
        raise RuntimeError("AUTH_JWT_SECRET must not be a placeholder in production.")
    if is_sqlite_database_url(settings.database_url):
        raise RuntimeError("SQLite DATABASE_URL is not allowed in production.")
    if "*" in settings.cors_origins:
        raise RuntimeError("BACKEND_CORS_ORIGINS must not contain * in production.")


def settings_summary(settings: Settings) -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "database_driver": _database_driver_name(settings.database_url),
        "database_is_sqlite": is_sqlite_database_url(settings.database_url),
        "auth_jwt_secret": _mask_config_value(settings.auth_jwt_secret),
        "auth_token_expire_minutes": settings.auth_token_expire_minutes,
        "ai_provider_mode": settings.ai_provider_mode,
        "llm_provider": settings.llm_provider,
        "llm_api_base_url": _mask_config_value(settings.llm_api_base_url),
        "llm_api_key": _mask_config_value(settings.llm_api_key),
        "llm_model": settings.llm_model,
        "embedding_provider": settings.embedding_provider,
        "embedding_api_base_url": _mask_config_value(settings.embedding_api_base_url),
        "embedding_api_key": _mask_config_value(settings.embedding_api_key),
        "embedding_model": settings.embedding_model,
        "vector_store": settings.vector_store,
        "rag_retrieval_mode": settings.rag_retrieval_mode,
        "enable_real_llm": settings.enable_real_llm,
        "enable_real_embedding": settings.enable_real_embedding,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "CareerAgent API"),
        app_env=os.getenv("APP_ENV", "development").strip().lower(),
        backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        cors_origins=_csv_env("BACKEND_CORS_ORIGINS", "http://localhost:5173"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./local_data/careeragent.db"),
        auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", "").strip(),
        auth_token_expire_minutes=int(os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "60")),
        rate_limit_per_minute=int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "0")),
        ai_provider_mode=os.getenv("AI_PROVIDER_MODE", "deterministic").strip().lower(),
        llm_provider=os.getenv("LLM_PROVIDER", "deterministic").strip().lower(),
        llm_api_base_url=os.getenv("LLM_API_BASE_URL", "").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local").strip().lower(),
        embedding_api_base_url=os.getenv("EMBEDDING_API_BASE_URL", "").strip(),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "local-bow-v1").strip(),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
        vector_store=os.getenv("VECTOR_STORE", "local").strip().lower(),
        rag_retrieval_mode=os.getenv("RAG_RETRIEVAL_MODE", "lexical").strip().lower(),
        enable_real_llm=_bool_env("ENABLE_REAL_LLM", False),
        enable_real_embedding=_bool_env("ENABLE_REAL_EMBEDDING", False),
    )
