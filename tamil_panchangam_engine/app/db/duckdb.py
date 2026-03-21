"""
DB connection — now powered by Neon PostgreSQL.
Kept as duckdb.py for backward compatibility with all existing imports.
"""
from app.db.postgres import get_conn  # noqa: F401

__all__ = ["get_conn"]
