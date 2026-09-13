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
- **`AuthContext.tsx`'s `googleLogin()` has zero callers anywhere in the
  frontend** — dead code, found during the 2026-09-11 login-race
  investigation (Task 1 reopened). Previously only noted in that fix's
  commit message (`03aecfc`), not actually recorded here — fixed
  2026-09-11. Would have the identical `navigate()`/`setUser()` race that
  bug was about if it were ever wired up (it calls `setUser()` the same
  way `login()`/`register()` do), so if someone adds a Google sign-in
  button later, route it through the same effect-driven `GuestRoute`
  pattern those two already use — don't add an imperative `navigate()`
  next to it.
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
- **`life_area_scorer.py`'s `top_signals` silently excludes every
  yoga/dasha-activation/Ashtakavarga signal from a life area's scoring
  breakdown** — found 2026-09-11 while investigating (and fixing, see
  `_momentum_from_score` in `ai_interpretation_engine.py`) the front/back
  Overview-contradiction bug. `LifeAreaScorer.score_one()` computes each
  signal's contribution as `(house_w + planet_w) * strength * src_bias *
  val_mult`, then only appends it to `contributions`/`top_signals` `if
  abs(raw) > 0`. Yoga (`YOGA_DHANA`, `YOGA_RAJA`), Ashtakavarga
  (`ASHTAKAVARGA_STRONG_SUPPORT`), and Yogakaraka-activation signals
  carry no `house`/`planet` field in their raw dict, so `house_w` and
  `planet_w` are both `0.0` regardless of the signal's real `strength` —
  `raw` is always exactly `0`, so these signals can never enter
  `top_signals` for ANY life area, no matter how strong. Confirmed via a
  real trace (4 charts, avg scores 57-77): `top_signals` for every area
  on every chart tested contained only Drishti/Gochara/house-affliction
  signals — never a yoga or dasha-activation signal, even when those
  were the dominant contributors to a high `base_score_0_100`. This
  fix only changed how the deterministic Overview text READS
  `top_signals` (switched to reading the final weighted `score`
  instead) — it did NOT touch `top_signals`' own population logic, so
  anything else that consumes `top_signals` (e.g. the "Signals" list
  shown in the legacy per-area PDF breakdown, `_get_relevant_signals_for_area`)
  still only ever shows house/planet-tagged signals, silently omitting
  yoga/dasha ones from that display too — same root cause, different
  visible symptom, not investigated further here. Also noticed but not
  chased: for the one chart traced in detail, `top_signals` came out
  IDENTICAL across all 5 life areas (same 6 signals, same order) despite
  each area having a different house/benefic weighting config in
  `LIFE_AREA_WEIGHTS` — expected if those specific signals happen to
  outrank everything else for every area's weighting, but not verified
  either way. Needs its own investigation — bigger blast radius than the
  Overview fix (affects score deltas, not just narrative text, and
  potentially the "Signals" display across all three prediction periods)
  — deliberately scoped out of the Overview fix.
- **Every birth-chart-only PDF (`render_birth_chart_pdf()`) silently
  omits Sade Sati & Saturn Analysis and Shadow Points (Upagrahas)**,
  despite both sections' rendering code being present, wired in, and
  confirmed working correctly when given data. Found 2026-09-11 while
  inventorying `render_birth_chart_pdf()` for the PDF redesign (#2) and
  confirmed concretely against a real chart (`f5da25da`): both
  `data.sade_sati_data` and `data.upagrahas` come back `None` from
  `build_birth_chart_report_data()` (`data_loader.py`), so
  `_build_sade_sati_section()`/`_build_upagrahas_section()` both hit
  their early `if not data.X: return []` guard and produce nothing —
  no error, no log, just two entire sections missing from every natal
  report a user has ever downloaded. This affects ALL users of this
  report type, not one chart — it's a structural gap in the loader, not
  a per-chart data quirk.
  - **Root cause, Sade Sati**: `build_birth_chart_report_data()` reads
    `sade_sati_raw = payload.get("sade_sati")` — the STATIC base_chart
    payload, which never gets a `"sade_sati"` key written at chart
    creation (confirmed: grepped the whole function, this is the only
    place it's referenced). That's actually correct behavior for a
    static field, because Sade Sati status is NOT static — it depends
    on Saturn's CURRENT transit relative to the natal Moon, which
    changes over years. The monthly report's loader (`build_report_data()`,
    same file) gets this right: it reads `envelope.get("sade_sati")`,
    where `envelope` is `build_monthly_prediction_envelope()`'s live,
    "as-of-now" computation. The birth-chart loader needs the same kind
    of live call — and already imports and calls two structurally
    identical live engines a few lines away in the very same function
    (`compute_gochara()`, `compute_nakshatra_context()`, both called
    with a live `reference_date_utc` to build `live_transit_context`/
    `live_nakshatra`) — it just never added the equivalent call to
    `sade_sati_engine.py`'s `compute_sade_sati()`. This is a same-file,
    same-pattern fix, not a design problem.
  - **Root cause, Upagrahas**: simpler and more complete an omission —
    `build_birth_chart_report_data()`'s `CanonicalReportData(...)`
    constructor call never passes an `upagrahas=` argument at all (the
    field just defaults to `None`). No read-from-wrong-place bug here,
    just never wired in. `upagrahas_engine.py`'s `compute_gulika_mandi()`
    is already imported and called elsewhere in this same file
    (`app/api/prediction.py`'s lazy-backfill path, per this file's own
    "Payload paths" notes above) — same shape of fix as Sade Sati:
    reuse an existing engine call, not build one from scratch.
  - Not fixed here — flagged during a visual-redesign pass (Phase 0-4
    inventory for #2), deliberately scoped out since it's a content-
    completeness bug, not a styling one, and the redesign work was
    already committed to reusing the existing (working) render
    functions for these two sections unchanged. Needs its own fix,
    prioritized as a real content gap affecting every natal-only
    report, not a minor mapping oversight.
- **Ask Jyotishi chat's ungrounded-fact pattern extends beyond
  Gochara — the GROUNDING rule was verified (live LLM call) to hold for
  all three flagged question types, but the underlying DATA gaps are
  still open** (2026-09-12 fix, verified same day). The 2026-09-12 fix
  grounded `_build_chat_context()`'s Gochara/transit data specifically
  (real `compute_gochara()` call) plus a generic GROUNDING/anti-
  fabrication system-prompt rule. `_build_chat_context()` still gives
  the LLM only current dasha LORD names (no start/end dates), one
  hardcoded D10 Sun/Saturn snippet (no other divisional placements), and
  yoga NAMES only (no house/planet specifics) — none of that DATA was
  added. What WAS verified, via three real live `anthropic.Anthropic`
  calls against chart `7c6e34be`'s actual context+system prompt (not
  just prompt inspection): asked for an exact antardasha end date, a
  specific D9 Saturn placement, and the specific houses in its (real,
  present) Raja Yoga — all three got an honest "I don't have that
  specific data available"-shaped answer, no fabricated date/sign/house
  in any of them. So the rule generalizes in practice, today, for this
  chart. Important asymmetry to remember: this is instruction-compliance
  verified by sampling, not a guarantee the way Gochara's fix is — Gochara
  can no longer fabricate because it now has the real answer to state;
  these three still rely on the model choosing to follow a textual rule
  every time, for every chart, every phrasing of the question. If a
  future report shows confident fabrication on one of these three (or
  a similar ungrounded-fact question chat wasn't designed to answer),
  don't assume the rule is broken — re-test with that exact question
  first, since compliance-by-instruction isn't provably universal the
  way a data fix is. Actually grounding these (precomputed dasha
  timeline dates, fuller divisional-chart data, yoga house/planet
  detail) remains deliberately out of scope, its own separate piece of
  work.
- **Closed 2026-09-13: chat now has real future ingress (peyarchi)
  dates for Rahu/Ketu/Jupiter/Saturn, via a new `ingress_engine.py` +
  `planet_ingress_events` table** — this was the one ungrounded-fact
  gap from the list above that WAS worth closing with real data rather
  than an instruction, because (unlike dasha dates or yoga house
  detail) an ingress date is a single small global fact, not something
  that multiplies per-user or per-question. Key design point worth
  remembering: the ingress date itself ("Rahu enters Capricorn on Dec
  5, 2026") is the same for every user and computed ONCE, cached, and
  looked up cheaply at chat time (never a live ephemeris call in the
  request path) — only the resulting HOUSE NUMBER is personal, computed
  from the cached sign + the user's own Rasi/Lagna via
  `ingress_engine.house_from_sign()`.
  - `find_next_ingress()` uses coarse-then-refine, not a day-by-day
    scan: estimates an adaptive step toward the next 30° boundary from
    the planet's current speed (re-estimated every step, so it
    naturally shrinks near a station rather than assuming monotonic
    motion), then bisects once a sampled sign change is observed.
    Verified against a real, unplanned example this feature's own build
    surfaced: Saturn enters Aries on 2027-06-03, then genuinely
    retrogrades back into Pisces around 2027-10-20 before settling —
    `find_next_ingress()` correctly reports the first crossing (the
    conventionally-reported peyarchi date) and separately flags the
    retrograde return via `retrograde_return_date_utc`, matching an
    exhaustive 264-call day-by-day scan while using ~49 calls itself.
    Rahu/Ketu are always retrograde by convention and never station, so
    this check is skipped for them (`_find_retrograde_return()` returns
    `None` immediately for both).
  - `planet_ingress_events` (new table, `app/db/bootstrap.py`) stores
    `node_type` as `'mean'`/`'true'` for Rahu/Ketu (their ingress date
    genuinely differs by node type) and the literal string `'n/a'` —
    never `NULL` — for Jupiter/Saturn, specifically to keep the
    `UNIQUE(planet, node_type, to_sign, ingress_date_utc)` constraint
    (and the lazy-backfill's `ON CONFLICT ... DO NOTHING`) working:
    Postgres treats `NULL != NULL`, so a `NULL` placeholder there would
    have silently defeated deduplication on concurrent backfills.
  - Refresh is lazy-backfill-on-read (`get_upcoming_ingresses()`, same
    pattern as `upagrahas_engine.py`'s lazy backfill, not a new
    scheduled-job mechanism — none exists in this codebase to hook
    into) — always keeps the next 2 known ingresses per
    planet/node_type computed ahead of `now`; a request that finds
    fewer computes and inserts more, subsequent requests just read the
    cache. Chat only ever reads the next 1 per planet today.
  - Scope: all four gochara_engine.py-tracked planets (Rahu, Ketu,
    Jupiter, Saturn), not just Rahu/Ketu — recommended since the
    marginal cost per planet is the same small algorithm, and
    Jupiter/Saturn peyarchi questions are equally common for this
    audience (per the Shelvi Guru Peyarchi content reviewed during the
    original December-2026 investigation).
  - Verified live end-to-end: re-asked the exact real question that
    started this whole investigation ("Ragu, Kethu peyarchi for Mesha
    rasi in 2026 transition?") through the real fixed pipeline against
    chart `7c6e34be` with a live LLM call — correct answer (Rahu into
    Capricorn, 10th house from Moon sign, Dec 5 2026), no hedge needed,
    sourced from the cached table. A follow-up asking for the ingress
    AFTER that one correctly got "I don't have that specific data
    available" (with an explicitly-caveated rough estimate offered, not
    stated as fact) — confirms the fix didn't make the model
    overconfident generally, only for what's actually in the table now.
- **`ashtakavarga_engine.py` had the same Tamil/English rasi-name
  mismatch as the two bugs fixed 2026-09-12 in `gochara_engine.py`/
  `moon_transit_engine.py` — confirmed dead code in its only real
  caller, fixed anyway 2026-09-12 as cheap defense-in-depth, same day.**
  `compute_ashtakavarga_validation()`'s fallback ("estimated") branch
  (`RASI_TO_INDEX.get(birth_moon_rasi, 0)` + two template-dict lookups
  keyed the same way) only runs in the `else` of
  `if natal_positions is not None and lagna_longitude is not None`. Its
  one real caller, `prediction_envelope.py:321`, always passes
  `natal_positions=ephemeris` (`ephemeris = base_chart["ephemeris"]` at
  line 99, accessed via `[...]` not `.get()` — would already have raised
  earlier in the function if absent, so it's never `None` in practice)
  and `lagna_longitude=natal_lagna_longitude` (`ephemeris.get("lagna",
  {}).get("longitude_deg", 0.0)` — a float default, never `None`). So
  that `if` is always true and the buggy branch is unreachable from this
  caller — verified by reading both files directly, not assumed from
  the earlier investigation. Fixed anyway: all `RASI_TO_INDEX`/
  template-dict lookups in the function (both branches, not just the
  reachable one) now go through `to_english_rasi()` — same shared
  utility as the other two fixes, zero behavior change confirmed via a
  direct before/after call in both branches, plus a regression test
  (`tests/engines/test_rasi_name_conversion.py`). Was cheap (3-line
  diff, no new caller behavior to verify) specifically because the
  branch was provably unreachable, so there was no live behavior to
  regress — that's what made "fix it anyway" the right call here, not a
  general license to fix every dead-code finding on sight.

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
- **Prediction-generation spinner/status messaging is duplicated across
  two files**, same trap as the family chat note above:
  `client/src/screens/prediction-screen.tsx` (routed at
  `/chart/:id/predictions`, the one real in-app navigation reaches —
  `chart-detail.tsx` links here) and `client/src/pages/predictions.legacy.tsx`
  (routed at `/predictions/:id`, but as of the 2026-09-11 spinner-copy
  fix, confirmed to have zero in-app links pointing at it anymore — only
  reachable by a direct/bookmarked URL, not truly dead like
  `predictions_ui.py` was, just orphaned). Both independently derive
  `llmPending` from the same `llm_status === "pending"` response field
  and render their own copy of the "Generating your interpretation…"
  spinner — fixing the wording in one and missing the other reproduces
  this exact mistake. Third/fourth occurrence of "multiple independent
  copies drift" in this project (family chat, bare-`fetch()` call sites,
  PDF download, now this) — see the PDF-consolidation backlog entry
  above for the same underlying suggestion (one shared component/helper)
  applied to a different surface.
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
- **`ephemeris.moon.rasi`/`ephemeris.lagna.rasi` on every chart payload
  are stored in TAMIL** (`ephemeris.py`'s `get_rasi()`/`RASI_NAMES`), but
  several engines (`gochara_engine.py`, `moon_transit_engine.py`) key
  their house-counting lookups in ENGLISH. Passing a Tamil rasi string
  into one of those silently defaulted to index 0 ("as if Moon is in
  Aries") instead of raising — fixed 2026-09-12 via
  `app.utils.rasi_utils.to_english_rasi()`, now the single conversion
  point (normalizes inside the lookup functions themselves, so every
  caller is covered, not just known ones). If you add a new engine that
  compares a rasi name read from a chart payload against an
  English-keyed table (`RASI_TO_INDEX`-shaped), run it through
  `to_english_rasi()` first — don't assume the payload's rasi is already
  in whatever naming scheme your lookup uses.
- **Transit/Gochara computations must thread `node_type` from the
  chart's own `chart_metadata.node_type`, not assume a default** — fixed
  2026-09-12: `swisseph_utils.py` used to hardcode `swe.TRUE_NODE` for
  Rahu regardless of the chart's setting, while the natal engine
  (`ephemeris.py`) already defaulted to mean node (the documented
  traditional-Tamil-astrology convention). `compute_planet_longitude()`/
  `compute_planet_longitude_with_speed()` now take `node_type` (default
  `"mean"`); every real Rahu/Ketu transit call site threads the chart's
  actual value through. A future transit-computing engine that skips
  this (hardcodes a node type, or doesn't accept the parameter at all)
  reintroduces the exact bug that moved Rahu's real Dec 2026 Capricorn
  ingress ~10 days early.
- **A 0-sign-offset chart (Rasi == Lagna) cannot prove the Lagna-rasi
  Tamil→English conversion is working** — investigated 2026-09-13 after
  a second real chart (`fd79efb3-87e8-4533-bec3-0c3d5396ce53`) looked
  suspicious (Ask Jyotishi stated the same house number "from both your
  Moon sign and Ascendant"). Ground truth: this chart's Rasi AND Lagna
  are genuinely both Mesham/Aries — not a bug, same situation as
  `7c6e34be` earlier. But the reason it's *structurally* untestable is
  worth remembering: `RASI_TO_INDEX` uses index 0 for Aries, so an
  unconverted Tamil Lagna silently defaulting to "Aries" (the bug's
  failure mode) and a REAL Aries Lagna produce byte-identical output —
  no 0-offset chart can distinguish "conversion worked" from "conversion
  is silently broken but happens not to matter here." Re-verified the
  three non-Aries-Lagna charts checked the previous night
  (`954f9482`/`7916f261`/`d6a77175`) against the actual buggy-vs-correct
  arithmetic (not just "different from the moon-house number") and
  confirmed all three match the correct Lagna-index formula, ruling out
  the same masking risk for them. Also found gochara_engine.py's
  `_house_from_moon()`/`_transit_natal_house()` normalize their inputs
  internally (added as defense-in-depth in the 2026-09-12 fix) — so
  even a hypothetical regression in chat.py's own `to_english_rasi()`
  call wouldn't currently reach a real user; confirmed this doesn't
  mean it's fine to skip the conversion at the call site (redundant
  layers are the point, not proof either one is unnecessary).
  `tests/api/test_chat_gochara_grounding.py`'s
  `test_chat_context_passes_already_english_lagna_to_compute_gochara`
  mocks `compute_gochara()` directly to isolate and pin chat.py's own
  conversion specifically, since the engine-level safety net masks a
  chat.py-level regression in any test that only checks final house
  numbers (confirmed by literally reintroducing the bug and watching
  the end-to-end test still pass).

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