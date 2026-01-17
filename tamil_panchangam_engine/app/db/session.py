"""
DuckDB-compatible DB session adapter.

This preserves the historical get_db() contract
used by FastAPI dependency injection.
"""

from contextlib import contextmanager
from app.db.duckdb import get_conn


@contextmanager
def get_db():
    """
    Yields a DuckDB connection.
    Matches previous SQLModel get_db() signature.
    """
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
