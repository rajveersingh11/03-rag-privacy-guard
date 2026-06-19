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
            "mysql+pymysql://aegis:aegis@localhost:3306/aegisdb"
        )
        kwargs = {
            "pool_recycle": 3600,
            "pool_pre_ping": True,   # auto-reconnect on stale connections
            "echo": False,
        }
        if not db_url.startswith("sqlite"):
            pool_size = int(os.environ.get("DATABASE_POOL_SIZE", "10"))
            max_overflow = int(os.environ.get("DATABASE_MAX_OVERFLOW", "5"))
            kwargs["pool_size"] = pool_size
            kwargs["max_overflow"] = max_overflow
            
        _engine = create_engine(db_url, **kwargs)
        logger.info(f"DB engine created")
    return _engine



def init_db():
    """Create all tables. Called on app startup."""
    global SessionLocal
    engine = _get_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    
    # Programmatically ensure users table exists for admin authentication
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id            VARCHAR(36)   PRIMARY KEY,
                    username      VARCHAR(255)  UNIQUE NOT NULL,
                    password_hash VARCHAR(255)  NOT NULL,
                    role          VARCHAR(50)   NOT NULL DEFAULT 'admin',
                    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            logger.info("Users table verified/created")
    except Exception as e:
        logger.error(f"Failed to create users table: {e}")
        
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