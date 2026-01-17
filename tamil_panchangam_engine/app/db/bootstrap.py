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

    con.execute("""
    CREATE TABLE IF NOT EXISTS weekly_predictions (
        id TEXT PRIMARY KEY,
        base_chart_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        week INTEGER NOT NULL,
        status TEXT NOT NULL,
        envelope JSON NOT NULL,
        synthesis JSON NOT NULL,
        interpretation JSON NOT NULL,
        engine_version TEXT NOT NULL,
        generated_at TIMESTAMP NOT NULL
        );
    """)

if __name__ == "__main__":
    bootstrap()
    print("✅ DuckDB schema initialized")
