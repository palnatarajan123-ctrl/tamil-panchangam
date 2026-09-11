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
- **Several screens still use a local bare `fetch()` + manual
  `authHeaders()` instead of the shared `apiRequest()` helper** —
  `family-timeline-screen.tsx`, `children-timing-screen.tsx`,
  `family-screen.tsx` (has its own local `apiFetch()` reimplementation,
  not just an inline call), `child-prediction-screen.tsx`,
  `RerunLLMButton.tsx`, `useChat.ts`. Found during the 2026-09-11 PDF
  auth investigation (Issue 1) while checking for other instances of the
  same bug class. Lower severity than Issue 1's `window.open()` calls —
  these DO send a token, so they're not "always 401" — but they miss
  `apiRequest()`'s auto-refresh-on-401 retry, so any of them can fail for
  a user with a just-expired access token. Not fixed now (out of scope
  for a PDF-specific bug), same class as the already-fixed
  `family-prediction-screen.tsx` instance.
- **Weekly/yearly prompt-token margins weren't re-verified after the
  Issue 2 fix** (2026-09-11, `payload_builder.py`'s `MAX_PROMPT_TOKENS`).
  Monthly was confirmed stale (0 real margin against a real chart) and
  raised 2000→2600; weekly (600-token margin) and yearly (1500-token
  margin) look comfortable by the same total-budget-minus-completion
  arithmetic, but that's arithmetic, not a real measured payload the way
  monthly's fix was. `test_payload_size_validation.py`'s
  `test_monthly_prompt_cap_has_real_margin_under_total_budget` already
  checks the margin invariant for all three periods going forward, so a
  future regression there won't go unnoticed the way this one did — but
  if weekly/yearly ever show the same "existing chart fine, new chart
  stuck on an old version" symptom, check this file's `MAX_PROMPT_TOKENS`
  first before assuming a new root cause.
- **Stale fallback-tagged cache rows (2026-09-11 follow-up to Issue 2,
  fixed at the `prediction.py` layer) may still have a matching latent
  issue one layer down**, in `llm_interpretation_orchestrator.py`'s
  `_check_cache()`: it special-cases `fallback_reason == "llm_disabled"`
  as always-reusable, regardless of whether `is_llm_enabled()` is
  CURRENTLY true — meaning if LLM was off when a period was first
  generated, then re-enabled later, `_check_cache()` would still hand
  back the stale disabled-era fallback if it's ever reached with that
  cache key again. `prediction.py`'s own retry trigger (this fix) doesn't
  carve out this same exception, so in practice `_check_cache()` won't be
  reached with a stale `llm_disabled` row anymore for Monthly — but
  Yearly calls `generate_llm_interpretation()` (and therefore
  `_check_cache()`) directly and unconditionally on every request, so
  this exact latent inconsistency may still be live there. Not verified
  either way — flagging, not fixed, since it's one layer deeper than
  tonight's fix and wasn't the reported symptom. Still true after Part A's
  consolidation below -- `_check_cache()` itself wasn't touched, only the
  single-source-of-truth gate one layer above it.
- **Dead duplicate token-limit implementation**: `token_estimator.py`'s
  `check_token_limits()`/`get_max_completion_tokens()`/`MAX_TOTAL_TOKENS=10000`
  are imported into `llm_interpretation_orchestrator.py` but never called
  anywhere -- the actually-enforced path is `payload_builder.py`'s own
  separate `validate_payload_size()`/`MAX_PROMPT_TOKENS` dict, with
  different numbers (`token_estimator.py` uses flat 6000/10000, not
  period-specific). Found while investigating whether the "3000-token
  ceiling" referenced in the Issue 2 fix was a real constraint (it isn't
  -- see below). Not fixed -- confusing but inert, someone reading
  `token_estimator.py` in isolation could mistake it for live enforcement.
- **`MAX_TOTAL_TOKENS`/`MAX_COMPLETION_TOKENS` (`payload_builder.py`) are
  self-referential, not hard constraints** (2026-09-11, Part B of the
  same follow-up): confirmed by tracing where they're actually used --
  `MAX_TOTAL_TOKENS` is read ONLY inside `validate_payload_size()`'s own
  check, nowhere else. It's not Claude's model context window (~200K
  tokens, far larger), not `budget_guard.py`'s dollar cap, and not
  `llm_interpretation_orchestrator.LLM_MONTHLY_TOKEN_BUDGET` (a separate
  1M-token/month quota) -- it's exactly as arbitrary as the original 2000
  figure was, just one level removed, with the same incremental-bump
  history (its own comments: "raised to accommodate v7 completion
  headroom"). 2600 (Monthly's new `MAX_PROMPT_TOKENS`) is confirmed to
  have real margin against two genuinely fresh, real charts measured
  after the fix (1841 and 2001 estimated tokens -- 599-759 tokens of
  headroom, ~23-29%) -- comfortable, not huge. If future prompt growth
  pushes real charts noticeably above ~2200-2300, re-measure rather than
  assume the margin still holds (same instruction already in
  `payload_builder.py`'s comment on the constant itself).
- **PDF download call-site consolidation**: `window.open()` was the root
  cause of Issue 1 (can't attach Authorization header) — this is the
  third instance of the "multiple independent copies drift" bug class in
  this project (two family-chat implementations, six bare-`fetch()` call
  sites, now PDF). Consider a single shared `downloadAuthenticatedFile()`
  helper (fetch + blob + programmatic download) used everywhere instead
  of ad-hoc `window.open()`/`fetch()`/`apiRequest()` mixes for file
  downloads specifically. Finding, not a fix — not built.
- **Hardcoded version-string gating is fragile**: Issue 3's root cause
  was `"v4"/"v5" in engine_version` silently failing to match v6/v7 with
  no error, just quiet degradation. Worth a repo-wide grep for other
  places gating logic on a hardcoded version-string allowlist rather than
  checking response shape/structure — same failure mode (works, then
  silently breaks on the next version bump) could be lurking elsewhere.
  Finding, not a fix — not built.
- **Ownership sweep test gap, generalized**: `test_ownership_sweep.py`
  proved "authenticated owner gets 200" for base-chart/predictions/
  prospects/family — PDF endpoints were missing from that list until
  Issue 1 forced adding one. Worth a deliberate pass confirming every
  endpoint requiring auth has a corresponding "real valid token → real
  200" test, not just the rejection-path coverage from the original auth
  sweep. Don't build this — it's a breadth-check across the whole API,
  not a quick add.

## 2026-09-11 regression investigation retrospective (Issue 4)

Four issues investigated in one pass; git history (`v3.3.1-auth-followup..HEAD`
against every relevant file) confirmed upfront that none were caused by
that session's own commits — all three real bugs found were pre-existing,
just newly surfaced by more thorough manual testing. What let each one
through, and whether the added test actually closes that shape of gap
(not just the specific bug):

- **Issue 1 (PDF "Not authenticated")**: the gap was a missing
  *authenticated-success-path* assertion, not a missing route. The auth
  sweep (backlog #2) already proved these routes reject unauthenticated
  requests — and still does; that was never broken. What no test
  checked: does a real, valid, correctly-attached token actually reach
  the route at all. A client-side bug (`window.open()` can't attach an
  `Authorization` header) is invisible to any backend-only test, sweep or
  ownership-scoped alike, no matter how thorough — the token simply never
  arrives. `test_pdf_auth_success.py` adds the missing owner-gets-200
  half for PDF specifically; it does NOT retroactively cover the other
  authenticated routes that might have the same "only rejection tested,
  never success" gap — that was a quick spot-check (see the bare-`fetch()`
  note above), not an audit.
- **Issue 2 (Monthly stuck at v1.0)**: the gap was that
  `payload_builder.py`'s size-validation threshold had zero test coverage
  at all, at any size. A fixture built from "a new chart" vs "an old
  chart" would have missed this regardless, because the bug was never
  about chart age — it was payload size proximity to a threshold that
  drifted stale as the payload-building logic grew richer. The first
  version of `test_payload_size_validation.py` written for this
  investigation used a hand-approximated fixture that measured 818
  tokens against a 2000-token threshold — nowhere near the boundary, it
  would have passed whether the bug was fixed or not. Rewritten to use
  `extract_payload_inputs()`'s actual output from the real chart that
  reproduced the bug (`fixtures_monthly_payload_inputs.json`) instead of
  approximated data, plus a structural margin-invariant test so the
  *threshold* itself is guarded going forward, not just this one
  chart's numbers.
- **Issue 3 (chat context)**: not a coverage gap in the same sense — no
  test previously covered `_build_chat_context()`'s monthly/yearly
  summary extraction at all for any version. Found by direct inspection
  while verifying the parameter-passing the task asked about, not by a
  failing test. `test_chat_context.py` now covers v7 (current), v4 (no
  regression), and the graceful-fallback path when `executive_summary` is
  absent/malformed.
- **Cross-cutting lesson**: two of three real bugs (Issues 1 and 2) were
  invisible to look-for-rejection-only tests. A sweep or ownership test
  proves "wrong things are refused" — it says nothing about "right things
  are accepted correctly," and that second half needs its own explicit
  assertions, route by route, not an assumption that passing the first
  half implies the second.

**Confirmed, not a bug**: `family.py`'s family-group chat
(`family_group_chat_stream()`) does not share Issue 3's stale
version-check — it builds its per-member context differently (via
`payload_builder.py`'s shared helpers per the two-chat-implementations
note below), not through `chat.py`'s `_build_chat_context()`. Checked,
not assumed, given this file's own standing warning that a fix to one
chat implementation doesn't reach the other.

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

**"Login requires two submits" — superseded, actually fixed, see commit
`03aecfc`** (the entry that used to live here said "closed stale, not
fixed" as of 2026-09-10 — wrong, corrected 2026-09-11 once new evidence
reopened it). The 2026-09-10 investigation correctly found the Turnstile
hypothesis false, but closed the whole issue on a headless-only trace
that couldn't reproduce it — exactly the kind of premature closure this
file's own header warns about. Real root cause, found 2026-09-11: login.tsx
called `navigate("/")` immediately after `setUser()` in the same
synchronous block; wouter's `navigate()` triggers an unbatched
`dispatchEvent()` (confirmed in wouter's own source, with the
maintainers' own TODO acknowledging it), which could force `AuthRoute` to
re-render on a stale `user = null` before React flushed the pending
`setUser()` update, silently bouncing back to `/login`. Fixed by removing
all imperative navigation from login/register and adding `GuestRoute`
(effect-driven, mirroring `AuthRoute`'s already-correct pattern). Real
Chrome-for-Testing browser confirmed: single submit, `/login` → `/` in
~925ms, no bounce. See `client/src/__tests__/auth-navigation-race.test.tsx`
for the regression test and its own documented limitation (a headless
repro couldn't be made to fail against a reintroduced bug via realistic
DOM-driven interaction — real-browser testing is what actually closed
this, not the automated suite alone).

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
- **`is_llm_enabled()` (`llm_interpretation_orchestrator.py`) is THE
  single source of truth for "may the LLM be called right now, anywhere"
  — as of 2026-09-11, not before.** It used to check only
  `llm_config.llm_enabled` (the admin's manual toggle); a completely
  separate flag, `llm_budget.llm_enabled` (auto-pause when $ spend
  crosses the configured threshold, set by
  `budget_guard._check_budget()`), was checked independently via raw SQL
  in three places (`chat.py` once, `family.py` twice) — meaning those
  three never reliably respected the manual toggle (only via a
  best-effort, swallowed-exception sync in `admin_llm.py`'s `/toggle`),
  and conversely every OTHER LLM call site (`natal_interpretation.py`,
  `daily.py`, `prediction.py`, the orchestrator itself) never respected
  the budget auto-pause at all. Now returns `False` if either source
  says off. If you're adding a new LLM-calling code path, call
  `is_llm_enabled()` — never re-query either table directly, never
  reimplement this check. Need the human-facing reason it's off (not a
  gating decision)? Use `get_llm_pause_reason()`, same file.
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