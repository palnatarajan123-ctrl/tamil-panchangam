# Prediction Signal Inventory

This document tracks all prediction signals implemented in the Tamil Panchangam Astrology Engine.

## Signal Types

| Type | Description |
|------|-------------|
| **slow** | Changes rarely (Mahadasha, major transits) |
| **fast** | Changes monthly/weekly (Moon transits, Tara Bala) |
| **validation** | Validates other signals (Ashtakavarga) |

## Signal Inventory

### 1. Gochara Engine (`app/engines/gochara_engine.py`)

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `GOCHARA_JUPITER` | slow | career, finance, personal_growth | monthly, yearly | Jupiter longitude, natal Moon rasi |
| `GOCHARA_SATURN_*` | slow | career, health, all areas | monthly, yearly | Saturn longitude, natal Moon rasi |
| `GOCHARA_RAHU_KETU` | slow | all areas (karmic) | monthly, yearly | Rahu longitude, natal Moon rasi |

**Outputs:**
- Jupiter: from_moon_house, effect (favorable/neutral/challenging)
- Saturn: phase (janma_sani/ashtama_sani/kantaka_sani/neutral), effect
- Rahu-Ketu: axis, theme, effect (disruptive/favorable/neutral)

---

### 2. Moon Transit Engine (`app/engines/moon_transit_engine.py`)

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `CHANDRA_GATI_RHYTHM` | fast | health, relationships | monthly, weekly | Moon positions throughout month, natal Moon rasi |

**Outputs:**
- dominant_moods: Top 3 emotional themes
- supportive_days: Days with favorable Moon position
- sensitive_days: Days requiring extra awareness
- challenging_days: Days with difficult Moon positions

---

### 3. Nakshatra Engine (`app/engines/nakshatra_engine.py`)

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `TARA_BALA_*` | fast | all areas | monthly, weekly, daily | Birth Moon longitude, current Moon longitude |

**Tara Bala Classifications:**
1. Janma (Birth Star) - neutral
2. Sampat (Wealth) - favorable
3. Vipat (Danger) - challenging
4. Kshemam (Welfare) - favorable
5. Pratyak (Obstacles) - challenging
6. Sadhana (Achievement) - favorable
7. Naidhana (Death-like) - challenging
8. Mitra (Friend) - favorable
9. Parama Mitra (Great Friend) - favorable

---

### 4. Ashtakavarga Engine (`app/engines/ashtakavarga_engine.py`)

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `ASHTAKAVARGA_*` | validation | all areas | monthly | Saturn/Jupiter transit rasi, birth Moon rasi |

**Strength Classifications:**
- high_support: Bindu >= 5 (Jupiter) / >= 4 (Saturn)
- moderate_support: Bindu 4 (Jupiter) / 3 (Saturn)
- low_support: Bindu 3 (Jupiter) / 2 (Saturn)
- resistance: Bindu < 3 (Jupiter) / < 2 (Saturn)

**Overall Support:**
- strong_support: Both planets well-supported
- partial_support: One planet well-supported
- balanced: Neither strong nor weak
- needs_remedies: One or both planets facing resistance

---

### 5. Remedy Engine (`app/engines/remedy_engine.py`)

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| (remedies output) | derived | all areas | monthly, weekly | Gochara, Nakshatra, Ashtakavarga outputs |

**Remedy Categories:**
- Saturn remedies (phase-specific)
- Rahu remedies (for disruptive effects)
- Ketu remedies (for karmic themes)
- Jupiter remedies (for weak transits)
- Tara Bala remedies (for challenging nakshatras)

---

### 6. Existing Signals (Pre-expansion)

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `DASHA_*_H*` | slow | varies by house | monthly, yearly | Mahadasha/Antardasha lords, house lordships |
| `NAVAMSA_DIGNITY` | slow | all areas | monthly | D9 chart dignities |

---

## Integration Points

### Prediction Envelope (`app/engines/prediction_envelope.py`)

The envelope now includes:
```python
{
    # Existing
    "dasha_context": {...},
    "navamsa": {...},
    
    # EPIC Signal Expansion
    "gochara": {...},
    "chandra_gati": {...},
    "nakshatra_context": {...},
    "ashtakavarga": {...},
    "remedies": {...},
}
```

### Synthesis Engine (`app/engines/synthesis_engine.py`)

Converts envelope signals to normalized synthesis signals:
- Gochara signals → GOCHARA_JUPITER, GOCHARA_SATURN_*, GOCHARA_RAHU_KETU
- Nakshatra signals → TARA_BALA_*
- Ashtakavarga signals → ASHTAKAVARGA_*
- Chandra Gati signals → CHANDRA_GATI_RHYTHM

---

## Signal Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PREDICTION PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Base Chart ──┬──► Gochara Engine ────────────────────┐     │
│               │                                        │     │
│               ├──► Moon Transit Engine ───────────────┤     │
│               │                                        │     │
│               ├──► Nakshatra Engine ──────────────────┼──► ENVELOPE
│               │                                        │     │
│               ├──► Ashtakavarga Engine ───────────────┤     │
│               │                                        │     │
│               └──► Remedy Engine ─────────────────────┘     │
│                                                              │
│  ENVELOPE ──────► Synthesis Engine ────► Life Area Scores   │
│                                                              │
│  Life Areas ────► Interpretation Builder ──► Final Output   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Debugging

All engines include DEBUG logging:
```python
logger.debug(f"DEBUG: {engine_name} computing for {reference_date}")
logger.debug(f"DEBUG: {engine_name} computed: {key_values}")
```

Enable debug logging to trace signal flow:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Graceful Degradation

All engines return safe defaults on error:
- Gochara: Returns "neutral" effects with error flag
- Moon Transit: Returns empty day lists with error flag
- Nakshatra: Returns "neutral" quality with error flag
- Ashtakavarga: Returns "unknown" strength with error flag
- Remedies: Returns default spiritual practices

Prediction pipeline continues even if individual engines fail.

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-23 | v1.0 | Initial EPIC Signal Expansion implementation |

---

## Future Enhancements

- [ ] Full Ashtakavarga calculation from all 7 planets + Lagna
- [ ] Weekly prediction granularity for Moon transits
- [ ] Daily Tara Bala tracking
- [ ] Planetary aspects (Drishti) engine
- [ ] Yogas (special combinations) detection
- [ ] AI explanation layer for signal interpretation
