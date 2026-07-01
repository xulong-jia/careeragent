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
LOCAL_DEV_DATA_ENCRYPTION_KEY = "MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew="


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
    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout_seconds: float
    db_echo_sql: bool
    local_data_dir: str
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
    data_encryption_key: str
    data_encryption_key_id: str


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


def _mask_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "[invalid]"


def _is_placeholder_secret(value: str) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in FORBIDDEN_PRODUCTION_SECRET_MARKERS)


def _is_valid_fernet_key(value: str) -> bool:
    if not value:
        return False
    try:
        from cryptography.fernet import Fernet

        Fernet(value.encode("utf-8"))
    except Exception:
        return False
    return True


def validate_runtime_settings(settings: Settings) -> None:
    if settings.app_env not in ALLOWED_APP_ENVS:
        raise RuntimeError("APP_ENV must be one of development, test, or production.")
    if _database_driver_name(settings.database_url) == "invalid":
        raise RuntimeError("DATABASE_URL is invalid.")
    if settings.data_encryption_key and not _is_valid_fernet_key(settings.data_encryption_key):
        raise RuntimeError("DATA_ENCRYPTION_KEY must be a valid Fernet key.")
    if settings.db_pool_size < 1:
        raise RuntimeError("DB_POOL_SIZE must be at least 1.")
    if settings.db_max_overflow < 0:
        raise RuntimeError("DB_MAX_OVERFLOW must be 0 or greater.")
    if settings.db_pool_timeout_seconds <= 0:
        raise RuntimeError("DB_POOL_TIMEOUT_SECONDS must be greater than 0.")

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
    if settings.db_echo_sql:
        raise RuntimeError("DB_ECHO_SQL must be false in production.")
    if "*" in settings.cors_origins:
        raise RuntimeError("BACKEND_CORS_ORIGINS must not contain * in production.")
    data_key = settings.data_encryption_key.strip()
    if not data_key:
        raise RuntimeError("DATA_ENCRYPTION_KEY is required in production.")
    if _is_placeholder_secret(data_key) or data_key == LOCAL_DEV_DATA_ENCRYPTION_KEY:
        raise RuntimeError("DATA_ENCRYPTION_KEY must not be a placeholder in production.")
    key_id = settings.data_encryption_key_id.strip()
    if not key_id:
        raise RuntimeError("DATA_ENCRYPTION_KEY_ID is required in production.")
    if _is_placeholder_secret(key_id):
        raise RuntimeError("DATA_ENCRYPTION_KEY_ID must not be a placeholder in production.")


def settings_summary(settings: Settings) -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "database_driver": _database_driver_name(settings.database_url),
        "database_is_sqlite": is_sqlite_database_url(settings.database_url),
        "database_url": _mask_database_url(settings.database_url),
        "db_pool_size": settings.db_pool_size,
        "db_max_overflow": settings.db_max_overflow,
        "db_pool_timeout_seconds": settings.db_pool_timeout_seconds,
        "db_echo_sql": settings.db_echo_sql,
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
        "data_encryption_key": _mask_config_value(settings.data_encryption_key),
        "data_encryption_key_id": settings.data_encryption_key_id,
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
        db_pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        db_pool_timeout_seconds=float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30")),
        db_echo_sql=_bool_env("DB_ECHO_SQL", False),
        local_data_dir=os.getenv("LOCAL_DATA_DIR", "local_data").strip(),
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
        data_encryption_key=os.getenv("DATA_ENCRYPTION_KEY", "").strip(),
        data_encryption_key_id=os.getenv("DATA_ENCRYPTION_KEY_ID", "local-dev-v1").strip(),
    )
