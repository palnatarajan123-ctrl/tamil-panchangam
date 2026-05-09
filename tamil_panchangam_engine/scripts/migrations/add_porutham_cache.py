"""Migration: Add family_porutham_cache table."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.postgres import get_conn

def run():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_porutham_cache (
                id SERIAL PRIMARY KEY,
                group_id TEXT NOT NULL,
                member_id_1 TEXT NOT NULL,
                member_id_2 TEXT NOT NULL,
                result_json JSONB NOT NULL,
                computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(group_id, member_id_1, member_id_2)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_porutham_cache_group
                ON family_porutham_cache(group_id)
        """)
        conn.commit()
        print("Migration complete: family_porutham_cache created")

if __name__ == "__main__":
    run()
