import sqlite3
import json
from pprint import pprint

DB_PATH = "data/panchangam.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("\n📦 TABLE COUNTS")
for table in ["base_charts", "chart_artifacts"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {count}")

print("\n🧱 BASE CHART ROW")
row = conn.execute(
    "SELECT id, checksum, locked, engine_version, created_at FROM base_charts ORDER BY created_at DESC LIMIT 1"
).fetchone()

pprint(dict(row))

print("\n🧩 CHART ARTIFACTS")
artifacts = conn.execute(
    """
    SELECT chart_type, engine_version, created_at
    FROM chart_artifacts
    WHERE base_chart_id = ?
    """,
    (row["id"],),
).fetchall()

for a in artifacts:
    pprint(dict(a))

print("\n📄 SAMPLE ARTIFACT PAYLOAD (D1)")
d1 = conn.execute(
    """
    SELECT payload FROM chart_artifacts
    WHERE base_chart_id = ? AND chart_type = 'D1'
    """,
    (row["id"],),
).fetchone()

payload = json.loads(d1["payload"])
print("Keys:", payload.keys())

print("\n✅ DB verification complete")
