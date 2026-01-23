# AI Interpretation Engine v1.0

## Overview

The AI Interpretation Engine generates intelligent, non-repetitive interpretations for prediction windows. It runs after the synthesis engine and produces human-readable analysis based on computed astrological signals.

## Architecture

```
Prediction Envelope → Synthesis Engine → AI Interpretation Engine → UI
```

## Three-Level Structure

### Level 1: Window Summary

Provides a concise overview of the prediction period:

- **Momentum**: growth, consolidation, pressure, or transition
- **Dominant Forces**: Top 2-3 astrological influences (dasha lords, major transits, yogas)
- **Outcome Mode**: ease, effort, or delay
- **Timing Shifts**: Notable timing variations within the window

**Example Output:**
```json
{
  "momentum": "consolidation",
  "momentum_description": "integration period",
  "dominant_forces": [
    {"type": "yoga", "name": "Gaja Kesari Yoga", "description": "Gaja Kesari Yoga"},
    {"type": "dasha", "planet": "Jupiter", "description": "Jupiter Mahadasha / Saturn Antardasha"}
  ],
  "outcome_mode": "effort",
  "overview": "This period marks an integration period..."
}
```

### Level 2: Life Area Interpretations

For each life area (career, finance, relationships, health, personal_growth):

- **Summary**: 2-3 sentence overview
- **Deeper Explanation**: 5-6 sentences with signal interaction
- **Tone varies by area**:
  - Career: authority, effort, visibility
  - Finance: inflow, retention, risk
  - Relationships: warmth, strain, reciprocity
  - Health: stamina, vulnerability, recovery
  - Personal Growth: learning, resistance, insight

### Level 3: Astrological Attribution

Every life area interpretation includes:

- **Planets**: Specific planets involved
- **Dasha**: Current Mahadasha/Antardasha
- **Engines**: Which calculation engines contributed (Drishti, Yoga, House Strength, etc.)
- **Signals Used**: Top signals with valence, strength, and rationale

**Example Output:**
```json
{
  "attribution": {
    "planets": ["Jupiter", "Mars"],
    "dasha": "Jupiter/Saturn",
    "engines": ["Gochara (Transits)", "Drishti (Aspects)"],
    "signals_used": [
      {"key": "GOCHARA_JUPITER", "valence": "pos", "strength": 0.8, "rationale": "Jupiter transiting house 5 from Moon (favorable)"}
    ]
  }
}
```

## Signal Prioritization

- Uses only top 2-3 dominant signals per life area
- Prefers signal interaction over enumeration
- Ignores weak or redundant signals
- Signals sourced from synthesis engine's `top_signals`

## Vocabulary System

Each life area has dedicated vocabulary sets:

- Positive outlook phrases
- Negative outlook phrases  
- Neutral outlook phrases
- Action verbs
- Tone descriptors

This ensures non-repetitive, contextually appropriate language.

## Integration

### Location
`tamil_panchangam_engine/app/engines/ai_interpretation_engine.py`

### Usage
```python
from app.engines.ai_interpretation_engine import generate_interpretation

ai_interpretation = generate_interpretation(
    envelope=envelope,
    synthesis=synthesis,
    year=2026,
    month=1,
)
```

### Response Structure
```json
{
  "engine_version": "ai-interpretation-v1.0",
  "generated_at": "2026-01-23T12:00:00",
  "window_summary": {...},
  "life_areas": {
    "career": {...},
    "finance": {...},
    "relationships": {...},
    "health": {...},
    "personal_growth": {...}
  }
}
```

## Constraints

- Does NOT recompute astrology
- Does NOT modify scores
- Grounds every statement in astrological logic
- Maximum 120-150 words per life area
- Uses deterministic vocabulary (no external AI calls)

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-23 | v1.0 | Initial implementation with 3-level structure |
