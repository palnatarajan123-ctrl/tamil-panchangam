# app/engines/life_area_config.py
from __future__ import annotations

"""
============================================================
ASTROLOGY TUNING ZONE — HANDLE WITH CARE ⚠️
============================================================

This file defines LIFE-AREA SCORING POLICY.
It is:
- Declarative
- Deterministic
- Versioned
- The ONLY place where astrology “opinions” live

❌ Do NOT add logic here
❌ Do NOT reference runtime data
❌ Do NOT mutate weights dynamically

If scores feel “off”, tune HERE — not in the scorer.

------------------------------------------------------------
SATURN PHILOSOPHY (IMPORTANT)
------------------------------------------------------------
Saturn is NOT treated as “bad”.

We model Saturn as:
- Delay
- Effort
- Responsibility
- Karmic pressure
- Long-term restructuring

Rules we follow:
1. Saturn is strongest when tied to IDENTITY (1), WORK (6), or STRUCTURE (10)
2. Saturn softens in:
   - 12th house (internalization, withdrawal, spiritual work)
   - 9th house (maturity through philosophy, mentors)
3. Saturn should REDUCE scores, not CRUSH them
4. Saturn’s value comes from DURATION, not SHOCK

Therefore:
- Saturn weights are moderate
- House weights do most of the work
- Valence multiplier stays at -1.0 (no dramatization)
"""

# -------------------------------------------------
# LIFE AREAS (LOCKED CONTRACT)
# -------------------------------------------------

LIFE_AREAS = (
    "career",
    "finance",
    "relationships",
    "health",
    "personal_growth",
)

# -------------------------------------------------
# V1.1 — STABLE, EXPLAINABLE, TUNABLE
# -------------------------------------------------
# Changes from v1:
# - Explicit Saturn softening via house weights (12, 9)
# - No change to scorer logic
# - Comments added for traceability

LIFE_AREA_WEIGHTS = {
    # ============================================================
    # CAREER
    # ============================================================
    # Saturn here = slow grind, delayed recognition, responsibility
    # NOT failure.
    "career": {
        "houses": {
            10: 1.00,  # authority, role, profession
            6: 0.55,   # service, effort, workload
            2: 0.35,   # earnings from work
            11: 0.35,  # gains, recognition
            1: 0.20,   # identity pressure (Saturn hits here)
            12: 0.10,  # ⬅ Saturn softens here (internal work, not collapse)
        },
        "benefics": {
            "Sun": 0.40,
            "Jupiter": 0.45,
            "Mercury": 0.30,
            "Venus": 0.15,
        },
        "malefics": {
            "Saturn": 0.45,  # strong but not punitive
            "Rahu": 0.35,
            "Ketu": 0.15,
            "Mars": 0.25,
        },
        "source_bias": {
            "dasha": 1.10,
            "transit": 1.00,
            "birth": 0.90,
            "derived": 0.95,
            "panchangam": 0.75,
            "pakshi": 0.70,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.25,
        },
        "max_abs_contrib_per_signal": 1.50,
        # Chart-wide yoga/event-window/divisional signals carry neither a
        # house nor a planet (see life_area_scorer.py's house_w/planet_w
        # lookup) -- weighted here by relevance to THIS area, same 0-1
        # scale as "houses" above (1.00 = this area's defining house).
        "signal_key_weights": {
            "YOGA_RAJA": 0.85,             # power/success -> strongest for career
            "YOGA_GAJA_KESARI": 0.55,      # leadership facet
            "YOGA_DHANA": 0.35,            # wealth yoga still supports career standing
            "D2_WEALTH_PATTERN": 0.20,
            "D7_CREATIVE_POTENTIAL": 0.15,
            "EVENT_WINDOWS_FAVORABLE": 0.30,
            "EVENT_WINDOWS_CHALLENGING": 0.30,
        },
        # Fallback base weight for structurally house/planet-less signals
        # not named above, keyed by "source" -- covers dynamically-
        # suffixed keys (TARA_BALA_*, ASHTAKAVARGA_*) without enumerating
        # every suffix. Only applied when a signal has no house/planet
        # AND no signal_key_weights entry (see life_area_scorer.py).
        "signal_source_weights": {
            "nakshatra": 0.20,     # Tara Bala: general period quality
            "ashtakavarga": 0.30,  # planetary support/strength summary
            "chandra_gati": 0.15,  # Moon rhythm, weaker for career
            "derived": 0.20,       # Navamsa dignity
            "drishti": 0.20,       # aspect-balance summary
        },
    },

    # ============================================================
    # FINANCE
    # ============================================================
    # Saturn here = delayed liquidity, conservative growth
    "finance": {
        "houses": {
            2: 1.00,   # income
            11: 0.80,  # gains
            8: 0.35,   # other people's money, risk
            12: 0.25,  # ⬅ loss but also expense discipline
        },
        "benefics": {
            "Jupiter": 0.50,
            "Venus": 0.40,
            "Mercury": 0.25,
        },
        "malefics": {
            "Saturn": 0.30,  # softened vs career
            "Rahu": 0.40,
            "Ketu": 0.20,
            "Mars": 0.25,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.90,
            "derived": 0.95,
            "panchangam": 0.70,
            "pakshi": 0.65,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.20,
        },
        "max_abs_contrib_per_signal": 1.40,
        "signal_key_weights": {
            "YOGA_DHANA": 0.85,            # wealth yoga -> strongest for finance
            "YOGA_RAJA": 0.35,             # status yoga still supports finances
            "YOGA_GAJA_KESARI": 0.20,
            "D2_WEALTH_PATTERN": 0.60,     # Hora chart is wealth-specific
            "D7_CREATIVE_POTENTIAL": 0.10,
            "EVENT_WINDOWS_FAVORABLE": 0.30,
            "EVENT_WINDOWS_CHALLENGING": 0.30,
        },
        "signal_source_weights": {
            "nakshatra": 0.20,
            "ashtakavarga": 0.35,  # planetary support summary matters most where it's already weighted heavily
            "chandra_gati": 0.10,
            "derived": 0.20,
            "drishti": 0.15,
        },
    },

    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    # Saturn here = boundaries, commitment tests, maturity
    "relationships": {
        "houses": {
            7: 1.00,   # marriage, partnership
            5: 0.45,   # romance
            2: 0.35,   # family
            8: 0.30,   # intimacy
            12: 0.25,  # emotional withdrawal
        },
        "benefics": {
            "Venus": 0.55,
            "Moon": 0.40,
            "Jupiter": 0.25,
        },
        "malefics": {
            "Saturn": 0.20,  # intentionally light
            "Mars": 0.45,
            "Rahu": 0.25,
            "Ketu": 0.30,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.95,
            "derived": 0.95,
            "panchangam": 0.70,
            "pakshi": 0.70,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.20,
        },
        "max_abs_contrib_per_signal": 1.40,
        "signal_key_weights": {
            "D7_CREATIVE_POTENTIAL": 0.45,  # family/creativity -> strongest for relationships
            "YOGA_GAJA_KESARI": 0.15,
            "YOGA_DHANA": 0.15,
            "YOGA_RAJA": 0.15,
            "D2_WEALTH_PATTERN": 0.10,
            "EVENT_WINDOWS_FAVORABLE": 0.30,
            "EVENT_WINDOWS_CHALLENGING": 0.30,
        },
        "signal_source_weights": {
            "nakshatra": 0.20,
            "ashtakavarga": 0.25,
            "chandra_gati": 0.35,  # emotional rhythm matters most for relationships
            "derived": 0.45,       # Navamsa (D9) is classically the marriage/spouse chart
            "drishti": 0.20,
        },
    },

    # ============================================================
    # HEALTH
    # ============================================================
    # Saturn here = chronic conditions, stamina, recovery time
    "health": {
        "houses": {
            6: 1.00,   # disease
            1: 0.75,   # body
            8: 0.55,   # longevity
            12: 0.30,  # ⬅ hospitalization/rest, not death
        },
        "benefics": {
            "Moon": 0.40,
            "Jupiter": 0.30,
            "Mercury": 0.20,
        },
        "malefics": {
            "Saturn": 0.45,
            "Mars": 0.50,
            "Rahu": 0.25,
            "Ketu": 0.20,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.95,
            "derived": 0.95,
            "panchangam": 0.75,
            "pakshi": 0.80,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.25,
        },
        "max_abs_contrib_per_signal": 1.50,
        "signal_key_weights": {
            # Yogas/divisional refinements are only weakly health-relevant
            # classically; kept low rather than zero so a strong yoga still
            # nudges health slightly (vitality/resilience), not excluded.
            "YOGA_GAJA_KESARI": 0.15,
            "YOGA_DHANA": 0.10,
            "YOGA_RAJA": 0.10,
            "D2_WEALTH_PATTERN": 0.10,
            "D7_CREATIVE_POTENTIAL": 0.10,
            "EVENT_WINDOWS_FAVORABLE": 0.30,
            "EVENT_WINDOWS_CHALLENGING": 0.30,
        },
        "signal_source_weights": {
            "nakshatra": 0.25,
            "ashtakavarga": 0.30,
            "chandra_gati": 0.35,  # emotional rhythm ties directly to psychosomatic health
            "derived": 0.15,
            "drishti": 0.15,
        },
    },

    # ============================================================
    # PERSONAL GROWTH
    # ============================================================
    # Saturn here = spiritual discipline, solitude, inner work
    "personal_growth": {
        "houses": {
            9: 1.00,   # philosophy, mentors
            5: 0.65,   # learning
            12: 0.60,  # ⬅ Saturn strongest *positive* here
            8: 0.40,   # transformation
        },
        "benefics": {
            "Jupiter": 0.55,
            "Ketu": 0.35,
            "Moon": 0.15,
        },
        "malefics": {
            "Saturn": 0.20,  # intentionally gentle
            "Rahu": 0.40,
            "Mars": 0.15,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.95,
            "derived": 0.95,
            "panchangam": 0.75,
            "pakshi": 0.75,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.25,
        },
        "max_abs_contrib_per_signal": 1.40,
        "signal_key_weights": {
            "YOGA_GAJA_KESARI": 0.65,       # wisdom/leadership -> strongest for personal growth
            "D7_CREATIVE_POTENTIAL": 0.45,  # creativity facet
            "YOGA_DHANA": 0.15,
            "YOGA_RAJA": 0.20,
            "D2_WEALTH_PATTERN": 0.10,
            "EVENT_WINDOWS_FAVORABLE": 0.30,
            "EVENT_WINDOWS_CHALLENGING": 0.30,
        },
        "signal_source_weights": {
            "nakshatra": 0.25,
            "ashtakavarga": 0.30,
            "chandra_gati": 0.25,
            "derived": 0.35,  # Navamsa dignity reflects dharmic/inner strength
            "drishti": 0.20,
        },
    },
}
