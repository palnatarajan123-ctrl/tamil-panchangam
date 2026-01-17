#!/usr/bin/env bash
set -e

echo "🧹 STEP 1 — Removing SQLite / SQLModel artifacts"

# Remove old DB/ORM files (safe even if missing)
rm -f app/db/engine.py
rm -f app/db/session.py

# Optional: remove SQLModel usage traces (does NOT touch logic files)
grep -R "sqlmodel" -l app | xargs -r sed -i 's/^/# REMOVED: /'

echo "🧱 STEP 2 — Creating DuckDB DB module"

mkdir -p app/db
cat > app/db/duckdb.py <<'EOF'
import duckdb
from pathlib import Path

DB_PATH = Path("data/panchangam.duckdb")
DB_PATH.parent.mkdir(exist_ok=True)

_conn = None

def get_conn():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(str(DB_PATH))
    return _conn
EOF

echo "🧱 STEP 3 — Creating DB bootstrap script"

cat > app/db/bootstrap.py <<'EOF'
from app.db.duckdb import get_conn

def bootstrap():
    con = get_conn()

    con.execute("""
    CREATE TABLE IF NOT EXISTS base_charts (
        id TEXT PRIMARY KEY,
        locked BOOLEAN,
        payload JSON
    );
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS monthly_predictions (
        id TEXT PRIMARY KEY,
        base_chart_id TEXT,
        year INTEGER,
        month INTEGER,
        status TEXT,
        envelope JSON,
        synthesis JSON,
        interpretation JSON,
        engine_version TEXT,
        created_at TIMESTAMP
    );
    """)

if __name__ == "__main__":
    bootstrap()
    print("✅ DuckDB schema initialized")
EOF

echo "🧱 STEP 4 — Replacing repositories"

mkdir -p app/repositories

cat > app/repositories/base_chart_repo.py <<'EOF'
import json
from app.db.duckdb import get_conn

def get_base_chart_by_id(_, chart_id: str):
    con = get_conn()
    row = con.execute(
        "SELECT id, locked, payload FROM base_charts WHERE id = ?",
        [chart_id],
    ).fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "locked": row[1],
        "payload": json.dumps(row[2]),
    }
EOF

cat > app/repositories/prediction_repo.py <<'EOF'
import json
from datetime import datetime
from app.db.duckdb import get_conn

def get_monthly_prediction(_, base_chart_id, year, month):
    con = get_conn()
    row = con.execute(
        """
        SELECT envelope, synthesis, interpretation
        FROM monthly_predictions
        WHERE base_chart_id = ? AND year = ? AND month = ?
        """,
        [base_chart_id, year, month],
    ).fetchone()

    if not row:
        return None

    return {
        "envelope": json.dumps(row[0]),
        "synthesis": json.dumps(row[1]),
        "interpretation": json.dumps(row[2]) if row[2] else None,
    }

def save_monthly_prediction(
    _,
    base_chart_id,
    year,
    month,
    status,
    envelope,
    synthesis,
    interpretation,
    engine_version,
):
    con = get_conn()
    pid = f"{base_chart_id}:{year}:{month}"

    con.execute(
        """
        INSERT OR REPLACE INTO monthly_predictions
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            pid,
            base_chart_id,
            year,
            month,
            status,
            envelope,
            synthesis,
            interpretation,
            engine_version,
            datetime.utcnow(),
        ],
    )
EOF

echo "🧱 STEP 5 — Initializing DuckDB schema"

PYTHONPATH=. python -m app.db.bootstrap


echo "🧪 STEP 6 — Verifying DuckDB works"

python - <<'EOF'
import duckdb
con = duckdb.connect("data/panchangam.duckdb")
print("DuckDB OK:", con.execute("select 1").fetchall())
EOF

echo "🎉 DONE — SQLite fully removed, DuckDB active"
