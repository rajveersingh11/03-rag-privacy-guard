"""
DB Session
----------
SQLAlchemy engine + session factory.
Reads DATABASE_URL from environment (set via .env or docker-compose).
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from aegisVault.utils.common import get_logger

logger = get_logger(__name__)

Base = declarative_base()

_engine = None
SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://aegis:aegis@localhost:5432/aegisdb"
        )
        _engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,   # auto-reconnect on stale connections
            echo=False,
        )
        logger.info(f"DB engine created")
    return _engine


def init_db():
    """Create all tables. Called on app startup."""
    global SessionLocal
    engine = _get_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    logger.info("Database initialised")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session per request."""
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for use outside FastAPI (scripts, workers)."""
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def health_check() -> bool:
    """Returns True if database is reachable."""
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False