from app.models.report_schema import PredictionReportSnapshot
from app.models.ui_birthchart_schema import (
    BirthChartView,
    BirthIdentity,
    PanchangamAtBirth,
    PlanetPosition,
    HouseDetail,
    DashaSnapshot,
    ChartMetadata,
)


def build_birthchart_view(snapshot: PredictionReportSnapshot) -> BirthChartView:
    """
    EPIC-7.6
    Build immutable BirthChartView from persisted snapshot.

    Rules:
    - NO DB access
    - NO astrology logic
    - Snapshot is single source of truth
    - Artifact-first lookup for Panchangam + charts
    """

    base = snapshot.base_chart
    birth = base["birth_details"]
    eph = base.get("ephemeris", {})

    # -----------------------------
    # IDENTITY
    # -----------------------------
    identity = BirthIdentity(
        name=birth.get("name"),
        gender=birth.get("gender"),
        date_of_birth=birth.get("date_of_birth"),
        time_of_birth=birth.get("time_of_birth"),
        place_of_birth=birth.get("place_of_birth"),
        latitude=birth.get("latitude"),
        longitude=birth.get("longitude"),
        timezone=birth.get("timezone"),
    )

    # -----------------------------
    # PANCHANGAM (AT BIRTH) — artifact-first
    # -----------------------------
    p_raw = None
    if snapshot.chart_artifacts and "panchangam" in snapshot.chart_artifacts:
        p_raw = snapshot.chart_artifacts["panchangam"]
    elif "panchangam" in base:
        # fallback (if engine ever stores it in base payload)
        p_raw = base["panchangam"]

    if not p_raw:
        found = list(snapshot.chart_artifacts.keys()) if snapshot.chart_artifacts else []
        raise ValueError(f"Panchangam artifact missing. Found: {found}")

    # Flatten rich artifact → UI strings
    # (keeps DB authoritative, UI stays simple)
    tithi = p_raw.get("tithi")
    nak = p_raw.get("nakshatra")
    yoga = p_raw.get("yoga")
    kar = p_raw.get("karana")
    wday = p_raw.get("weekday")

    panchangam = PanchangamAtBirth(
        tithi=(
            f"{tithi.get('paksha')} {tithi.get('tithi')}"
            if isinstance(tithi, dict)
            else str(tithi)
        ),
        nakshatra=(
            f"{nak.get('name')} (Pada {nak.get('pada')})"
            if isinstance(nak, dict)
            else str(nak)
        ),
        yoga=(yoga.get("name") if isinstance(yoga, dict) else str(yoga)),
        karana=(kar.get("name") if isinstance(kar, dict) else str(kar)),
        weekday=(wday.get("english") if isinstance(wday, dict) else str(wday)),
    )

    # -----------------------------
    # PLANETS (from ephemeris)
    # -----------------------------
    planets = []
    planets_raw = eph.get("planets", {}) or {}
    for planet, p in planets_raw.items():
        planets.append(
            PlanetPosition(
                planet=planet,
                longitude=p.get("longitude"),
                sign=p.get("rasi"),
                degree=p.get("degree"),
                nakshatra=p.get("nakshatra"),
                pada=p.get("pada"),
                house=p.get("house"),
                retrograde=p.get("retrograde"),
            )
        )

    # -----------------------------
    # HOUSES (from ephemeris)
    # -----------------------------
    houses = []
    for h in (eph.get("houses") or []):
        houses.append(
            HouseDetail(
                house=h.get("house"),
                sign=h.get("sign"),
                lord=h.get("lord"),
                planets=h.get("planets") or [],
            )
        )

    # -----------------------------
    # DASHA (static snapshot) — optional
    # -----------------------------
    dasha_raw = base.get("dasha")
    dasha = None
    if isinstance(dasha_raw, dict):
        dasha = DashaSnapshot(
            system="Vimshottari",
            maha_dasha=dasha_raw.get("maha"),
            antar_dasha=dasha_raw.get("antar"),
            start_date=dasha_raw.get("start_date"),
            end_date=dasha_raw.get("end_date"),
        )
    else:
        # keep contract stable; if schema requires dasha, raise here instead
        dasha = DashaSnapshot(
            system="Vimshottari",
            maha_dasha=None,
            antar_dasha=None,
            start_date=None,
            end_date=None,
        )

    # -----------------------------
    # METADATA
    # -----------------------------
    lagna = (eph.get("lagna") or {}).get("rasi")
    moon = (eph.get("moon") or {}).get("rasi")
    sun = (eph.get("sun") or {}).get("rasi")

    metadata = ChartMetadata(
        lagna=lagna,
        moon_sign=moon,
        sun_sign=sun,
        ayanamsa=base.get("ayanamsa"),
        calculation_method=base.get("calculation_method"),
    )

    return BirthChartView(
        identity=identity,
        panchangam=panchangam,
        chart_metadata=metadata,
        planets=planets,
        houses=houses,
        dasha=dasha,
    )
