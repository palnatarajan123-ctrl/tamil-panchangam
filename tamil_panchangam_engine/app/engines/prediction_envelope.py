# app/engines/prediction_envelope.py

from app.engines.transits import compute_monthly_transits
from app.engines.pancha_pakshi import get_daily_pakshi_guidance
from app.utils.time_utils import get_month_reference_date_utc
from app.engines.dasha_resolver import resolve_antar_dasha


def build_monthly_prediction_envelope(
    *,
    base_chart: dict,
    year: int,
    month: int,
) -> dict:
    """
    EPIC-4 + EPIC-6 + EPIC-6.2
    Build the monthly astrological envelope.

    FACTS ONLY — no scoring, no prose
    """

    reference_date_utc = get_month_reference_date_utc(year, month)

    birth_details = base_chart["birth_details"]
    ephemeris = base_chart["ephemeris"]

    latitude = birth_details["latitude"]
    longitude = birth_details["longitude"]
    natal_moon_rasi = ephemeris["moon"]["rasi"]

    # 1. Transits
    transits = compute_monthly_transits(
        reference_date_utc=reference_date_utc,
        latitude=latitude,
        longitude=longitude,
        natal_moon_rasi=natal_moon_rasi,
    )

    # 2. Maha Dasha
    vimshottari = base_chart["dashas"]["vimshottari"]
    active_dasha = vimshottari.get("current")
    if not active_dasha:
        raise RuntimeError("Active Maha Dasha could not be resolved")

    # 3. Antar Dasha
    antar_dasha = resolve_antar_dasha(
        vimshottari=vimshottari,
        reference_date=reference_date_utc,
    )

    # 4. Pancha Pakshi
    pakshi_name = base_chart["pancha_pakshi_birth"]["pakshi"]
    pakshi_daily = get_daily_pakshi_guidance(
        birth_pakshi=pakshi_name,
        date_local=reference_date_utc,
    )

    # 5. Dasha context (enriched)
    active_lords = [active_dasha["lord"]]
    lord_weights = {active_dasha["lord"]: 0.7}

    if antar_dasha:
        active_lords.append(antar_dasha["antar_lord"])
        lord_weights[antar_dasha["antar_lord"]] = round(
            0.3 * antar_dasha.get("confidence_weight", 0.5), 2
        )

    dasha_context = {
        "maha_lord": active_dasha["lord"],
        "antar_lord": antar_dasha["antar_lord"] if antar_dasha else None,
        "is_maha_active": True,
        "active_lords": active_lords,
        "lord_weights": lord_weights,
    }

    # 6. Envelope
    envelope = {
        "reference": {
            "year": year,
            "month": month,
            "reference_date_utc": reference_date_utc.isoformat(),
        },
        "environment": {"transits": transits},
        "time_ruler": {
            "vimshottari_dasha": active_dasha,
            "antar_dasha": antar_dasha,
        },
        "dasha_context": dasha_context,
        "biological_rhythm": {"pancha_pakshi_daily": pakshi_daily},
    }

    return envelope
