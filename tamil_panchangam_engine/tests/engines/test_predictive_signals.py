# tests/engines/test_predictive_signals.py
"""
Tests for the predictive_signals engine suite.

All tests are pure unit tests — no DB, no live swisseph required for most.
The varshaphal and transit tests call swisseph but only verify shape/sanity,
not exact values, so they tolerate minor ephemeris differences.
"""

from datetime import date, datetime, timezone


# ── Helper: minimal vimshottari structure ─────────────────────────────────────

def _mk_vm(md_lord, md_start, md_end, ad_lord, ad_start, ad_end):
    """Build a minimal vimshottari dict with one MD and one AD."""
    return {
        "timeline": [
            {
                "mahadasha": md_lord,
                "start": md_start,
                "end": md_end,
                "is_partial": False,
                "antar_dashas": [
                    {
                        "antar_lord": ad_lord,
                        "start": ad_start,
                        "end": ad_end,
                    }
                ],
            }
        ]
    }


# ── Engine 1: Pratyantar Dasha ────────────────────────────────────────────────

class TestPratyantar:
    def test_lord_and_dates_returned(self):
        from app.engines.pratyantar_dasha_engine import compute_pratyantar

        vm = _mk_vm(
            "Moon", "2022-05-05T00:00:00+00:00", "2032-05-05T00:00:00+00:00",
            "Jupiter", "2025-04-03T00:00:00+00:00", "2026-08-02T00:00:00+00:00",
        )
        # reference_date well inside Jupiter AD
        result = compute_pratyantar(vm, date(2026, 7, 1))

        assert result["md_lord"] == "Moon"
        assert result["ad_lord"] == "Jupiter"
        assert result["pratyantar"] is not None
        pt = result["pratyantar"]
        assert "lord" in pt and pt["lord"] in {
            "Sun", "Moon", "Mars", "Rahu", "Jupiter",
            "Saturn", "Mercury", "Ketu", "Venus",
        }
        assert "start" in pt and "end" in pt
        assert pt["duration_days"] > 0

    def test_sookshma_returned(self):
        from app.engines.pratyantar_dasha_engine import compute_pratyantar

        vm = _mk_vm(
            "Moon", "2022-05-05T00:00:00+00:00", "2032-05-05T00:00:00+00:00",
            "Jupiter", "2025-04-03T00:00:00+00:00", "2026-08-02T00:00:00+00:00",
        )
        result = compute_pratyantar(vm, date(2026, 7, 1))
        sk = result.get("sookshma")
        assert sk is not None
        assert "lord" in sk and sk["duration_days"] > 0

    def test_returns_empty_outside_all_periods(self):
        from app.engines.pratyantar_dasha_engine import compute_pratyantar

        vm = _mk_vm(
            "Moon", "2022-05-05T00:00:00+00:00", "2032-05-05T00:00:00+00:00",
            "Jupiter", "2025-04-03T00:00:00+00:00", "2026-08-02T00:00:00+00:00",
        )
        # Date outside the only MD
        result = compute_pratyantar(vm, date(2010, 1, 1))
        assert result == {}

    def test_sequence_starts_from_ad_lord(self):
        """Pratyantar sequence must start from the AD lord."""
        from app.engines.pratyantar_dasha_engine import compute_pratyantar, DASHA_SEQUENCE

        vm = _mk_vm(
            "Venus", "2000-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00",
            "Sun",   "2000-01-01T00:00:00+00:00", "2000-07-01T00:00:00+00:00",
        )
        # First Pratyantar within Sun AD should start with Sun
        result = compute_pratyantar(vm, date(2000, 1, 5))
        # Very start of Sun AD → PT lord should be Sun
        assert result.get("pratyantar", {}).get("lord") == "Sun"


# ── Engine 2: Transit Hits ────────────────────────────────────────────────────

class TestTransitHits:
    def _ephemeris(self, moon_lon=235.0, sun_lon=228.0, mercury_lon=14.3, lagna_lon=250.0):
        return {
            "lagna": {"longitude_deg": lagna_lon},
            "planets": {
                "Sun":     {"longitude_deg": sun_lon},
                "Moon":    {"longitude_deg": moon_lon},
                "Mercury": {"longitude_deg": mercury_lon},
                "Mars":    {"longitude_deg": 30.0},
                "Jupiter": {"longitude_deg": 60.0},
                "Venus":   {"longitude_deg": 90.0},
                "Saturn":  {"longitude_deg": 120.0},
                "Rahu":    {"longitude_deg": 150.0},
                "Ketu":    {"longitude_deg": 330.0},
            },
        }

    def test_returns_list(self):
        from app.engines.transit_hits_engine import compute_transit_hits
        hits = compute_transit_hits(self._ephemeris(), date(2026, 7, 1), window_days=5)
        assert isinstance(hits, list)

    def test_hit_dict_shape(self):
        from app.engines.transit_hits_engine import compute_transit_hits
        hits = compute_transit_hits(self._ephemeris(), date(2026, 7, 1), window_days=15)
        for h in hits:
            assert "transit_planet" in h
            assert "natal_planet" in h
            assert "aspect_type" in h
            assert "orb" in h and h["orb"] <= 2.0
            assert "house" in h and 1 <= h["house"] <= 12
            assert "life_area_hint" in h
            assert "hit_date" in h

    def test_angular_diff_conjunction(self):
        from app.engines.transit_hits_engine import _angular_diff
        assert _angular_diff(15.0, 14.5, 0.0) < 1.0

    def test_angular_diff_opposition(self):
        from app.engines.transit_hits_engine import _angular_diff
        assert _angular_diff(194.5, 14.5, 180.0) < 1.0

    def test_house_of(self):
        from app.engines.transit_hits_engine import _house_of
        # Planet 30° ahead of lagna → house 2
        assert _house_of(280.0, 250.0) == 2
        # Planet at lagna → house 1
        assert _house_of(250.0, 250.0) == 1

    def test_rahu_ketu_only_conjunction_opposition(self):
        """Rahu/Ketu should never generate trine or square hits."""
        from app.engines.transit_hits_engine import compute_transit_hits
        hits = compute_transit_hits(self._ephemeris(), date(2026, 7, 1), window_days=45)
        for h in hits:
            if h["transit_planet"] in ("Rahu", "Ketu"):
                assert h["aspect_type"] in ("conjunction", "opposition"), (
                    f"Unexpected aspect {h['aspect_type']} for {h['transit_planet']}"
                )


# ── Engine 3: Yoga Activation ─────────────────────────────────────────────────

class TestYogaActivation:
    def _yogas(self):
        return {
            "yogas": [
                {
                    "name": "Dhana Yoga",
                    "type": "dhana",
                    "planets": ["Jupiter", "Venus"],
                    "houses_involved": [2, 11],
                    "present": True,
                    "strength": "strong",
                },
                {
                    "name": "Gaja Kesari Yoga",
                    "present": True,
                    "strength": "strong",
                },
                {
                    "name": "Some Yoga",
                    "type": "raja",
                    "planets": ["Saturn"],
                    "present": True,
                    "strength": "moderate",
                },
            ]
        }

    def test_peak_activation_when_pt_matches(self):
        from app.engines.yoga_activation_engine import compute_yoga_activation
        result = compute_yoga_activation(self._yogas(), "Moon", "Jupiter", "Venus")
        dhana = next(y for y in result if y["name"] == "Dhana Yoga")
        assert dhana["activation_level"] == "peak"
        assert dhana["currently_active"] is True

    def test_strong_activation_when_md_matches(self):
        from app.engines.yoga_activation_engine import compute_yoga_activation
        result = compute_yoga_activation(self._yogas(), "Jupiter", "Moon", "Mars")
        dhana = next(y for y in result if y["name"] == "Dhana Yoga")
        assert dhana["activation_level"] == "strong"

    def test_moderate_activation_when_ad_matches(self):
        from app.engines.yoga_activation_engine import compute_yoga_activation
        result = compute_yoga_activation(self._yogas(), "Moon", "Venus", "Mars")
        dhana = next(y for y in result if y["name"] == "Dhana Yoga")
        assert dhana["activation_level"] == "moderate"

    def test_gaja_kesari_uses_name_map(self):
        from app.engines.yoga_activation_engine import compute_yoga_activation
        result = compute_yoga_activation(self._yogas(), "Jupiter", "Moon", "Mars")
        names = [y["name"] for y in result]
        assert "Gaja Kesari Yoga" in names

    def test_inactive_yoga_excluded(self):
        """Yoga with present=False should not appear."""
        from app.engines.yoga_activation_engine import compute_yoga_activation
        yogas = {"yogas": [{"name": "Foo", "present": False, "planets": ["Sun"]}]}
        result = compute_yoga_activation(yogas, "Sun", "Sun", "Sun")
        assert result == []

    def test_sorted_peak_first(self):
        from app.engines.yoga_activation_engine import compute_yoga_activation
        result = compute_yoga_activation(self._yogas(), "Moon", "Jupiter", "Venus")
        levels = [y["activation_level"] for y in result]
        if len(levels) >= 2:
            order = {"peak": 0, "strong": 1, "moderate": 2}
            assert order.get(levels[0], 9) <= order.get(levels[-1], 9)


# ── Engine 4: Special Lagnas ──────────────────────────────────────────────────

class TestSpecialLagnas:
    """Uses pre-known Dhanusu (index 8) lagna with Jupiter-ruled chart."""

    def _ephemeris(self):
        # Dhanusu lagna: sign index 8, longitude ~250°
        # Jupiter (ruler) at ~135° = Simham (index 4)
        return {
            "lagna": {"longitude_deg": 250.0},
            "planets": {
                "Sun":     {"longitude_deg": 228.75},
                "Moon":    {"longitude_deg": 235.75},
                "Mars":    {"longitude_deg": 60.0},
                "Mercury": {"longitude_deg": 220.0},
                "Jupiter": {"longitude_deg": 135.0},  # Simham
                "Venus":   {"longitude_deg": 200.0},
                "Saturn":  {"longitude_deg": 300.0},
                "Rahu":    {"longitude_deg": 70.0},
                "Ketu":    {"longitude_deg": 250.0},
            },
        }

    def _birth_details(self):
        return {
            "date_of_birth": "1983-12-05",
            "time_of_birth": "08:00:00",
            "latitude": 9.9252,
            "longitude": 78.1198,
            "timezone": "Asia/Kolkata",
        }

    def test_arudha_shape(self):
        from app.engines.special_lagnas_engine import compute_special_lagnas
        result = compute_special_lagnas(self._ephemeris(), self._birth_details())
        assert "arudha" in result
        assert "rasi" in result["arudha"]
        assert 1 <= result["arudha"]["house_from_lagna"] <= 12

    def test_arudha_not_same_as_lagna_or_7th(self):
        """Arudha Lagna exception rule: must not equal lagna (house 1) or 7th house."""
        from app.engines.special_lagnas_engine import compute_special_lagnas
        result = compute_special_lagnas(self._ephemeris(), self._birth_details())
        h = result["arudha"]["house_from_lagna"]
        assert h not in (1, 7), f"Arudha should not be at house {h} (exception not applied)"

    def test_hora_ghati_lagnas_present(self):
        from app.engines.special_lagnas_engine import compute_special_lagnas
        result = compute_special_lagnas(self._ephemeris(), self._birth_details())
        assert "hora" in result and "rasi" in result["hora"]
        assert "ghati" in result and "rasi" in result["ghati"]

    def test_upapada_shape(self):
        from app.engines.special_lagnas_engine import compute_special_lagnas
        result = compute_special_lagnas(self._ephemeris(), self._birth_details())
        assert "upapada" in result
        assert "rasi" in result["upapada"]

    def test_arudha_rasi_is_valid(self):
        from app.engines.special_lagnas_engine import compute_special_lagnas, RASI_NAMES
        result = compute_special_lagnas(self._ephemeris(), self._birth_details())
        assert result["arudha"]["rasi"] in RASI_NAMES


# ── Engine 5: Varshaphal ──────────────────────────────────────────────────────

class TestVarshaphal:
    """
    Uses a Scorpio Sun (228.75°) birth; solar return for 2026 should be ≈Oct 2026.
    Exact date varies by 1-2 days depending on ayanamsa/ephemeris version — we
    only assert approximate range and correct shape.
    """

    def _ephemeris(self):
        return {
            "lagna": {"longitude_deg": 250.0},
            "planets": {"Sun": {"longitude_deg": 228.75}},
        }

    def _birth_details(self):
        return {
            "date_of_birth": "1983-12-05",
            "latitude": 9.9252,
            "longitude": 78.1198,
        }

    def test_solar_return_date_approximate(self):
        from app.engines.varshaphal_engine import compute_varshaphal
        result = compute_varshaphal(self._ephemeris(), self._birth_details(), year=2026)
        sr = result["solar_return_date"]
        # Sun at ~228° is in Scorpio; SR should be in Oct/Nov
        assert sr.startswith("2026"), f"Expected 2026 solar return, got {sr}"
        month = int(sr.split("-")[1])
        assert 9 <= month <= 12, f"Unexpected SR month {month} for Scorpio sun"

    def test_varshesha_is_valid_planet(self):
        from app.engines.varshaphal_engine import compute_varshaphal
        valid = {"Mars", "Venus", "Mercury", "Moon", "Sun", "Jupiter", "Saturn"}
        result = compute_varshaphal(self._ephemeris(), self._birth_details(), year=2026)
        assert result["varshesha"] in valid

    def test_muntha_formula(self):
        """Muntha = (natal_lagna_sign + years_elapsed) % 12."""
        from app.engines.varshaphal_engine import compute_varshaphal, RASI_NAMES
        result = compute_varshaphal(self._ephemeris(), self._birth_details(), year=2026)
        natal_lagna_idx = int(250.0 / 30) % 12  # Dhanusu = 8
        years = 2026 - 1983
        expected_muntha_idx = (natal_lagna_idx + years) % 12
        assert result["muntha"] == RASI_NAMES[expected_muntha_idx]

    def test_result_shape(self):
        from app.engines.varshaphal_engine import compute_varshaphal
        result = compute_varshaphal(self._ephemeris(), self._birth_details(), year=2026)
        for key in ("year", "solar_return_date", "lagna", "varshesha",
                    "varshesha_house", "muntha", "muntha_house",
                    "strength", "benefics_in_kendra"):
            assert key in result, f"Missing key: {key}"
        assert result["year"] == 2026
        assert result["strength"] in ("strong", "moderate", "weak", "minimal")


# ── Confluence Detector ───────────────────────────────────────────────────────

class TestConfluence:
    def _mock_pratyantar(self, pt_lord="Jupiter"):
        return {
            "md_lord": "Moon",
            "ad_lord": "Jupiter",
            "pratyantar": {"lord": pt_lord, "start": "2026-06-01", "end": "2026-08-01", "duration_days": 61},
            "sookshma": {"lord": "Venus", "start": "2026-07-01", "end": "2026-07-10", "duration_days": 9},
        }

    def _mock_transit_hits(self, area="career", n=3):
        """Generate n positive Jupiter transit hits for the given life area."""
        hits = []
        for i in range(n):
            hits.append({
                "transit_planet": "Jupiter",
                "natal_planet": "Mercury",
                "natal_degree": 14.3,
                "transit_degree": 14.1,
                "hit_date": f"2026-07-{10 + i:02d}",
                "aspect_type": "conjunction",
                "orb": 0.2,
                "house": 10,
                "life_area_hint": area,
            })
        return hits

    def test_opportunity_emitted_at_3_signals(self):
        from app.engines.event_window_engine import detect_confluence
        hits = self._mock_transit_hits("career", n=3)
        result = detect_confluence(
            pratyantar=self._mock_pratyantar("Jupiter"),
            transit_hits=hits,
            active_yogas=[],
            varshaphal={"varshesha": "Jupiter", "year": 2026, "muntha_house": 10},
            refined_av={},
            reference_date=date(2026, 7, 15),
            num_months=1,
        )
        opportunities = [w for w in result if w["direction"] == "opportunity"]
        assert len(opportunities) >= 1

    def test_caution_emitted_for_malefic_hits(self):
        from app.engines.event_window_engine import detect_confluence
        hits = [
            {
                "transit_planet": "Saturn",
                "natal_planet": "Sun",
                "natal_degree": 228.0,
                "transit_degree": 48.0,
                "hit_date": "2026-07-11",
                "aspect_type": "opposition",
                "orb": 0.5,
                "house": 10,
                "life_area_hint": "career",
            }
        ] * 4  # 4 Saturn opposition hits → strong caution signal
        result = detect_confluence(
            pratyantar=self._mock_pratyantar("Saturn"),
            transit_hits=hits,
            active_yogas=[],
            varshaphal={"varshesha": "Saturn", "year": 2026},
            refined_av={},
            reference_date=date(2026, 7, 15),
            num_months=1,
        )
        cautions = [w for w in result if w["direction"] == "caution"]
        assert len(cautions) >= 1

    def test_confidence_levels(self):
        from app.engines.event_window_engine import detect_confluence
        hits = self._mock_transit_hits("career", n=5)
        result = detect_confluence(
            pratyantar=self._mock_pratyantar("Jupiter"),
            transit_hits=hits,
            active_yogas=[],
            varshaphal={"varshesha": "Jupiter"},
            refined_av={},
            reference_date=date(2026, 7, 15),
            num_months=1,
        )
        for w in result:
            assert w["confidence"] in ("medium", "high", "very high")
            assert w["signal_count"] >= 3

    def test_no_window_below_threshold(self):
        """A single transit hit should not generate any window."""
        from app.engines.event_window_engine import detect_confluence
        hits = self._mock_transit_hits("career", n=1)
        result = detect_confluence(
            pratyantar=self._mock_pratyantar("Mars"),  # malefic → no positive for career
            transit_hits=hits,
            active_yogas=[],
            varshaphal={"varshesha": "Mars"},
            refined_av={},
            reference_date=date(2026, 7, 15),
            num_months=1,
        )
        # With only 1 transit hit and Mars (not a benefic for career), career should not reach 3
        career_opps = [w for w in result if w["life_area"] == "career" and w["direction"] == "opportunity"]
        assert len(career_opps) == 0

    def test_window_sorted_by_start(self):
        from app.engines.event_window_engine import detect_confluence
        hits = self._mock_transit_hits("career", n=4)
        result = detect_confluence(
            pratyantar=self._mock_pratyantar("Jupiter"),
            transit_hits=hits,
            active_yogas=[],
            varshaphal={"varshesha": "Jupiter"},
            refined_av={},
            reference_date=date(2026, 7, 15),
            num_months=2,
        )
        dates = [w["window_start"] for w in result]
        assert dates == sorted(dates)
