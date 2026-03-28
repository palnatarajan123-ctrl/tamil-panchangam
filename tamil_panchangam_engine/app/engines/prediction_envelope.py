# app/engines/prediction_envelope.py

import logging
from app.engines.transits import compute_monthly_transits
from app.engines.pancha_pakshi import get_daily_pakshi_guidance
from app.utils.time_utils import get_month_reference_date_utc
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.antar_explanation_engine import build_antar_explanation
from app.engines.narrative_engine import build_narrative
from app.services.birth_chart_builder import build_birth_chart_view_model
from app.engines.gochara_engine import compute_gochara, _longitude_to_rasi
from app.engines.moon_transit_engine import compute_chandra_gati
from app.engines.nakshatra_engine import compute_nakshatra_context
from app.engines.ashtakavarga_engine import compute_ashtakavarga_validation
from app.engines.remedy_engine import compute_remedies
from app.engines.drishti_engine import compute_drishti
from app.engines.house_strength_engine import compute_all_house_strength
from app.engines.functional_role_engine import compute_functional_roles
from app.engines.yoga_engine import compute_yogas
from app.engines.sade_sati_engine import compute_sade_sati
from app.engines.shadbala_engine import compute_shadbala
from app.engines.event_window_engine import compute_event_windows

logger = logging.getLogger(__name__)



# ============================================================
# MAHADASHA TIMELINE (UI SAFE)
# ============================================================

def build_mahadasha_timeline(vimshottari: dict) -> list:
    """
    Build UI-ready Mahadasha timeline from Vimshottari data.
    SINGLE SOURCE: vimshottari["timeline"]
    """
    timeline = vimshottari.get("timeline", [])
    out = []

    for p in timeline:
        out.append(
            {
                "mahadasha": p.get("mahadasha"),
                "start": p.get("start"),
                "end": p.get("end"),
                "is_partial": p.get("is_partial", False),
            }
        )

    return out


# ============================================================
# MONTHLY PREDICTION ENVELOPE
# ============================================================

def _compute_sade_sati_safe(base_chart: dict) -> dict:
    """Compute sade sati fresh — base_chart never stores it."""
    try:
        result = compute_sade_sati(base_chart)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.warning(f"Sade sati computation failed: {e}")
        return {}

def _compute_shadbala_safe(base_chart: dict) -> dict:
    """Compute shadbala fresh — base_chart never stores it."""
    try:
        result = compute_shadbala(base_chart)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.warning(f"Shadbala computation failed: {e}")
        return {}

def build_monthly_prediction_envelope(
    *,
    base_chart: dict,
    year: int,
    month: int,
) -> dict:
    """
    EPIC-4 + EPIC-6 + EPIC-6.3 + EPIC-10 + EPIC-14 + EPIC-3 (2A)

    FACTUAL ENVELOPE.
    - No scoring
    - No decisioning
    - No deterministic claims
    """

    # -------------------------------------------------
    # Reference date
    # -------------------------------------------------
    reference_date_utc = get_month_reference_date_utc(year, month)

    birth_details = base_chart["birth_details"]
    ephemeris = base_chart["ephemeris"]
    ayanamsa = ephemeris.get("ayanamsa", "lahiri")

    latitude = birth_details["latitude"]
    longitude = birth_details["longitude"]
    natal_moon_rasi = ephemeris["moon"]["rasi"]

    # -------------------------------------------------
    # 🔑 DERIVE HOUSES (SINGLE SOURCE OF TRUTH)
    # -------------------------------------------------
    birth_chart_view = build_birth_chart_view_model(base_chart)

    # 🔒 Normalize houses → dict keyed by house number (REQUIRED)
    houses = {
        h["house"]: h
        for h in (birth_chart_view.get("houses") or [])
    }

    # -------------------------------------------------
    # 1. Transits
    # -------------------------------------------------
    transits = compute_monthly_transits(
        reference_date_utc=reference_date_utc,
        latitude=latitude,
        longitude=longitude,
        natal_moon_rasi=natal_moon_rasi,
    )

    # -------------------------------------------------
    # 2. Vimshottari Dasha (single source)
    # -------------------------------------------------
    vimshottari = base_chart["dashas"]["vimshottari"]

    active_maha = vimshottari.get("current")
    if not active_maha:
        raise RuntimeError("Active Mahadasha missing from Vimshottari data")

    timeline = build_mahadasha_timeline(vimshottari)

    # -------------------------------------------------
    # 3. Antar Dasha (resolved ONCE)
    # -------------------------------------------------
    antar_dasha = resolve_antar_dasha(
        vimshottari=vimshottari,
        reference_date=reference_date_utc,
    )

    antar = antar_dasha.get("antar") if antar_dasha else None

    # -------------------------------------------------
    # 4. Pancha Pakshi (daily rhythm)
    # -------------------------------------------------
    pakshi_name = base_chart["pancha_pakshi_birth"]["pakshi"]

    pakshi_daily = get_daily_pakshi_guidance(
        birth_pakshi=pakshi_name,
        date_local=reference_date_utc,
    )

    # -------------------------------------------------
    # 5. Dasha Context (UI + synthesis safe)
    # -------------------------------------------------
    active_lords = [active_maha["lord"]]
    lord_weights = {active_maha["lord"]: 0.7}

    if antar:
        active_lords.append(antar["lord"])
        lord_weights[antar["lord"]] = round(
            0.3 * antar.get("confidence_weight", 0.5),
            2,
        )

    antar_explanation = (
        build_antar_explanation(
            maha_lord=active_maha["lord"],
            antar_lord=antar["lord"],
            confidence_weight=antar.get("confidence_weight", 0.5),
        )
        if antar
        else None
    )

    dasha_context = {
        "maha_lord": active_maha["lord"],
        "antar_lord": antar["lord"] if antar else None,
        "active_lords": active_lords,
        "lord_weights": lord_weights,

        "active": {
            "maha": {
                "lord": active_maha["lord"],
                "start": active_maha["start"],
                "end": active_maha["end"],
                "is_partial": active_maha.get("is_partial", False),
            },
            "antar": (
                {
                    "lord": antar["lord"],
                    "start": antar["start"],
                    "end": antar["end"],
                    "confidence_weight": antar.get("confidence_weight"),
                }
                if antar
                else None
            ),
        },

        "timeline": timeline,
        "antar_explanation": antar_explanation,
    }

    # -------------------------------------------------
    # 6. Narrative (optional, safe)
    # -------------------------------------------------
    narrative = build_narrative(
        period_label="Monthly",
        maha_lord=active_maha["lord"],
        antar_lord=antar["lord"] if antar else None,
        antar_phase=(
            antar_explanation.get("phase")
            if antar_explanation
            else None
        ),
        themes=(
            antar_explanation.get("themes", [])
            if antar_explanation
            else []
        ),
        remedies=(
            antar_explanation.get("remedies", [])
            if antar_explanation
            else []
        ),
        cautions=(
            antar_explanation.get("cautions", [])
            if antar_explanation
            else []
        ),
    )

    # -------------------------------------------------
    # 6A. NAVAMSA (D9) CONTEXT (FACTUAL)
    # -------------------------------------------------
    d9_raw = (
        base_chart
        .get("divisional_charts", {})
        .get("D9", {})
    )

    d9_context = {
        "planet_signs": {
            planet: data.get("navamsa_sign")
            for planet, data in d9_raw.items()
            if isinstance(data, dict)
        },
        "dignity": {
            planet: data.get("dignity", "neutral")
            for planet, data in d9_raw.items()
            if isinstance(data, dict)
        },
        "has_d9": bool(d9_raw),
    }

    # -------------------------------------------------
    # 7. DRISHTI ENGINE - computed early so Gochara L3 can use it
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Drishti (aspects) [early, for Gochara L3]")
    birth_moon_longitude = ephemeris.get("moon", {}).get("longitude_deg", 0.0)
    natal_lagna_longitude = ephemeris.get("lagna", {}).get("longitude_deg", 0.0)
    drishti = compute_drishti(
        ephemeris=ephemeris,
        houses=houses,
        lagna_longitude=natal_lagna_longitude,
    )

    # -------------------------------------------------
    # 7b. GOCHARA (TRANSIT) ENGINE - EPIC Signal Expansion
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Gochara signals")
    natal_lagna_rasi_for_gochara = _longitude_to_rasi(natal_lagna_longitude) if natal_lagna_longitude else None
    gochara = compute_gochara(
        reference_date_utc=reference_date_utc,
        latitude=latitude,
        longitude=longitude,
        natal_moon_rasi=natal_moon_rasi,
        natal_moon_longitude=birth_moon_longitude if birth_moon_longitude else None,
        natal_lagna_rasi=natal_lagna_rasi_for_gochara,
        drishti_data=drishti,
        ayanamsa=ayanamsa,
    )

    # -------------------------------------------------
    # 8. CHANDRA GATI (Moon Transit Rhythm) - EPIC Signal Expansion
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Chandra Gati signals")
    chandra_gati = compute_chandra_gati(
        year=year,
        month=month,
        natal_moon_rasi=natal_moon_rasi,
        latitude=latitude,
        longitude=longitude,
        ayanamsa=ayanamsa,
    )

    # -------------------------------------------------
    # 9. NAKSHATRA CONTEXT + TARA BALA - EPIC Signal Expansion
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Nakshatra context")
    nakshatra_context = compute_nakshatra_context(
        reference_date_utc=reference_date_utc,
        birth_moon_longitude=birth_moon_longitude,
        latitude=latitude,
        longitude=longitude,
        ayanamsa=ayanamsa,
    )

    # -------------------------------------------------
    # 10. ASHTAKAVARGA VALIDATION - EPIC Signal Expansion
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Ashtakavarga validation")
    ashtakavarga = compute_ashtakavarga_validation(
        saturn_transit_rasi=gochara.get("saturn", {}).get("transit_rasi", "Aries"),
        jupiter_transit_rasi=gochara.get("jupiter", {}).get("transit_rasi", "Aries"),
        birth_moon_rasi=natal_moon_rasi,
        natal_positions=ephemeris,
        lagna_longitude=natal_lagna_longitude,
    )

    # -------------------------------------------------
    # 11. REMEDY ENGINE - EPIC Signal Expansion
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Remedies")
    remedies = compute_remedies(
        gochara=gochara,
        nakshatra_context=nakshatra_context,
        ashtakavarga=ashtakavarga,
    )

    # -------------------------------------------------
    # 13. HOUSE STRENGTH ENGINE - Prompt 2
    # -------------------------------------------------
    logger.debug("DEBUG: Computing House Strength")
    house_strength = compute_all_house_strength(
        ephemeris=ephemeris,
        houses=houses,
        drishti_data=drishti,
    )

    # -------------------------------------------------
    # 14. FUNCTIONAL ROLE ENGINE - Prompt 2
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Functional Roles")
    functional_roles = compute_functional_roles(
        ephemeris=ephemeris,
        houses=houses,
    )

    # -------------------------------------------------
    # 15. YOGA ENGINE - Prompt 2
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Yogas")
    yogas = compute_yogas(
        ephemeris=ephemeris,
        houses=houses,
    )

    # -------------------------------------------------
    # 16. EVENT WINDOW ENGINE - Prompt 2
    # -------------------------------------------------
    logger.debug("DEBUG: Computing Event Windows")
    event_windows = compute_event_windows(
        birth_moon_longitude=birth_moon_longitude,
        reference_date=reference_date_utc,
        gochara_data=gochara,
        latitude=latitude,
        longitude=longitude,
        ayanamsa=ayanamsa,
    )

    # -------------------------------------------------
    # 17. TIER-1 DIVISIONAL CHARTS
    # -------------------------------------------------
    divisional_charts = base_chart.get("divisional_charts", {})
    
    # -------------------------------------------------
    # 18. Final Envelope (FACTS FIRST)
    # -------------------------------------------------
    logger.debug(f"DEBUG: Envelope keys: gochara={bool(gochara)}, chandra_gati={bool(chandra_gati)}, nakshatra={bool(nakshatra_context)}, ashtakavarga={bool(ashtakavarga)}, remedies={bool(remedies)}")
    
    return {
        "reference": {
            "year": year,
            "month": month,
            "reference_date_utc": reference_date_utc.isoformat(),
            "ayanamsa": ayanamsa,
        },

        # ✅ CRITICAL: DERIVED HOUSES (NOT FROM DB)
        "houses": houses,

        "ephemeris": base_chart.get("ephemeris", {}),

        "environment": {
            "transits": transits,
        },

        "time_ruler": {
            "vimshottari_dasha": active_maha,
            "antar_dasha": antar,
        },

        "dasha_context": dasha_context,
        "narrative": narrative,

        "biological_rhythm": {
            "pancha_pakshi_daily": pakshi_daily,
        },

        "navamsa": d9_context,
        
        # ===== TIER-1 DIVISIONAL CHARTS =====
        "divisional_charts": divisional_charts,

        # ===== EPIC SIGNAL EXPANSION =====
        "gochara": gochara,
        "chandra_gati": chandra_gati,
        "nakshatra_context": nakshatra_context,
        "ashtakavarga": ashtakavarga,
        "remedies": remedies,

        # ===== PROMPT 2 ENGINES =====
        "drishti": drishti,
        "house_strength": house_strength,
        "functional_roles": functional_roles,
        "yogas": yogas,
        "event_windows": event_windows,

        # ===== SADE SATI =====
        "sade_sati": _compute_sade_sati_safe(base_chart),

        # ===== SHADBALA =====
        "shadbala": _compute_shadbala_safe(base_chart),
    }
