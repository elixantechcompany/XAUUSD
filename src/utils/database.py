"""
SQLAlchemy engine + session factory + declarative Base.

All models import Base from here.
Call init_db() once at application startup to create tables.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine(db_path: Path | str | None = None):
    global _engine
    if _engine is None:
        if db_path is None:
            from src.config.settings import get_settings
            db_path = get_settings().db_path
        url = f"sqlite:///{db_path}"
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Enable WAL mode for better concurrent reads
        @event.listens_for(_engine, "connect")
        def set_wal(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return _engine


def get_session_factory(db_path: Path | str | None = None) -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(db_path)
        _SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Session:
    """FastAPI dependency — yields a session and always closes it."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Create all tables if they do not exist."""
    engine = get_engine(db_path)
    # Import models so their metadata is registered
    import src.state.models       # noqa: F401  (includes DecisionLog)
    import src.journal.models     # noqa: F401
    import src.api.models         # noqa: F401
    Base.metadata.create_all(bind=engine)


def reset_db_for_tests(db_path: Path | str = ":memory:") -> None:
    """Wipe and recreate all tables — only for test use."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
    get_engine(db_path)
    init_db(db_path)
