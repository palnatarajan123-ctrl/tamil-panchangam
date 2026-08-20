#!/usr/bin/env python3
"""
One-off: recompute full chart payload for a single chart whose birth time was
corrected directly in Neon without re-running the ephemeris engine.

Usage:
    cd tamil_panchangam_engine
    python ../scripts/recompute_chart.py
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

CHART_ID = "fd79efb3-87e8-4533-bec3-0c3d5396ce53"

from app.db.postgres import get_conn
from app.engines.ephemeris import compute_sidereal_positions
from app.engines.panchangam import compute_panchangam
from app.engines.dasha_vimshottari import compute_vimshottari_dasha
from app.engines.pancha_pakshi import get_birth_pakshi
from app.engines.navamsa_engine import build_navamsa_chart
from app.engines.divisional_charts import (
    build_hora_chart,
    build_saptamsa_chart,
    build_navamsa_chart as build_d9_chart,
    build_dasamsa_chart,
)
from app.engines.functional_role_engine import compute_functional_roles
from app.engines.yoga_engine import compute_yogas
from app.engines.shadbala_engine import compute_shadbala
from app.engines.bhinnashtakavarga_engine import compute_bhinnashtakavarga
from app.engines.upagraha_engine import compute_gulika_mandi
from app.utils.time_utils import normalize_birth_time_to_utc
from app.utils.checksum import compute_chart_checksum


def main():
    # ── Load existing payload ─────────────────────────────────────────────────
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload FROM base_charts WHERE id = %s",
            (CHART_ID,),
        ).fetchone()

    if not row:
        logger.error(f"Chart {CHART_ID} not found in DB")
        sys.exit(1)

    payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])

    birth = payload["birth_details"]
    meta  = payload.get("chart_metadata", {})

    date_of_birth = birth["date_of_birth"]        # e.g. "1990-01-15"
    time_of_birth = birth["time_of_birth"]        # already updated: "11:21:00"
    latitude      = birth["latitude"]
    longitude     = birth["longitude"]
    timezone_str  = birth["timezone"]
    ayanamsa      = meta.get("ayanamsa", "lahiri")
    node_type     = meta.get("node_type", "mean")

    # ── Before state ─────────────────────────────────────────────────────────
    old_eph  = payload.get("ephemeris", {})
    old_moon = old_eph.get("moon", {})
    print("\n── BEFORE ───────────────────────────────────────────────────────")
    print(f"  time_of_birth : {birth.get('time_of_birth')}")
    print(f"  Moon longitude: {old_moon.get('longitude_deg')}")
    print(f"  Moon rasi     : {old_moon.get('rasi')}")
    nak = old_moon.get("nakshatra", {})
    print(f"  Moon nakshatra: {nak.get('name') if isinstance(nak, dict) else nak}")

    # ── Recompute ─────────────────────────────────────────────────────────────
    birth_utc = normalize_birth_time_to_utc(
        birth_date=date_of_birth,
        birth_time=time_of_birth,
        latitude=latitude,
        longitude=longitude,
        timezone_str=timezone_str,
    )
    logger.info(f"birth_utc = {birth_utc.isoformat()}")

    ephemeris = compute_sidereal_positions(
        birth_utc, latitude, longitude,
        node_type=node_type, ayanamsa=ayanamsa,
    )

    panchangam = compute_panchangam(
        dt_local=birth_utc,
        sun_lon=ephemeris["planets"]["Sun"]["longitude_deg"],
        moon_lon=ephemeris["moon"]["longitude_deg"],
        nakshatra=ephemeris["moon"]["nakshatra"],
    )

    dasha = compute_vimshottari_dasha(
        birth_datetime_utc=birth_utc,
        moon_longitude=ephemeris["moon"]["longitude_deg"],
        nakshatra_index=ephemeris["moon"]["nakshatra"]["index"],
    )

    try:
        pakshi = get_birth_pakshi(ephemeris["moon"]["nakshatra"]["name"])
    except Exception as e:
        logger.warning(f"Pakshi failed: {e}")
        pakshi = payload.get("pancha_pakshi_birth", {})

    navamsa_legacy = build_navamsa_chart(ephemeris)
    d2_hora        = build_hora_chart(ephemeris)
    d7_saptamsa    = build_saptamsa_chart(ephemeris)
    d9_navamsa     = build_d9_chart(ephemeris)
    d10_dasamsa    = build_dasamsa_chart(ephemeris)

    functional_roles = compute_functional_roles(ephemeris=ephemeris, houses={})

    try:
        yoga_result = compute_yogas(ephemeris, {})
    except Exception as e:
        logger.warning(f"Yoga failed: {e}")
        yoga_result = payload.get("yogas", {"yogas": [], "summary": {}})

    try:
        shadbala_natal = compute_shadbala(
            ephemeris.get("planets", {}),
            ephemeris.get("lagna", {}).get("longitude_deg", 0.0),
        )
    except Exception as e:
        logger.warning(f"Shadbala failed: {e}")
        shadbala_natal = payload.get("shadbala_natal", {})

    try:
        bav_result = compute_bhinnashtakavarga(ephemeris)
    except Exception as e:
        logger.warning(f"BAV failed: {e}")
        bav_result = payload.get("bhinnashtakavarga", {"error": str(e)})

    try:
        upagraha_result = compute_gulika_mandi(
            birth_utc=birth_utc,
            latitude=latitude,
            longitude=longitude,
            ayanamsa=ayanamsa,
        )
    except Exception as e:
        logger.warning(f"Upagraha failed: {e}")
        upagraha_result = payload.get("upagrahas", {"error": str(e)})

    # ── Assemble new payload (keep static fields, replace computed fields) ────
    new_payload = {
        **payload,                      # keeps name, place, user_id, etc.
        "birth_utc": birth_utc.isoformat(),
        "ephemeris": ephemeris,
        "panchangam_birth": panchangam,
        "charts": {"D9": navamsa_legacy},
        "divisional_charts": {
            "D2": d2_hora,
            "D7": d7_saptamsa,
            "D9": d9_navamsa,
            "D10": d10_dasamsa,
        },
        "chart_metadata": {
            **meta,
            "ayanamsa": ayanamsa,
            "node_type": node_type,
        },
        "dashas": {"vimshottari": dasha},
        "pancha_pakshi_birth": pakshi,
        "functional_roles": functional_roles,
        "yogas": yoga_result,
        "shadbala_natal": shadbala_natal,
        "bhinnashtakavarga": bav_result,
        "upagrahas": upagraha_result,
    }

    # ── Persist ───────────────────────────────────────────────────────────────
    with get_conn() as conn:
        conn.execute(
            "UPDATE base_charts SET payload = %s::jsonb WHERE id = %s",
            (json.dumps(new_payload), CHART_ID),
        )
    logger.info("DB updated.")

    # ── After state ───────────────────────────────────────────────────────────
    new_moon = ephemeris["moon"]
    new_nak  = new_moon.get("nakshatra", {})
    print("\n── AFTER ────────────────────────────────────────────────────────")
    print(f"  time_of_birth : {time_of_birth}")
    print(f"  Moon longitude: {new_moon.get('longitude_deg')}")
    print(f"  Moon rasi     : {new_moon.get('rasi')}")
    print(f"  Moon nakshatra: {new_nak.get('name') if isinstance(new_nak, dict) else new_nak}")
    print()


if __name__ == "__main__":
    main()
