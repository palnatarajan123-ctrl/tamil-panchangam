# TamilPanchangam Astrology App

## Purpose
A Tamil Panchangam-based astrology application providing daily/monthly
Panchangam calculations including Tithi, Vara, Nakshatra, Yoga, and Karana.

## Stack
(fill in: Python/Node, any frameworks, DB if any)

## Domain Glossary
- **Tithi**: Lunar day (30 per lunar month)
- **Vara**: Day of the week (with planetary rulers)
- **Nakshatra**: Lunar mansion (27 total)
- **Yoga**: Combined sun-moon longitude calculation
- **Karana**: Half of a Tithi
- **Rahu Kalam / Yamagandam**: Inauspicious time periods

## Current MVP Status
Migrated from Replit. Core calculations working.

## Next Priorities
(list your goals here)

Before writing any new engine that reads base_charts.payload,
always run this first to see actual structure:

SELECT jsonb_pretty(payload) FROM base_charts LIMIT 1;

Key paths:
  birth_details.latitude / longitude / timezone
  ephemeris.moon.nakshatra.index
  ephemeris.moon.longitude_deg
  ephemeris.lagna.longitude_deg
  chart_metadata.ayanamsa
  chart_metadata.node_type
  dashas.vimshottari.timeline
  PK column: id (not base_chart_id)

  ## Daily API patterns (learned from daily.py)

- Route handlers are SYNC def, not async def
- LLM enabled check: from app.engines.llm_interpretation_orchestrator 
  import is_llm_enabled (NOT budget_guard)
- log_llm_call signature: log_llm_call(db, chart_id, call_type, 
  period, input_tokens, output_tokens)
- Daily response keys: nakshatra, tara_bala, rahu_kaalam, tithi
  (NOT vara, dinaphalam_score, weekday, today_nakshatra)
- Daily component filename: DailyView.tsx 
  (NOT DailyPanchangamView.tsx)
- PK column on base_charts: id (NOT base_chart_id)
- Payload paths (always read actual DB before writing .get() calls):
    birth_details.latitude / longitude / timezone
    ephemeris.moon.nakshatra.index
    ephemeris.moon.longitude_deg
    ephemeris.lagna.longitude_deg
    chart_metadata.ayanamsa
    chart_metadata.node_type