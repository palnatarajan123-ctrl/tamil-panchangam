# Prediction Signal Inventory

## Overview

This document tracks the astrological signals, UI components, and interpretation engines used in the Tamil Panchangam prediction system.

---

## UI Components

### BirthAstroContextTable

**Location:** `client/src/components/BirthAstroContextTable.tsx`

A unified table component displaying birth and current astrological context used for predictions.

**Sections:**

1. **Birth Reference**
   - Janma Nakshatra
   - Janma Rasi
   - Lagna
   - Moon Sign
   - Nakshatra Lord
   - Birth Dasha

2. **Active Dasha Context (Now)**
   - Current Mahadasha
   - Current Antardasha
   - Dasha Balance
   - Functional Role Planets (Yogakaraka/Maraka)

3. **Transit / Gochara Context**
   - Jupiter Transit
   - Saturn Transit
   - Rahu-Ketu Axis

4. **Nakshatra & Timing Context**
   - Current Moon Nakshatra
   - Tara Bala Classification
   - Chandra Gati Dominant Mood
   - Favorable Window Summary

5. **Pakshi / Rhythm Context**
   - Dominant Pakshi
   - Activity Phase

---

## AI Interpretation Engine

### Version: ai-interpretation-v1.0

**Location:** `tamil_panchangam_engine/app/engines/ai_interpretation_engine.py`

**Adapter:** `client/src/adapters/aiInterpretationAdapter.ts`

### Structure

1. **Window Summary (Level 1)**
   - Momentum (positive/neutral/negative)
   - Overview text
   - Outcome mode
   - Timing guidance

2. **Life Areas (Level 2)**
   - career
   - finance
   - relationships
   - health
   - personal_growth

   Each area contains:
   - Score (0-100)
   - Outlook (favorable/neutral/challenging)
   - Summary
   - Deeper explanation (explainability-gated)

### Explainability Modes

**Filter:** `tamil_panchangam_engine/app/engines/explainability_filter.py`

| Mode     | Visibility                                      |
|----------|------------------------------------------------|
| minimal  | Summary only                                   |
| standard | Summary + explanation (hide signal attribution)|
| full     | Complete output with all attribution           |

**UI Toggle:** Available on prediction screens

---

## Prediction Engines (10 Signal Sources)

1. **Transit Engine** - Current planetary positions relative to natal chart
2. **Aspect Engine** - Planetary aspects and drishti
3. **Yoga Engine** - Classical yoga formations
4. **House Strength Engine** - Bhava strength calculations
5. **Dasha Engine** - Vimshottari dasha periods
6. **Nakshatra Engine** - Tara bala and nakshatra context
7. **Gochara Engine** - Transit effects from Moon
8. **Ashtakavarga Engine** - Bindhu-based strength
9. **Functional Role Engine** - Yogakaraka/Maraka planets
10. **Pancha Pakshi Engine** - Daily rhythm guidance

---

## Data Flow

```
Birth Chart (immutable)
    ↓
Prediction Envelope (temporal signals)
    ↓
Synthesis Engine (weighted combination)
    ↓
AI Interpretation Engine
    ↓
Explainability Filter
    ↓
Frontend Adapter → UI
```

---

## Last Updated

2026-01-23: Added BirthAstroContextTable and AI Interpretation v1.0 consumption
