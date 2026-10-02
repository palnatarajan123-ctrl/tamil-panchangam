#!/usr/bin/env python3
"""
One-off backfill (run 2026-10-02): recompute the stored
payload['bhinnashtakavarga'] for every chart that has one, after
bhinnashtakavarga_engine.BAV_TABLES was corrected to the classical tables
(commits 8e2edca + 08c69c1). The table is written once at chart creation,
so the code fix alone didn't reach existing charts.

Deterministic, no LLM. Dry run by default: prints every transit_scores
change (old -> new, with labels) and writes a JSON backup of the current
values. Pass --apply to write.

Usage:
    cd tamil_panchangam_engine
    python ../scripts/backfill_bav_classical_tables.py [--apply]
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine", ".env"))

from app.db.postgres import get_conn
from app.engines.bhinnashtakavarga_engine import PLANET_KEYS, compute_bhinnashtakavarga

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backfill_backups")


def main(apply: bool) -> None:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, payload->'bhinnashtakavarga' AS bav, payload->'ephemeris' AS eph "
            "FROM base_charts WHERE payload->'bhinnashtakavarga' IS NOT NULL"
        ).fetchall()

    backup, updates = {}, []
    for chart_id, stored, eph in rows:
        if not stored or "error" in stored:
            continue
        new = compute_bhinnashtakavarga(eph)
        if new == stored:
            continue
        backup[str(chart_id)] = stored
        updates.append((json.dumps(new), str(chart_id)))
        totals = {p: (stored[p]["total"], new[p]["total"]) for p in PLANET_KEYS if stored[p]["total"] != new[p]["total"]}
        print(f"{str(chart_id)[:8]} totals {totals}")
        for planet in ("saturn", "jupiter", "rahu"):
            a = stored.get("transit_scores", {}).get(planet) or {}
            b = (new.get("transit_scores") or {}).get(planet) or {}
            label = "strength" if planet == "rahu" else "combined_strength"
            if a != b:
                print(f"    {planet:7s} BAV {a.get('bav_score')}->{b.get('bav_score')} "
                      f"SAV {a.get('sav_score')}->{b.get('sav_score')} {a.get(label)}->{b.get(label)}")

    print(f"{len(updates)} of {len(rows)} stored tables differ from the classical recompute")
    if not apply or not updates:
        print("dry run -- pass --apply to write")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, "bhinnashtakavarga_pre_classical_tables.json")
    with open(path, "w") as f:
        json.dump(backup, f)
    with get_conn() as conn:
        for new_json, chart_id in updates:
            conn.execute(
                "UPDATE base_charts SET payload = jsonb_set(payload, '{bhinnashtakavarga}', %s::jsonb) WHERE id = %s",
                (new_json, chart_id),
            )
    print(f"wrote {len(updates)} charts; backup at {path}")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
