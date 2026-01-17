# app/db/duckdb.py

import duckdb
from pathlib import Path

# 🔒 SINGLE SOURCE OF TRUTH
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "panchangam.duckdb"

def get_conn():
    """
    Returns a DuckDB connection to the ONE canonical database file.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))
