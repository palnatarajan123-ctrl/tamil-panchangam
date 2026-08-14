#!/usr/bin/env python3
"""
One-off recompute: fix base_charts.payload->'upagrahas' for charts whose
Gulika (Mandi) was computed under the pre-fix segment tables.

Context: _YAMA_SEGMENT / _GULIKA_SEGMENT (dinaphalam_engine.py) and
_MANDI_DAYTIME_SEGMENT (upagraha_engine.py) were each off by one weekday —
every chart's Gulika was computed from the PREVIOUS day's segment. Fixed in
the commit that added tests/engines/test_dinaphalam_engine.py and
test_upagraha_engine.py. This script does NOT touch prediction_llm_interpretation
(confirmed 0 natal_v2.2 rows exist, so no natal cache entanglement here) —
that table's staleness, if any, is a separate scoped step.

Scope: NOT every chart with upagrahas — only charts whose STORED Gulika
longitude disagrees with what the current (fixed) compute_gulika_mandi()
produces for the same birth data. This is ground truth, not a timestamp
guess: base_charts has no created_at column, so a commit-window heuristic
isn't even available here.

Guardrails:
1. Backs up payload->'upagrahas' for every affected chart to a JSON file
   before writing anything, as a rollback path.
2. All UPDATEs run inside a single DB transaction; verifies total rowcount
   affected == the number of charts identified, and rolls back (raises
   inside the `with get_conn()` block, which _ConnWrapper.__exit__ turns
   into a rollback) if it doesn't match.
3. After commit, re-runs the same diff check fresh from the DB and confirms
   zero charts still mismatch — verification, not an assumption that the
   UPDATE "ran clean".

Usage:
    cd tamil_panchangam_engine
    python ../scripts/backfill_gulika_segment_fix.py
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine", ".env"))

from app.db.postgres import get_conn
from app.engines.upagraha_engine import compute_gulika_mandi

LON_TOLERANCE_DEG = 0.01
BACKUP_DIR = Path(__file__).parent / "backfill_backups"


def _load_payload(raw):
    return raw if isinstance(raw, dict) else json.loads(raw or "{}")


def _recompute_gulika(payload: dict):
    """Returns the fresh {"gulika": ..., "mandi": ...} dict, or None if this
    chart lacks the birth data needed to compute it."""
    birth_details = payload.get("birth_details", {})
    birth_utc_str = payload.get("birth_utc", "")
    if not birth_utc_str or not birth_details:
        return None
    birth_utc = datetime.fromisoformat(birth_utc_str.replace("Z", "+00:00"))
    return compute_gulika_mandi(
        birth_utc=birth_utc,
        latitude=birth_details.get("latitude", 0.0),
        longitude=birth_details.get("longitude", 0.0),
        ayanamsa=payload.get("ephemeris", {}).get("ayanamsa", "lahiri"),
    )


def _find_mismatches(rows):
    """Ground-truth scoping: recompute vs. stored, diff on longitude_deg.
    Returns (mismatches: list[(chart_id, stored_upagrahas, fresh_upagrahas)],
             no_data_count: int, error_count: int)."""
    mismatches = []
    no_data = 0
    errors = 0

    for chart_id, payload_raw in rows:
        payload = _load_payload(payload_raw)
        stored_upa = payload.get("upagrahas", {})
        stored_gulika = stored_upa.get("gulika", {}) if isinstance(stored_upa, dict) else {}

        if not stored_gulika or not stored_gulika.get("rasi"):
            no_data += 1  # out of scope -- lazy-backfill-on-read already handles these
            continue

        try:
            fresh = _recompute_gulika(payload)
        except Exception as e:
            logger.error(f"{chart_id}: recompute failed — {e}")
            errors += 1
            continue

        if fresh is None:
            logger.warning(f"{chart_id}: has Gulika data but missing birth_utc/birth_details for recompute — skip")
            errors += 1
            continue

        stored_lon = stored_gulika.get("longitude_deg")
        fresh_lon = fresh.get("gulika", {}).get("longitude_deg")
        if stored_lon is None or fresh_lon is None or abs(stored_lon - fresh_lon) > LON_TOLERANCE_DEG:
            mismatches.append((chart_id, stored_upa, fresh))

    return mismatches, no_data, errors


def main():
    with get_conn() as conn:
        rows = conn.execute("SELECT id, payload FROM base_charts").fetchall()
    logger.info(f"Fetched {len(rows)} base_charts")

    mismatches, no_data, errors = _find_mismatches(rows)
    logger.info(f"Charts with no Gulika data (out of scope): {no_data}")
    logger.info(f"Charts with recompute errors (skipped): {errors}")
    logger.info(f"Charts needing recompute: {len(mismatches)}")

    if not mismatches:
        logger.info("Nothing to do.")
        return

    # ── Step 1: backup before writing anything ─────────────────────────────
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / f"gulika_segment_fix_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    backup_data = {chart_id: stored_upa for chart_id, stored_upa, _fresh in mismatches}
    with open(backup_path, "w") as f:
        json.dump(backup_data, f, indent=2, default=str)
    logger.info(f"Backed up pre-update upagrahas for {len(backup_data)} charts to {backup_path}")

    # ── Step 2: transactional update, verify rowcount before commit ────────
    expected = len(mismatches)
    with get_conn() as conn:
        total_rowcount = 0
        for chart_id, _stored_upa, fresh in mismatches:
            conn.execute(
                "UPDATE base_charts SET payload = payload || %s::jsonb WHERE id = %s",
                (json.dumps({"upagrahas": fresh}), chart_id),
            )
            total_rowcount += conn._cur.rowcount

        logger.info(f"UPDATE affected {total_rowcount} row(s); expected {expected}")
        if total_rowcount != expected:
            raise RuntimeError(
                f"Row count mismatch ({total_rowcount} != {expected}) — "
                f"aborting without commit. Backup is at {backup_path}."
            )
    # `with get_conn()` commits here on clean exit (or rolled back above via
    # the raised exception, per _ConnWrapper.__exit__).
    logger.info("Transaction committed.")

    # ── Step 3: post-update verification — don't just trust the UPDATE ─────
    with get_conn() as conn:
        rows_after = conn.execute("SELECT id, payload FROM base_charts").fetchall()
    still_mismatched, _no_data_after, errors_after = _find_mismatches(rows_after)

    if still_mismatched:
        logger.error(
            f"VERIFICATION FAILED: {len(still_mismatched)} chart(s) still mismatch "
            f"after update: {[c for c, _, _ in still_mismatched]}"
        )
        sys.exit(1)

    logger.info(f"Verification passed: 0 charts mismatch post-update "
                f"(recompute errors during verification, if any: {errors_after}).")
    logger.info(f"Done. Recomputed {expected} chart(s). Backup: {backup_path}")


if __name__ == "__main__":
    main()
