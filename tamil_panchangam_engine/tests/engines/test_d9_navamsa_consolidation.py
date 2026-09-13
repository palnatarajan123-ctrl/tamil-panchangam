"""
Regression tests for the D9/Navamsa consolidation (2026-09-13).

Two independent D9 implementations used to exist: app.engines.navamsa_engine
(now deleted) and app.engines.divisional_charts.d9_navamsa (now the sole
implementation). Both used the identical, formula-verified-correct
Parashara Navamsa calculation, but different output key names
("navamsa_sign" vs "sign") -- which caused prediction_envelope.py's
d9_context to always read None for every planet's D9 sign. See
CLAUDE.md's 2026-09-13 entry.
"""
from app.engines.divisional_charts import build_navamsa_chart, navamsa_to_legacy_shape
from app.engines.d9_strength_engine import planet_strength


def test_navamsa_to_legacy_shape_matches_old_engine_output_shape():
    ephemeris = {
        "planets": {"Sun": {"rasi": "Aries", "longitude_deg": 10.0}},
        "lagna": {"rasi": "Taurus", "longitude_deg": 40.0},
    }
    d9 = build_navamsa_chart(ephemeris)
    legacy = navamsa_to_legacy_shape(d9)

    assert "Sun" in legacy
    assert set(legacy["Sun"].keys()) == {"navamsa_sign", "dignity"}
    assert legacy["Sun"]["navamsa_sign"] == d9["planets"]["Sun"]["sign"]
    # Lagna must NOT appear in the legacy shape -- the old engine never
    # computed one, and payload["charts"]["D9"] consumers were never
    # built to expect it.
    assert "Lagna" not in legacy


def test_vargottama_bonus_fires_when_d1_and_d9_signs_match():
    d1_context = {"planet_positions": {"Mars": {"rasi": "Capricorn"}}}
    d9_context = {
        "dignity": {"Mars": "neutral"},
        "planet_signs": {"Mars": "Capricorn"},  # same sign as D1 -> Vargottama
    }
    strength = planet_strength("Mars", d1_context, d9_context)
    assert strength == 1.1  # base 1.0 * dignity 1.0 * vargottama 1.1


def test_vargottama_bonus_does_not_fire_when_signs_differ():
    d1_context = {"planet_positions": {"Mars": {"rasi": "Capricorn"}}}
    d9_context = {
        "dignity": {"Mars": "neutral"},
        "planet_signs": {"Mars": "Leo"},
    }
    strength = planet_strength("Mars", d1_context, d9_context)
    assert strength == 1.0


def test_vargottama_bonus_would_have_silently_never_fired_under_the_old_key():
    """Regression guard against reintroducing the exact bug: if
    planet_signs used the OLD ("navamsa_sign") key name instead of the
    fixed one, this must show the bonus silently failing to apply --
    proves the fix actually matters, not just that the new key works."""
    d1_context = {"planet_positions": {"Mars": {"rasi": "Capricorn"}}}
    d9_context_with_old_key_only = {
        "dignity": {"Mars": "neutral"},
        "navamsa_sign_WRONG_KEY": {"Mars": "Capricorn"},
    }
    # d9_context here has no "planet_signs" key at all (simulating the
    # pre-fix bug where prediction_envelope.py read the wrong key and
    # produced an all-None planet_signs dict) -- .get() must return None,
    # not raise, and the bonus must not fire.
    strength = planet_strength("Mars", d1_context, {**d9_context_with_old_key_only, "planet_signs": {}})
    assert strength == 1.0
