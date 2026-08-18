"""Migration: Add porutham_prospects table (Phase G1, chart-to-chart
compatibility links, independent of family_groups).

Also idempotently applied via app/db/bootstrap.py at app startup (same
pattern as family_porutham_cache) -- this script exists to run once
immediately against an existing production DB.

Run once against production PostgreSQL:
    cd tamil_panchangam_engine
    python scripts/migrations/add_porutham_prospects.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.postgres import get_conn

def run():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS porutham_prospects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_chart_id TEXT NOT NULL REFERENCES base_charts(id) ON DELETE CASCADE,
                candidate_chart_id TEXT NOT NULL REFERENCES base_charts(id) ON DELETE CASCADE,
                source_role TEXT NOT NULL CHECK (source_role IN ('boy', 'girl')),
                result_json JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_porutham_prospects_user
                ON porutham_prospects(user_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_porutham_prospects_source
                ON porutham_prospects(source_chart_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_porutham_prospects_candidate
                ON porutham_prospects(candidate_chart_id)
        """)
        conn.commit()
        print("Migration complete: porutham_prospects created")

if __name__ == "__main__":
    run()
