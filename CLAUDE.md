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
- **`app/api/predictions_ui.py` is dead code** — its `router` (prefix
  `/ui`) is never imported into `main.py`, so `POST /api/ui/predictions`
  doesn't exist in the running app. Found during the 2026-09-10 auth
  sweep test (backlog #2) while enumerating every mounted route. Not a
  live gap (unreachable), just noting it here so it isn't mistaken for a
  missing-auth finding by someone skimming `app/api/` later — either wire
  it in or delete it, don't "fix" its auth in place believing it's live.
- **`POST /api/auth/refresh` has no rate limit at all** — unlike
  `/api/auth/google`'s `10/hour` (both are legitimately unauthenticated
  by design; the body token is the credential — see backlog #2's sweep
  test). Same bot-verification/budget-exposure bucket as Task 3's
  register-Turnstile work; not a Turnstile candidate itself since refresh
  is machine-driven, not human-driven, but worth a rate limit given a
  stolen/guessed refresh token could otherwise be hammered without limit.
- **Per-account daily LLM cap (`budget_guard.check_user_llm_cap()`,
  landed 2026-09-10) is only wired into 3 routes** —
  `daily.py`'s `/prediction/daily`, `natal_interpretation.py`'s
  `/natal-interpretation` and `/{chart_id}/kp-interpretation`. NOT wired
  into `chat.py`, `family.py`'s family-group chat/predictions, or the
  engine-layer `log_llm_call()` sites (`children_timing_engine.py`,
  `child_prediction_engine.py`, `family_prediction_engine.py`,
  `payload_builder.py`) — threading `user_id` through those means
  changing signatures several call-frames deep, deliberately scoped out
  rather than done half-carefully in the same pass. A capped account can
  still exhaust budget through any of those paths today.
- **`admin_llm.py`'s `/budget` endpoint doesn't expose
  `llm_budget.per_account_daily_cap_usd`** (added alongside the
  per-account cap above) — an admin can currently only edit
  `monthly_budget_usd` via the API; changing the per-account cap requires
  a direct DB update. Same singleton-row pattern as the existing field,
  straightforward to add to that endpoint's request/response models when
  someone needs it.

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
- "Login requires two submits" (was: Turnstile token not ready before
  submit enabled) — investigated 2026-09-10, closed stale, not fixed.
  The premise was wrong on both counts: the login screen isn't under
  `client/src/screens/` (it's `client/src/pages/login.tsx`), and
  Turnstile is wired into nothing in the login flow, client or server —
  it only gates `base_chart.py`'s `/create` route. Full static trace
  ruled out all three hypothesized mechanisms (Turnstile gate, silent
  error-handling, stale closure); automated repro via curl, both locally
  and against the live prod Vercel+Render stack, got a clean 200 on
  attempt #1 every time, no delay, no lockout. Don't re-open on the
  Turnstile hypothesis; if it resurfaces, check Render's cold-start
  behavior (free-tier services spin down after ~15min idle) instead.

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