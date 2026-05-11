#!/usr/bin/env python3
"""
One-off backfill: compute and persist upagrahas for all base_charts where
payload->'upagrahas' IS NULL (charts created before v2.0).

Usage:
    cd tamil_panchangam_engine
    python ../scripts/backfill_upagrahas.py
"""

import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine", ".env"))

from datetime import datetime
from app.db.postgres import get_conn
from app.engines.upagraha_engine import compute_gulika_mandi


def main():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, payload
            FROM base_charts
            WHERE payload->'upagrahas' IS NULL
            ORDER BY id
            """
        ).fetchall()

    total = len(rows)
    if total == 0:
        logger.info("No charts missing upagrahas — nothing to backfill.")
        return

    logger.info(f"Found {total} chart(s) missing upagrahas. Starting backfill…")

    ok = 0
    failed = 0

    for i, (chart_id, payload_raw) in enumerate(rows, 1):
        payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
        birth_utc_str = payload.get("birth_utc", "")
        birth_details = payload.get("birth_details", {})
        ayanamsa = payload.get("ephemeris", {}).get("ayanamsa", "lahiri")

        if not birth_utc_str or not birth_details:
            logger.warning(f"[{i}/{total}] {chart_id}: missing birth_utc or birth_details — skip")
            failed += 1
            continue

        try:
            birth_utc = datetime.fromisoformat(birth_utc_str.replace("Z", "+00:00"))
            result = compute_gulika_mandi(
                birth_utc=birth_utc,
                latitude=birth_details.get("latitude", 0.0),
                longitude=birth_details.get("longitude", 0.0),
                ayanamsa=ayanamsa,
            )
            with get_conn() as conn:
                conn.execute(
                    "UPDATE base_charts SET payload = payload || %s::jsonb WHERE id = %s",
                    (json.dumps({"upagrahas": result}), chart_id),
                )
            logger.info(f"[{i}/{total}] {chart_id}: backfilled OK — gulika={result['gulika']['rasi']}")
            ok += 1
        except Exception as e:
            logger.error(f"[{i}/{total}] {chart_id}: FAILED — {e}")
            failed += 1

    logger.info(f"Done. Backfilled {ok}/{total} charts. Failed: {failed}.")


if __name__ == "__main__":
    main()
