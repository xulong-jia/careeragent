import os
from dataclasses import dataclass
from functools import lru_cache


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


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "CareerAgent API"),
        app_env=os.getenv("APP_ENV", "development"),
        backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        cors_origins=_csv_env("BACKEND_CORS_ORIGINS", "http://localhost:5173"),
    )
