import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from models.base import Base


# =========================================================
# Configuration
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Please define it in your environment variables."
    )


# =========================================================
# SQLAlchemy Engine
# =========================================================

engine: Engine = create_engine(
    DATABASE_URL,

    # Detect and discard stale connections.
    pool_pre_ping=True,

    # Connection pool configuration.
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,

    # Keep SQL logging disabled by default.
    echo=False,
)


# =========================================================
# Session Factory
# =========================================================

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


# =========================================================
# Database Session Dependency
# =========================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session.

    Intended for API endpoints and other components
    that need temporary access to PostgreSQL.

    The caller is responsible for committing transactions.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================================================
# Transaction Context Manager
# =========================================================

@contextmanager
def session_scope():
    """
    Provides a session with automatic transaction handling.

    - Commits when the operation succeeds.
    - Rolls back when an exception occurs.
    - Always closes the session.
    """

    db = SessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =========================================================
# Connection Check
# =========================================================

def check_database_connection() -> bool:
    """
    Checks whether PostgreSQL is reachable.

    Returns:
        True if the connection succeeds.
        False otherwise.
    """

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception as error:
        print(f"Database connection failed: {error}")
        return False


# =========================================================
# Engine Shutdown
# =========================================================

def dispose_database_engine() -> None:
    """
    Closes all pooled connections.

    Useful during application shutdown.
    """

    engine.dispose()