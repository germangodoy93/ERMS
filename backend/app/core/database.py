"""Database engine and session management (SQLAlchemy 2, synchronous, psycopg 3).

Synchronous access is a deliberate decision (see docs/ERMS-HLD.md, ADR-001):
Celery workers and the API share the same models and session handling.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
