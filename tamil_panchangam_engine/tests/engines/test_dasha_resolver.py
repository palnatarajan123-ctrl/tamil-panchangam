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
    # Given: A simplified Vimshottari structure
    # (matches what base_chart["dashas"]["vimshottari"] contains)
    # -------------------------------------------------
    vimshottari = {
        "current": {
            "lord": "Saturn",
            "start": "2019-06-01T00:00:00Z",
            "end": "2038-06-01T00:00:00Z",
        },
        "periods": [
            {
                "maha_lord": "Saturn",
                "start": "2019-06-01T00:00:00Z",
                "end": "2038-06-01T00:00:00Z",
                "antar_dashas": [
                    {
                        "antar_lord": "Saturn",
                        "start": "2019-06-01T00:00:00Z",
                        "end": "2022-06-01T00:00:00Z",
                    },
                    {
                        "antar_lord": "Mercury",
                        "start": "2022-06-01T00:00:00Z",
                        "end": "2025-06-01T00:00:00Z",
                    },
                    {
                        "antar_lord": "Ketu",
                        "start": "2025-06-01T00:00:00Z",
                        "end": "2026-06-01T00:00:00Z",
                    },
                ],
            }
        ],
    }

    # -------------------------------------------------
    # When: Resolving Antar Dasha for Jan 2026
    # -------------------------------------------------
    reference_date = datetime(2026, 1, 15, tzinfo=timezone.utc)

    antar = resolve_antar_dasha(
        vimshottari=vimshottari,
        reference_date=reference_date,
    )

    # -------------------------------------------------
    # Then: Antar Dasha is resolved correctly
    # -------------------------------------------------
    assert antar is not None, "Antar dasha should not be None"

    assert antar["maha_lord"] == "Saturn"
    assert antar["antar_lord"] == "Ketu"

    assert "start" in antar
    assert "end" in antar

    # Sanity: reference date must fall within antar period
    start = datetime.fromisoformat(antar["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(antar["end"].replace("Z", "+00:00"))

    assert start <= reference_date <= end
