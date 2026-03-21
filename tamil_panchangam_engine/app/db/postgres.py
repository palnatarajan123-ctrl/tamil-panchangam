"""
PostgreSQL connection via Neon.
Replaces duckdb.py as the single source of truth for DB connections.
"""
import os
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

def _get_database_url():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        from pathlib import Path
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    os.environ["DATABASE_URL"] = url
                    break
    return url


class _ConnWrapper:
    def __init__(self, conn):
        self._conn = conn
        self._cur = conn.cursor()
        self.description = None

    def execute(self, sql, params=None):
        sql = sql.replace("?", "%s")
        sql = sql.replace("INSERT OR REPLACE INTO", "INSERT INTO")
        sql = sql.replace("CURRENT_TIMESTAMP", "NOW()")
        if params:
            self._cur.execute(sql, params)
        else:
            self._cur.execute(sql)
        self.description = self._cur.description
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if hasattr(row, 'values'):
            return tuple(row.values())
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        return [tuple(r.values()) if hasattr(r, 'values') else r
                for r in rows]

    def commit(self):
        self._conn.commit()

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self._conn.rollback()
            except Exception:
                pass
        else:
            try:
                self._conn.commit()
            except Exception:
                pass
        self.close()


def get_conn():
    url = _get_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    conn = psycopg2.connect(
        url,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return _ConnWrapper(conn)
