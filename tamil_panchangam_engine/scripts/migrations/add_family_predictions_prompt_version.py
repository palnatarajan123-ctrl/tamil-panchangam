"""
Migration: add prompt_version column to family_predictions, backfill
existing rows.

family_predictions had no version-gating mechanism at all -- caching was
keyed solely on (group_id, year), so a prompt/context change (like the
addition of per-member yogas/upagraha/KP/predictive_signals context) would
silently keep serving stale cached rows for any group with an existing
prediction that year, with no way to detect or exclude them. See
app/engines/family_prediction_engine.py's PROMPT_VERSION for the full
reasoning.

Also idempotently applied via app/db/bootstrap.py at app startup (same
pattern as family_groups.primary_chart_id) -- this script exists to run
once, immediately, and to backfill existing rows, which bootstrap.py's
generic ADD COLUMN IF NOT EXISTS does not do.

Run once against production PostgreSQL:
    cd tamil_panchangam_engine
    python scripts/migrations/add_family_predictions_prompt_version.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.postgres import get_conn

# All 3 rows that existed when this migration was written were regenerated
# earlier the same day (today's Phase 1 fix), using exactly the prompt
# content that PROMPT_VERSION = "family_v2.0" identifies -- this is the
# true, correct value for them, not a placeholder.
BACKFILL_VERSION = "family_v2.0"


def run():
    with get_conn() as conn:
        conn.execute(
            "ALTER TABLE family_predictions ADD COLUMN IF NOT EXISTS prompt_version TEXT"
        )

        before = conn.execute(
            "SELECT group_id, year FROM family_predictions WHERE prompt_version IS NULL"
        ).fetchall()
        print(f"Rows with no prompt_version before backfill: {len(before)}")
        for group_id, year in before:
            print(f"  {group_id} / {year}")

        conn.execute(
            "UPDATE family_predictions SET prompt_version = %s WHERE prompt_version IS NULL",
            (BACKFILL_VERSION,),
        )

        after = conn.execute(
            "SELECT group_id, year, prompt_version FROM family_predictions ORDER BY group_id"
        ).fetchall()
        print(f"\nAll rows after backfill ({len(after)}):")
        for group_id, year, prompt_version in after:
            print(f"  {group_id} / {year} -> {prompt_version}")

    print("\nMigration complete: prompt_version added and backfilled on family_predictions")


if __name__ == "__main__":
    run()
