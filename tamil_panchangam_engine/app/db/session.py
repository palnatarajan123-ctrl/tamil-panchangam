"""
DuckDB-compatible DB session adapter.

This preserves the historical get_db() contract
used by FastAPI dependency injection.
"""

from app.db.duckdb import get_conn


def get_db():
    """
    Yields a DuckDB connection.
    Compatible with FastAPI Depends().
    """
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
