import sqlite3
from pathlib import Path

DB_PATH = Path("data/panchangam.db")
SCHEMA_PATH = Path("scripts/schema.sql")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DB_PATH) as conn:
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()

print("✅ Database initialized at", DB_PATH.resolve())
