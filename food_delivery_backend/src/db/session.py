from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings

_ENGINE = None
_SessionLocal: Optional[sessionmaker] = None


# PUBLIC_INTERFACE
def init_engine() -> None:
    """Initialize the SQLAlchemy engine and session factory from environment settings."""
    global _ENGINE, _SessionLocal
    settings = get_settings()
    if not settings.database_url:
        # Engine is left uninitialized; endpoints relying on DB will raise a clear error.
        _ENGINE = None
        _SessionLocal = None
        return

    _ENGINE = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_ENGINE, future=True)


# PUBLIC_INTERFACE
def get_engine():
    """Return the initialized SQLAlchemy engine (or None if not configured)."""
    return _ENGINE


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    if _SessionLocal is None:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL or POSTGRES_* env vars and restart."
        )
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context-managed DB session for scripts/CLI usage."""
    if _SessionLocal is None:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL or POSTGRES_* env vars and restart."
        )
    db: Session = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
