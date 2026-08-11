"""
Predictive Signals Engine — orchestrator for all predictive signal sub-engines.

Computes and caches predictive_signals in base_charts.payload for a given month.
Follows the same lazy backfill pattern as upagraha_engine.py.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def compute_predictive_signals(
    payload: Dict[str, Any],
    chart_id: str,
    year: int,
    month: int,
) -> Dict[str, Any]:
    """
    Run all 7 predictive signal engines, persist to DB, and return the assembled dict.

    Args:
        payload: full base_chart payload dict.
        chart_id: base_charts.id (UUID string).
        year: prediction year.
        month: prediction month (1–12).

    Returns:
        predictive_signals dict written to payload['predictive_signals'].
    """
    from datetime import date

    reference_date = date(year, month, 15)  # mid-month anchor

    ephemeris = payload.get("ephemeris", {})
    birth_details = payload.get("birth_details", {})
    vimshottari = payload.get("dashas", {}).get("vimshottari", {})
    yogas_payload = payload.get("yogas", {})
    bav = payload.get("bhinnashtakavarga", {})
    ayanamsa = ephemeris.get("ayanamsa", "lahiri")

    signals: Dict[str, Any] = {"computed_for": f"{year}-{month:02d}"}

    # ── 1. Pratyantar Dasha ───────────────────────────────────────────────────
    try:
        from app.engines.pratyantar_dasha_engine import compute_pratyantar
        signals["dasha_precision"] = compute_pratyantar(vimshottari, reference_date)
    except Exception as e:
        logger.warning("pratyantar_dasha failed chart=%s: %s", chart_id, e)
        signals["dasha_precision"] = {}

    pratyantar = signals["dasha_precision"]
    md_lord = pratyantar.get("md_lord")
    ad_lord = pratyantar.get("ad_lord")
    pt_lord = (pratyantar.get("pratyantar") or {}).get("lord")

    # ── 2. Transit Hits ───────────────────────────────────────────────────────
    try:
        from app.engines.transit_hits_engine import compute_transit_hits
        signals["transit_hits"] = compute_transit_hits(
            ephemeris=ephemeris,
            reference_date=reference_date,
            ayanamsa=ayanamsa,
            window_days=45,
        )
    except Exception as e:
        logger.warning("transit_hits failed chart=%s: %s", chart_id, e)
        signals["transit_hits"] = []

    # ── 3. Yoga Activation ────────────────────────────────────────────────────
    try:
        from app.engines.yoga_activation_engine import compute_yoga_activation
        signals["active_yogas"] = compute_yoga_activation(
            yogas_payload=yogas_payload,
            md_lord=md_lord,
            ad_lord=ad_lord,
            pt_lord=pt_lord,
        )
    except Exception as e:
        logger.warning("yoga_activation failed chart=%s: %s", chart_id, e)
        signals["active_yogas"] = []

    # ── 4. Special Lagnas ─────────────────────────────────────────────────────
    try:
        from app.engines.special_lagnas_engine import compute_special_lagnas
        signals["special_lagnas"] = compute_special_lagnas(
            ephemeris=ephemeris,
            birth_details=birth_details,
            ayanamsa=ayanamsa,
        )
    except Exception as e:
        logger.warning("special_lagnas failed chart=%s: %s", chart_id, e)
        signals["special_lagnas"] = {}

    # ── 5. Varshaphal ─────────────────────────────────────────────────────────
    try:
        from app.engines.varshaphal_engine import compute_varshaphal
        signals["varshaphal"] = compute_varshaphal(
            ephemeris=ephemeris,
            birth_details=birth_details,
            year=year,
            ayanamsa=ayanamsa,
        )
    except Exception as e:
        logger.warning("varshaphal failed chart=%s: %s", chart_id, e)
        signals["varshaphal"] = {}

    # ── 6. Refined AV ─────────────────────────────────────────────────────────
    try:
        from app.engines.refined_av_engine import compute_refined_av
        signals["refined_av_scores"] = compute_refined_av(bav)
    except Exception as e:
        logger.warning("refined_av failed chart=%s: %s", chart_id, e)
        signals["refined_av_scores"] = {}

    # ── 7. Event Window Confluence ────────────────────────────────────────────
    try:
        from app.engines.event_window_engine import detect_confluence
        signals["event_windows"] = detect_confluence(
            pratyantar=pratyantar,
            transit_hits=signals["transit_hits"],
            active_yogas=signals["active_yogas"],
            varshaphal=signals["varshaphal"],
            refined_av=signals["refined_av_scores"],
            reference_date=reference_date,
            num_months=3,
        )
    except Exception as e:
        logger.warning("detect_confluence failed chart=%s: %s", chart_id, e)
        signals["event_windows"] = []

    # ── Persist to DB ─────────────────────────────────────────────────────────
    try:
        from app.db.postgres import get_conn
        with get_conn() as conn:
            conn.execute(
                "UPDATE base_charts SET payload = jsonb_set(payload, '{predictive_signals}', %s::jsonb) WHERE id = %s",
                (json.dumps(signals), chart_id),
            )
        logger.info("predictive_signals persisted chart=%s month=%d-%02d", chart_id, year, month)
    except Exception as e:
        logger.warning("Failed to persist predictive_signals chart=%s: %s", chart_id, e)

    return signals
