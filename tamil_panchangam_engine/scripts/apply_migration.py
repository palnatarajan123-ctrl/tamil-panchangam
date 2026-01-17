import sqlite3
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python scripts/apply_migration.py <migration.sql>")
    sys.exit(1)

db_path = Path("data/panchangam.db")
sql_path = Path(sys.argv[1])

if not db_path.exists():
    raise FileNotFoundError(f"DB not found: {db_path}")

if not sql_path.exists():
    raise FileNotFoundError(f"SQL not found: {sql_path}")

conn = sqlite3.connect(db_path)
conn.executescript(sql_path.read_text())
conn.commit()
conn.close()

print(f"✅ Applied migration: {sql_path.name}")
