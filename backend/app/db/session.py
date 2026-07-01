from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings, is_sqlite_database_url


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return
    if not url.database or url.database == ":memory:":
        return
    Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = database_url or settings.database_url
    _ensure_sqlite_parent_dir(url)
    engine_options = {
        "connect_args": _sqlite_connect_args(url),
        "pool_pre_ping": True,
        "future": True,
        "echo": settings.db_echo_sql,
    }
    if not is_sqlite_database_url(url):
        engine_options.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_timeout": settings.db_pool_timeout_seconds,
            }
        )
    return create_engine(url, **engine_options)


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
