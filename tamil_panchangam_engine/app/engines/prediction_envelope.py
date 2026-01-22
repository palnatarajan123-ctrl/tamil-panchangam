# app/engines/prediction_envelope.py

from app.engines.transits import compute_monthly_transits
from app.engines.pancha_pakshi import get_daily_pakshi_guidance
from app.utils.time_utils import get_month_reference_date_utc
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.antar_explanation_engine import build_antar_explanation
from app.engines.narrative_engine import build_narrative


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

    latitude = birth_details["latitude"]
    longitude = birth_details["longitude"]
    natal_moon_rasi = ephemeris["moon"]["rasi"]

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
        # Legacy-safe fields
        "maha_lord": active_maha["lord"],
        "antar_lord": antar["lord"] if antar else None,
        "active_lords": active_lords,
        "lord_weights": lord_weights,

        # UI contract (DO NOT BREAK)
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

        # Lifetime reference
        "timeline": timeline,

        # EPIC-6.3 — additive
        "antar_explanation": antar_explanation,
    }

    # -------------------------------------------------
    # 6. EPIC-14 — Narrative (optional, safe)
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
    # 6A. EPIC-3 STEP 2A — NAVAMSA (D9) CONTEXT (FACTUAL)
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
    # 7. Final Envelope (FACTS FIRST)
    # -------------------------------------------------
    return {
        "reference": {
            "year": year,
            "month": month,
            "reference_date_utc": reference_date_utc.isoformat(),
        },
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
        # EPIC-3 ADDITIVE (NON-BREAKING)
        "navamsa": d9_context,
    }
