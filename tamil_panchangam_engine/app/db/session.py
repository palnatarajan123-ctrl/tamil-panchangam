"""
DB session adapter for FastAPI dependency injection.
"""
from app.db.postgres import get_conn


def get_db():
    """
    Yields a PostgreSQL connection.
    Compatible with FastAPI Depends().
    """
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
