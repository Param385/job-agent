"""
Database connection utilities.

Creates the SQLAlchemy engine and session factory from the project config.
Call :func:`init_db` once at startup to create all tables.

Usage::

    from src.database.connection import get_session, init_db

    init_db()
    with get_session() as session:
        # use session ...
"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import config
from src.database.models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine – shared across the entire process
# ---------------------------------------------------------------------------
engine = create_engine(
    config.database_url,
    # Only relevant for SQLite; prevents "Objects created in a thread can only
    # be used in that same thread" errors in tests / multi-threaded use.
    connect_args={"check_same_thread": False}
    if config.database_url.startswith("sqlite")
    else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create all database tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised at %s", config.database_url)


@contextmanager
def get_session():
    """Context manager that provides a transactional database session.

    Automatically commits on success and rolls back on any exception::

        with get_session() as session:
            session.add(some_object)
            # commit happens automatically on exit
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
