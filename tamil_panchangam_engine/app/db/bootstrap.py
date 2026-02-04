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

    con.execute("""
    CREATE TABLE IF NOT EXISTS prediction_llm_interpretation (
        id TEXT PRIMARY KEY,
        base_chart_id TEXT NOT NULL,
        period_type TEXT NOT NULL,
        period_key TEXT NOT NULL,
        feature_name TEXT NOT NULL,
        provider TEXT,
        model TEXT,
        prompt_version TEXT NOT NULL,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        content_json JSON,
        fallback_reason TEXT,
        reflection_text TEXT,
        created_at TIMESTAMP NOT NULL
    );
    """)
    
    # Add reflection_text column if missing (for existing tables)
    try:
        con.execute("""
            ALTER TABLE prediction_llm_interpretation 
            ADD COLUMN IF NOT EXISTS reflection_text TEXT;
        """)
    except Exception:
        pass  # Column already exists or DB doesn't support IF NOT EXISTS
    
    # v1.9: Add explainability_mode column for cache key differentiation
    try:
        con.execute("""
            ALTER TABLE prediction_llm_interpretation 
            ADD COLUMN IF NOT EXISTS explainability_mode TEXT;
        """)
    except Exception:
        pass  # Column already exists

    con.execute("""
    CREATE TABLE IF NOT EXISTS llm_token_usage (
        id TEXT PRIMARY KEY,
        feature_name TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        total_tokens INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS llm_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );
    """)

    con.execute("""
    INSERT INTO llm_config (key, value, updated_at) 
    VALUES ('llm_enabled', 'true', CURRENT_TIMESTAMP)
    ON CONFLICT (key) DO NOTHING;
    """)

if __name__ == "__main__":
    bootstrap()
    print("✅ DuckDB schema initialized")
