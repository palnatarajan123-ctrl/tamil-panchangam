from app.reference.nakshatra_attributes import NAKSHATRA_ATTRIBUTES


def build_birth_metadata(
    ephemeris: dict,
    panchangam_birth: dict,
) -> dict:
    """
    Build immutable birth metadata for UI + PDF rendering.

    Inputs:
    - ephemeris: computed planetary positions at birth
    - panchangam_birth: panchangam computed at birth time

    No astrology logic.
    No prediction logic.
    Deterministic transformation only.
    """

    # -----------------------------
    # Core birth markers
    # -----------------------------
    moon = ephemeris["moon"]
    lagna = ephemeris["lagna"]

    nakshatra_name = moon["nakshatra"]["name"]
    nakshatra_pada = moon["nakshatra"].get("pada")

    nakshatra_attrs = NAKSHATRA_ATTRIBUTES.get(nakshatra_name)

    if not nakshatra_attrs:
        raise ValueError(f"Missing Nakshatra attributes for {nakshatra_name}")

    # -----------------------------
    # Tamil calendar (from Panchangam)
    # -----------------------------
    tamil_calendar = {
        "tamil_year": panchangam_birth.get("tamil_year"),
        "tamil_month": panchangam_birth.get("tamil_month"),
        "tamil_day": panchangam_birth.get("tamil_day"),
        "weekday": panchangam_birth.get("weekday"),
    }

    # -----------------------------
    # Nakshatra metadata
    # -----------------------------
    nakshatra_metadata = {
        "name": nakshatra_name,
        "pada": nakshatra_pada,
        "lord": nakshatra_attrs["lord"],
        "deity": nakshatra_attrs["deity"],
        "ganam": nakshatra_attrs["ganam"],
        "yoni": nakshatra_attrs["yoni"],
        "animal": nakshatra_attrs["animal"],
        "tree": nakshatra_attrs["tree"],
        "bird": nakshatra_attrs["bird"],
        "bhutam": nakshatra_attrs["bhutam"],
    }

    # -----------------------------
    # Rasi & Ascendant
    # -----------------------------
    rasi_metadata = {
        "moon_sign": moon["rasi"],
        "moon_sign_lord": moon["rasi_lord"],
        "ascendant": lagna["rasi"],
        "ascendant_lord": lagna["rasi_lord"],
    }

    # -----------------------------
    # Panchangam elements
    # -----------------------------
    panchangam_elements = {
        "tithi": panchangam_birth.get("tithi"),
        "paksha": panchangam_birth.get("paksha"),
        "yoga": panchangam_birth.get("yoga"),
        "karana": panchangam_birth.get("karana"),
        "sunrise": panchangam_birth.get("sunrise"),
        "sunset": panchangam_birth.get("sunset"),
    }

    # -----------------------------
    # Final immutable block
    # -----------------------------
    return {
        "tamil_calendar": tamil_calendar,
        "nakshatra": nakshatra_metadata,
        "rasi": rasi_metadata,
        "panchangam": panchangam_elements,
    }
