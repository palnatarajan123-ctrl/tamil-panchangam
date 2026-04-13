"""
Migration: add summary column to family_timeline_cache
Run once against production PostgreSQL.
"""
import os
import psycopg2

def run():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE family_timeline_cache
        ADD COLUMN IF NOT EXISTS summary TEXT
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete: summary column added to family_timeline_cache")

if __name__ == "__main__":
    run()
