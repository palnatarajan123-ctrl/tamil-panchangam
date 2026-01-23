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
| 2026-01-23 | v2.0 | Prompt 2 implementation: Drishti, House Strength, Functional Roles, Yogas, Event Windows |

---

### 6. Drishti Engine (`app/engines/drishti_engine.py`) - Prompt 2

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `DRISHTI_{planet}_H{house}` | natal | varies by house | monthly | Planetary longitudes, Lagna |
| `DRISHTI_BALANCE_*` | natal | all areas | monthly | All aspect calculations |

**Parashara Special Aspects:**
- Mars: 4th and 8th house aspects
- Jupiter: 5th and 9th house aspects
- Saturn: 3rd and 10th house aspects
- Rahu/Ketu: 5th and 9th house aspects (like Jupiter)

**Effect Classifications:**
- supportive: Benefic planet aspect
- challenging: Malefic planet aspect
- protective: Malefic aspecting dusthana
- mixed: Neutral planet aspect

---

### 7. House Strength Engine (`app/engines/house_strength_engine.py`) - Prompt 2

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `HOUSE_STRENGTH_H{n}` | natal | varies by house | monthly | Occupants, lord position, aspects |
| `HOUSE_WEAKNESS_H{n}` | natal | varies by house | monthly | Occupants, lord position, aspects |
| `HOUSE_AFFLICTION_H{n}` | natal | varies by house | monthly | Malefic presence/aspects |

**Strength Factors:**
- Benefic occupants: +10 points
- Malefic in upachaya (3,6,10,11): +5 points
- Malefic elsewhere: -8 points
- Lord in kendra: +12 points
- Lord in trikona: +15 points
- Lord in dusthana: -10 points
- Benefic aspects: +5 points each
- Malefic aspects: -5 points each

**Strength Levels:** strong (>=70), moderate (50-69), weak (30-49), very_weak (<30)

**Affliction Sources:** Saturn/Rahu presence (+20), Mars/Ketu (+15), Saturn/Rahu aspect (+12), Mars aspect (+10)

---

### 8. Functional Role Engine (`app/engines/functional_role_engine.py`) - Prompt 2

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `YOGAKARAKA_ACTIVE_{planet}` | natal | all areas (strong positive) | monthly | Lagna, house lordship, active dasha |
| `MARAKA_ACTIVE_{planet}` | natal | health, longevity | monthly | Lagna, house lordship, active dasha |
| `PLANET_FUNCTIONAL_ROLE` | natal | varies | monthly | Lagna, house lordship |

**Functional Roles:**
- yogakaraka: Rules both trikona and kendra
- benefic: Trikona lord without dusthana
- malefic: Dusthana lord without trikona
- neutral: Kendradhipati dosha (benefic owning kendra)
- neutral_positive: Natural malefic owning kendra
- maraka: Lords of 2nd or 7th house
- mixed: Rules both favorable and unfavorable houses

**Classical Yogakarakas by Lagna:**
- Aries/Leo: Mars
- Taurus/Libra/Aquarius: Saturn (Taurus), Saturn (Libra), Venus (Aquarius)
- Cancer: Mars
- Capricorn: Venus

---

### 9. Yoga Engine (`app/engines/yoga_engine.py`) - Prompt 2

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `YOGA_GAJA_KESARI` | natal | career, status, wisdom | monthly | Jupiter-Moon distance |
| `YOGA_DHANA` | natal | finance, wealth | monthly | Lords of 2,5,9,11 positions |
| `YOGA_RAJA` | natal | career, power, success | monthly | Viparita Raja detection |

**Yogas Detected:**

1. **Gaja Kesari Yoga**
   - Jupiter in kendra (1,4,7,10) from Moon
   - Effects: Leadership, wisdom, reputation, prosperity

2. **Dhana Yoga**
   - Lords of 2,5,9,11 in conjunction or mutual aspect
   - Effects: Wealth accumulation, financial prosperity

3. **Viparita Raja Yoga**
   - Lords of 6,8,12 placed in other dusthanas
   - Harsha Yoga: 6th lord in 8th or 12th
   - Sarala Yoga: 8th lord in 6th or 12th
   - Vimala Yoga: 12th lord in 6th or 8th
   - Effects: Rise through unconventional means

4. **Neecha Bhanga Raja Yoga**
   - Debilitated planet's sign lord in kendra from Moon
   - Effects: Success despite initial challenges

---

### 10. Event Window Engine (`app/engines/event_window_engine.py`) - Prompt 2

| Signal | Type | Life Areas Impacted | Used By | Deterministic Inputs |
|--------|------|---------------------|---------|---------------------|
| `EVENT_WINDOWS_FAVORABLE` | fast | all areas | monthly | Moon transit, Tara Bala |
| `EVENT_WINDOWS_CHALLENGING` | fast | all areas | monthly | Moon transit, Tara Bala |

**Window Types:**
- supportive: Favorable Tara Bala (Sampat, Kshemam, Sadhana, Mitra, Parama Mitra)
- sensitive: Janma or Pratyak Tara
- challenging: Vipat or Naidhana Tara

**Overall Quality:**
- favorable: Supportive > 2× Challenging
- mildly_favorable: Supportive > Challenging
- balanced: Equal distribution
- mildly_challenging: Challenging > Supportive
- challenging: Challenging > 2× Supportive

---

## Future Enhancements

- [ ] Full Ashtakavarga calculation from all 7 planets + Lagna
- [ ] Weekly prediction granularity for Moon transits
- [ ] Daily Tara Bala tracking
- [x] Planetary aspects (Drishti) engine ✓ Prompt 2
- [x] Yogas (special combinations) detection ✓ Prompt 2
- [ ] AI explanation layer for signal interpretation
