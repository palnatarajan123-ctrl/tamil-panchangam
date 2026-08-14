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

**Pending backlog** (verify against actual code before starting any of
these — this list has been wrong before; see "Gulika/Sani Oorai" and
"family surfaces" audits in git history, 2026-08-14, for what "confirmed
stale" and "confirmed real" looked like in practice):

- **Night-birth Gulika (Mandi)** — `_MANDI_NIGHTTIME_SEGMENT` in
  `upagraha_engine.py` exists but is unwired. Deferred, not guessed at:
  the daytime table's mechanism (a continuous Saturn→Jupiter→Mars→Sun→
  Venus→Mercury→Moon cycle spanning all 56 weekly daytime segments,
  no per-day reset) exactly reproduces all 7 verified daytime values, but
  extending that same cycle into night segments gives a table that
  disagrees with the existing (unvalidated, no-citation) code table by a
  consistent 2-segment offset on every day. No third-party source found
  with an explicit night-specific table to break the tie. Affects 10 of
  24 charts (41.7%) — real blast radius, not a rare edge case. Needs an
  authoritative source (or a domain expert) before wiring anything in.

**Considered and closed, not pending** (investigated with real data
2026-08-14 — don't re-open without new evidence):
- Chat history cap (was: "reduce to 6 messages") — already capped at 12
  (`chat.py`, `family.py`), and real usage data (126 logged sessions)
  shows the longest session ever recorded is 2 messages, average 1.98.
  Tightening the cap would save zero real tokens.
- predictive_signals/KP for non-anchor family chat members — deliberately
  declined for cost (multiplies per-member, unbounded with family size,
  for the lowest-value case). Reaffirmed given the history-cap finding
  above showed no token headroom elsewhere to justify adding cost here.

## Architecture notes (learned the hard way — read before assuming)

- **Two separate family chat implementations exist.** `chat.py`'s
  `chat_stream()` (POST `/api/chat/stream` with `group_id` set) is used by
  `family-screen.tsx`. `family.py`'s `family_group_chat_stream()` (POST
  `/api/family/groups/{groupId}/chat/stream`) is a fully independent
  implementation — own system prompt, own per-member context builder —
  used by `children-timing-screen.tsx`, `family-timeline-screen.tsx`,
  `family-prediction-screen.tsx`, and `child-prediction-screen.tsx`. A fix
  to one does NOT reach the other; check both before declaring a family
  chat feature "done." (Found 2026-08-14 when a fix to the first missed
  the second, serving 4 screens, entirely.)
- Shared per-member family-context logic (yogas/upagraha) lives in
  `app.llm.payload_builder._build_family_yoga_upagraha_suffix()`, used by
  both implementations above. Their *base* fields (nakshatra/rasi vs
  lagna/moon, sade-sati-always-shown vs conditional) are NOT unified —
  they'd already diverged before anyone looked; don't assume they match.
- `family_predictions` caches per `(group_id, year)` only — no version
  history is kept. A regeneration overwrites the single row for that
  group/year; `prompt_version` gates whether a *read* is treated as
  current, it doesn't preserve old rows the way `prediction_llm_interpretation`
  does for individual charts.

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