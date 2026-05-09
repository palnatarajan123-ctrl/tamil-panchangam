# tests/engines/test_dasha_resolver.py

from datetime import datetime, timezone

from app.engines.dasha_resolver import resolve_antar_dasha


def test_resolve_antar_dasha_basic():
    """
    EPIC-6
    Verifies that Antar Dasha is correctly resolved
    for a given reference date within an active Maha Dasha.
    """

    # -------------------------------------------------
    # Given: A simplified Vimshottari structure using the locked schema
    # (matches what base_chart["dashas"]["vimshottari"] contains)
    # -------------------------------------------------
    vimshottari = {
        "timeline": [
            {
                "mahadasha": "Jupiter",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2036-01-01T00:00:00+00:00",
                "is_partial": False,
                "antar_dashas": [
                    {
                        "antar_lord": "Jupiter",
                        "start": "2020-01-01T00:00:00+00:00",
                        "end": "2022-02-01T00:00:00+00:00",
                    },
                    {
                        "antar_lord": "Saturn",
                        "start": "2022-02-01T00:00:00+00:00",
                        "end": "2024-10-01T00:00:00+00:00",
                    },
                ],
            }
        ]
    }

    # -------------------------------------------------
    # When: Resolving Antar Dasha for Jun 2023 (inside Saturn antar)
    # -------------------------------------------------
    result = resolve_antar_dasha(
        vimshottari=vimshottari,
        reference_date=datetime(2023, 6, 15, tzinfo=timezone.utc),
    )

    # -------------------------------------------------
    # Then: Antar Dasha is resolved correctly
    # -------------------------------------------------
    assert result is not None, "Antar dasha should not be None"

    assert result["maha"]["lord"] == "Jupiter"
    assert result["antar"]["lord"] == "Saturn"

    assert isinstance(result["antar"]["confidence_weight"], float)
    assert 0.0 <= result["antar"]["confidence_weight"] <= 1.0

    # Sanity: reference date must fall within antar period
    start = datetime.fromisoformat(result["antar"]["start"])
    end = datetime.fromisoformat(result["antar"]["end"])
    reference_date = datetime(2023, 6, 15, tzinfo=timezone.utc)
    assert start <= reference_date < end


def test_resolve_antar_dasha_no_match():
    """Returns None when reference date is outside all mahadasha windows."""
    vimshottari = {
        "timeline": [
            {
                "mahadasha": "Jupiter",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2036-01-01T00:00:00+00:00",
                "is_partial": False,
                "antar_dashas": [
                    {
                        "antar_lord": "Jupiter",
                        "start": "2020-01-01T00:00:00+00:00",
                        "end": "2022-02-01T00:00:00+00:00",
                    }
                ],
            }
        ]
    }
    result = resolve_antar_dasha(
        vimshottari=vimshottari,
        reference_date=datetime(2010, 1, 1, tzinfo=timezone.utc),
    )
    assert result is None
