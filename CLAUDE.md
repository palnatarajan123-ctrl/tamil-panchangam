# TamilPanchangam Astrology App

## ⚠️ ACTION ITEMS — HUMAN REQUIRED, OUTSIDE THIS REPO'S REACH (2026-09-15)

These two items cannot be completed by working in this codebase alone —
each needs a human to act on infrastructure/scheduling outside this
environment. Read this section first.

1. **URGENT — redeploy the live production server now.** Commit
   `d2661c7` raised `LLM_MONTHLY_TOKEN_BUDGET` from 1,000,000 to
   3,500,000 (`llm_interpretation_orchestrator.py:39`) to fix a live
   incident: real users generating fresh monthly/yearly/weekly
   predictions were silently getting a degraded, deterministic-only
   fallback instead of a real LLM-authored result, with no user-facing
   indication. **That fix is committed to source but has NOT taken
   effect for real users yet** — it only applies once the actual
   deployed server process is restarted/redeployed; a source-only
   change does not affect an already-running process, and this
   environment has no access to that deployment (no local server
   process found; this app was migrated from Replit and is deployed
   separately). Until someone redeploys, real users are still hitting
   the same silent fallback as before this session's fix. This is the
   single most time-sensitive item from the 2026-09-15 work — see
   "Next Priorities" below for the full incident writeup.
2. **SCHEDULED — apply the permanent budget value of 1,500,000 on or
   after 2026-10-01, not before.** `LLM_MONTHLY_TOKEN_BUDGET` is
   currently 3,500,000 as a temporary emergency ceiling for the rest of
   September only. Do NOT apply 1,500,000 early — September's
   cumulative usage already exceeds it, so applying it before the
   October 1 monthly reset would immediately re-break real users again.
   Do NOT forget to apply it at rollover either — with no admin
   dashboard or alert for this budget (see "Next Priorities" below), the
   temporary 3,500,000 will simply persist by default if nobody changes
   it, silently undermining the capacity-planning work done to size
   1,500,000 as the right permanent number. Whoever owns deploys/ops for
   this app needs a reminder for 2026-10-01 — none exists automatically.

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

- **2026-09-18 life-event-predictions investigation (marriage timing,
  children, married-life quality, wealth events, health events) —
  2 wiring gaps FIXED, 3 domains + 1 live grounding risk confirmed and
  reported, NOT built.** These are discrete, dasha-timing-based
  natal-chart predictions, a genuinely different feature class from the
  existing 5-area periodic scores (which are transit-modulated, not
  discrete-event).

  | Domain | Exists? | Wired to reports? | Wired to chat? |
  |---|---|---|---|
  | Marriage timing (primary chart) | Partial — 7th lord identified generically, no dasha-timing analysis; Upapada Lagna computed (`special_lagnas_engine.py`) but confirmed **zero consumers anywhere in the codebase**; Darakaraka (Jaimini) absent entirely | No discrete report | No |
  | Children — likelihood/timing | **Yes** — `children_timing_engine.py` does the real classical technique (5th house/lord + Jupiter Putra Karaka dasha windows) | Yes (dedicated endpoint + PDF, though the PDF has no UI download button, per the earlier 2026-09-14 surface-matrix audit) | **Fixed today** (was: no) |
  | Married-life quality | Partial — generic 7th-house/Venus/Jupiter affliction already folds into the periodic Relationships score; D9 dignity exists chart-wide, not 7th-lord/Kalatra-Karaka-specific | No discrete report | No |
  | Wealth — discrete events | Not implemented — `event_windows` is the same generic 5-area periodic confluence mechanism, no 2nd/11th-house dasha-activation-specific timing | No | No |
  | Health — discrete events | Not implemented — same generic periodic mechanism, no 6th/8th-house dasha-timing vulnerability-window mechanism | No | No |

  **Fixed (pure wiring, no methodology change, no sign-off needed)**:
  1. `children_timing_engine.py`'s already-computed, already-cached
     analysis is now surfaced into `family.py`'s
     `family_group_chat_stream()` via `_build_children_timing_chat_block()`
     -- a read-only cache lookup (same default year window
     `get_children_timing()` uses), deliberately never triggering a
     fresh `run_children_timing()` computation from the chat path (that
     has its own LLM call). Before this, asking family chat "when might
     we have children?" had nothing to ground on even when the real
     answer was already cached.
  2. `chat.py`'s `divisional_summary` always claimed to cover "D10/D2/D7"
     in its own comment but only ever extracted D10 (Sun/Saturn) --
     confirmed by direct code read, not assumed. D7's Jupiter placement
     (already labeled `"d7_children"` and given to monthly/yearly REPORT
     generation via `payload_builder.py`'s `_extract_divisional_signals()`)
     never reached chat at all. Now reuses that same shared extractor
     for D10/D2/D7 instead of a second, incomplete, hand-rolled copy.

  **CLOSED 2026-09-19 — marriage-timing and health-events now have real
  dasha-window computation, wired into every consumer.** Two new
  engines generalize `children_timing_engine.py`'s proven 5th-lord/
  Jupiter pattern (real Dasha/Antardasha windows per classical
  significator, handed to the LLM as citable facts, never a single
  invented verdict):
  - `marriage_timing_engine.py`: 7th house lord (from Moon, same
    convention as `_get_house_lord()`), Darakaraka (Jaimini -- lowest
    degree-within-sign among the 7 classical grahas, Rahu/Ketu
    excluded, deterministic tiebreak), and Kalatra Karaka (Parashari --
    Venus for a male native, Jupiter for a female native). Each gets
    its own real bounded Dasha-window list via
    `children_timing_engine._find_planet_dashas()`, reused directly
    (fully planet-agnostic already).
  - `health_events_engine.py`: 6th house lord (disease/daily struggle)
    and 8th house lord (longevity/chronic), both from Moon, same
    dasha-window computation, plus a real natal-affliction check
    (whether a natural malefic -- Saturn/Mars/Rahu/Ketu -- occupies the
    6th/8th house itself).

  **Design decision -- how multiple, possibly-disagreeing signals
  combine**: neither engine synthesizes a single verdict itself (same
  choice `children_timing_engine.py`'s own "combined_windows" already
  made). Each returns raw per-significator facts; the LLM narrative
  layer is required (via a `"basis"` field in the JSON schema) to name
  which specific significator(s) and window(s) back any date claim it
  makes, and must return `null`/an empty list rather than invent a date
  when no real window falls in the requested range. This was chosen
  over having the engine pre-merge signals into one window because the
  significators can legitimately disagree (e.g. 7th lord dasha in one
  range, Darakaraka dasha in another) and collapsing that into a single
  number would itself be a kind of fabrication -- citing the specific
  basis lets a reader judge the claim's strength themselves.

  **Confirmed data-model gap, not silently guessed around**: this app
  collects no gender field anywhere (`base_charts`, `family_members`,
  `birth_details` -- checked directly, none). Kalatra Karaka requires
  gender, so it's only computed for family members with
  `role='husband'`/`'wife'` (inferred from role); for individual charts
  and `role='child'` members it's correctly omitted rather than
  guessed, and the prompt/system-prompt both say so explicitly.

  **Wired into every consumer**: `child_prediction_engine.py`'s
  `_build_child_context()` now includes real "Marriage Timing Signals"
  and "Health Event Signals" sections (removed the old bare "7th
  (Marriage): {lord name}" line, now redundant/superseded);
  `child_prediction_prompt.txt`'s schema requires a `"basis"` citation
  for both `marriage_window` and `health_cautions` and instructs `null`/
  `[]` over guessing. Both `chat.py` (individual-chart chat, verbose
  formatter) and `family.py` (family-group chat, compact formatter --
  the two independent chat implementations noted elsewhere in this
  file) now compute and inject these signals; `family.py`'s per-member
  gender is inferred from `role` the same way. All new/changed code has
  test coverage (`test_marriage_timing_engine.py`,
  `test_health_events_engine.py`, updated
  `test_child_prediction_grounding.py`); full suite green (708 passed).

  **Verified with real charts and live LLM calls, not just unit
  tests**: `child_prediction_engine.py` re-run for chart `b1a35180`
  (member AN Sr) produced a grounded `marriage_window` citing "7th lord
  Venus Antardasha (Jan 2026 – Jan 2027) and Darakaraka Sun Antardasha
  (Jan 2027 – May 2027)" and `health_cautions` citing "8th house lord
  Mars active as Mahadasha lord (Jan 2026 – Dec 2027)" -- both an exact
  match to the real computed windows, not paraphrased or invented.
  `chat.py` re-verified live for chart `7c6e34be`: correctly cited
  "Venus Antardasha (2032–2035)" and "Mercury Antardasha... 2028-2031"
  matching computed data. `family.py` re-verified against the real "PN
  KP" family group (`dbd3fbbd-389b-409e-b26c-a4737b627002`): husband/
  wife correctly show Kalatra Karaka, children correctly omit it (no
  gender). This IS the fabrication risk's actual fix, not just the
  2026-09-19-morning hedge below (which forced empty output as a same-
  day stopgap) -- these fields now populate with real, cited content.

  **Cached-content exposure, checked before this fix landed**: 1 row
  existed in `family_child_predictions` at fix time -- it was created
  by this session's own live-verification call above (chart `b1a35180`,
  2026-09-18 16:13 UTC) using the fixed prompt, so it already carries
  real cited windows, not fabricated ones; nothing to backfill there.
  `family_children_timing` (the feature this pattern was generalized
  from) has 0 cached rows. **No backfill needed or executed.**

  **Note, still not investigated**: `career_aptitude.peak_period` and
  `leaving_home.window` in the same prompt share the identical
  underlying weakness (a specific year/period claim from house-lord
  identity alone, no dasha-window computation) -- found while fixing
  marriage_window/health_cautions, deliberately not touched here since
  it wasn't the reported symptom and widening scope risks
  under-verifying everything. Flagging so it isn't mistaken for
  "already covered."

  **Part 3 (scoped, deliberately NOT built) -- married-life quality and
  wealth events**, since neither is causing an active fabrication
  exposure the way marriage-timing/health-events were:
  - **Wealth events**: comparable in size to `health_events_engine.py`,
    i.e. small. Same pattern generalizes directly -- 2nd house lord
    (accumulated wealth) and 11th house lord (income/gains), both from
    Moon, real dasha-window computation via the same
    `_find_planet_dashas()`. No Jaimini-karaka-equivalent complexity
    needed (unlike marriage's Darakaraka). Genuinely free bonus signals
    already computed elsewhere and just need citing, not building:
    `yoga_engine.py` already detects Dhana Yoga by name, and
    `family_prediction_engine.py` already extracts KP 2nd/11th-house
    cuspal significators for KP-verified charts -- `event_window_engine.py`
    was checked and is NOT reusable here despite the "wealth" tag
    appearing in it (it's a monthly Moon-transit/Tara-Bala favorability
    tagger, a structurally different multi-year dasha-window engine).
  - **Married-life quality** (distinct from marriage *timing*, just
    closed above -- this is "how is the marriage," not "when does it
    start"): genuinely larger and structurally different, not a
    dasha-window generalization at all. Would need a new
    dignity/affliction synthesis: 7th lord's natal dignity (reuse
    `shadbala_engine.compute_sthana_bala()`/`functional_role_engine.py`,
    same as the Gochara dispositor fix), aspects to the 7th house/lord
    (reuse `drishti_engine.py`), Kalatra Karaka's and Venus/Jupiter's
    own condition, and a Kuja Dosha (Mangal/Manglik) check -- confirmed
    this does NOT exist anywhere in this codebase today (grepped;
    `yoga_engine.py`'s only Mars-related hit is the unrelated
    Chandra-Mangala Yoga). Rough scope: a new "quality scoring" engine
    comparable to `life_area_scorer.py`'s shape (weighing multiple
    dignity/affliction signals into a score+narrative) rather than
    `children_timing_engine.py`'s shape (one dasha-window lookup) --
    larger than wealth-events, roughly the size of the two engines just
    built combined. Not started -- logged here for explicit
    prioritization, per this file's own standing rule that this class
    of decision isn't made unilaterally.

  **Historical note (fixed same-day stopgap, since superseded)**: a
  2026-09-19-morning emergency fix forced `child_prediction_prompt.txt`
  to return literal `"marriage_window": {}`/`"health_cautions": []`
  while the real engines above were being built, to immediately close
  the live fabrication risk found 2026-09-18 (the LLM had been asked
  for a specific marriage year/health period backed only by a bare
  house-lord name, no real dasha-window computation -- the same
  ungrounded-fact-fabrication shape already fixed twice elsewhere this
  session, chat.py's Gochara fabrication and family.py's ingress
  fabrication). Confirmed live/reachable at the time via
  `family-screen.tsx`'s unconditional child-predictions button routing
  to `child-prediction-screen.tsx`. Superseded by the real fix above the
  same week -- kept only as a record of the fix sequence, not as
  current behavior.

- **IMPLEMENTED 2026-09-17, backfill held pending sign-off — Gochara
  dispositor analysis** (closes the methodology gap found 2026-09-15:
  Gochara was house-position-only, the same static `JUPITER_EFFECTS`/
  `SATURN_PHASES` table applying identically to every chart with the
  same Moon-house transit, regardless of who ruled that house or that
  lord's natal condition). `gochara_engine.py`'s new
  `_dispositor_analysis()` looks up the transited house's own lord
  (from Lagna, reusing `house_strength_engine.get_lord_for_house()`),
  that lord's natal placement/dignity (reusing
  `shadbala_engine.compute_sthana_bala()`, which already combines
  exaltation/debilitation/own/friendly/neutral + kendra/trikona bonus
  into one score), and this chart's yogakaraka/maraka status for that
  lord (reusing `functional_role_engine.compute_functional_roles()`).
  Returns a bounded `strength_bonus` (+/-0.4) that modulates
  `synthesis_engine.py`'s existing Gochara signal strength the same way
  `drishti_aspect_bonus` already does -- it does not replace the base
  house-position classification, it qualifies it.
  `prediction_envelope.py`'s Functional Role step was moved earlier
  (step 6B, before Gochara) since it only needs `ephemeris`/`houses`
  and Gochara now needs its output.

  **Verified**: real two-chart differentiation proof (charts
  `cc8325b8` and `fca1abca`) -- identical base Saturn transit (same
  phase `kantaka_sani`, same "challenging" effect, same Moon-house 7),
  identical dispositor lord and natal placement (Jupiter, own_sign),
  but different chart-specific functional role (yogakaraka vs. maraka)
  produces genuinely different final signal contribution (-0.724 vs.
  -0.506) -- exactly the differentiation this gap was about, and a test
  case that was structurally impossible to write before this fix. Real
  before/after across all 38 charts: 190 (chart, area) comparisons,
  average |delta| 0.332 (appropriately modest -- a modulation of
  existing signals, not a new signal category like the top_signals
  fix), 54/190 scores changed, 3/190 crossed a label boundary. See
  `tests/engines/test_gochara_dispositor_analysis.py`.

  **Chat wiring**: `chat.py`'s `compute_gochara()` call and system-prompt
  "CURRENT TRANSITS" text both updated -- the LLM now gets the
  dispositor's condition as a real grounded fact (see
  `tests/api/test_chat_dispositor_grounding.py`). `family.py` has
  **zero** Gochara/current-transit grounding at all (confirmed: no
  `compute_gochara` reference anywhere in that file) -- a separate,
  already-partially-known gap distinct from the ingress/peyarchi fix
  already ported there; this dispositor fix has nothing to attach to
  until that base gap is closed.

  **Backfill NOT executed -- held pending explicit sign-off**, same
  category of decision as the `top_signals` fix (methodology change to
  cached prediction content). Scope: all 65 `monthly_predictions` + 12
  `yearly_predictions` (77 total; `weekly_predictions` has 0 cached rows
  currently, so nothing to backfill there). Estimated cost: ~1,211,826
  tokens (~$6.70 at Sonnet 4.6 pricing), extrapolated from the
  top_signals backfill's real observed per-row average (15,738
  tokens/row). **Cannot safely run right now even with sign-off**: only
  926,810 tokens remain under the current temporary 3,500,000 budget
  ceiling -- less than this backfill alone would need -- so running it
  today would repeat the exact same budget-exhaustion incident. Needs
  either the emergency ceiling raised further or to wait until closer
  to the October reset.
- **RESOLVED 2026-09-15 (was URGENT/LIVE) — the app's shared, site-wide
  `LLM_MONTHLY_TOKEN_BUDGET` was exhausted mid-backfill, affecting real
  users; raised, both blocked backfills completed, and a permanent
  right-sized value decided (not yet applied — see below).** Original
  incident: the Ashtakavarga backfill (56 rows) pushed usage from
  428,763 (already used before the backfill started) to 1,014,767 tokens
  -- over the then-1,000,000 cap -- causing 21 of its 56 rows, and real
  users' concurrent monthly/yearly/weekly generation requests app-wide,
  to silently fall back to deterministic-only content
  (`fallback_reason: "budget_exceeded"`) with no user-facing indication.
  This budget is global and shared across ALL monthly/yearly/weekly
  prediction generation (checked inside `generate_llm_interpretation()`,
  independent of and in addition to the separate dollar-based
  `llm_budget.llm_enabled` auto-pause).

  **Fix applied**: raised `LLM_MONTHLY_TOKEN_BUDGET` to 3,500,000
  (`llm_interpretation_orchestrator.py:39`), sized to cover already-used
  tokens + projected remaining September organic traffic + the 21 stuck
  Ashtakavarga rows (~332,000) + the top_signals fix's 76-row backfill
  (~1,202,000) + 15% margin. Confirmed active for any freshly-started
  process immediately after the code change (`get_monthly_token_usage()`
  reflected the new ceiling on the next call) -- but this repo has no
  visibility into or control over the actual deployed server process
  (no local server found; this app was migrated from Replit and is
  presumably deployed separately), so **the live deployment must be
  redeployed/restarted for this to take effect for real traffic** -- a
  source-only change does not affect an already-running process. This
  is a real gap this investigation could not close from here.

  **Both blocked backfills completed after the raise**: the 21 stuck
  Ashtakavarga rows (all re-ran successfully, real content, zero
  fallbacks, 333,054 tokens) and the top_signals fix's 76-row backfill
  (75/76 succeeded immediately; 1 row -- chart `f1eb7ec4`, monthly
  2026-07 -- hit a real, unrelated pre-existing bug in
  `ai_interpretation_engine.py`'s signal-source inference, fixed
  separately, see the entry below; re-ran clean afterward, 76/76 final).
  Total real spend across all three backfill passes today (original
  56-row Ashtakavarga run + 21-row stuck rerun + 76-row top_signals run,
  including the one row's second attempt): ~2,115,070 tokens, ~$11.60 at
  Sonnet 4.6 pricing ($3/$15 per MTok) -- month-to-date usage stood at
  2,543,833/3,500,000 (72.7%) once everything finished.

  **Capacity assessment (why NOT to just revert to 1,000,000)**: real
  Sept 1-14 organic-only usage (i.e., excluding all of today's backfill
  activity) was 428,763 tokens, but concentrated on only 4 of those 14
  days (Sept 8, 11, 12, 13) -- a pattern that lines up with this
  project's own documented live-LLM investigation/verification sessions
  from that week (see the 2026-09-11 through 09-13 entries elsewhere in
  this file), so it likely overstates genuine steady-state end-user
  demand and can't be cleanly separated from it with the data available.
  Even taking it at face value, though, extrapolating that rate across a
  full 30-day month gives ~918,780 tokens -- which would leave the
  ORIGINAL 1,000,000 cap only ~8% headroom, with zero room for periodic
  admin/backfill work or organic growth. Reverting to exactly the number
  that just failed would not be a safe permanent baseline.

  **Decided permanent value: 1,500,000/month, NOT yet applied.** Chosen
  for ~58% headroom over the worst-case organic estimate above --
  meaningfully higher than the original (already shown inadequate),
  well below the one-time emergency ceiling (which included non-
  recurring backfill catch-up costs). Deliberately NOT set in code yet:
  September's cumulative usage (2,543,833) already exceeds 1,500,000,
  so applying it now would immediately regress real users again for the
  rest of this month. Must be applied manually at/after the next
  calendar-month reset (2026-10-01) -- there is no automation to do this
  or to remind anyone, which is exactly the gap the admin-visibility
  backlog entry below is about.
- **CLOSED 2026-09-15 (both) — Karana and Ashtakavarga backfills from
  the 2026-09-14 recommendation below, fully executed and verified.**
  - **Karana backfill: done, verified.** All 38 charts processed (pure
    recomputation, no LLM cost): 32 changed, 6 already coincidentally
    correct, 0 skipped. Spot-checked 2 of the changed charts against
    DrikPanchang post-backfill (Chennai chart -> Garaja, Madurai chart
    -> Naga) -- both confirmed correct.
  - **Ashtakavarga backfill: 56/56 rows now genuinely regenerated with a
    real LLM call, 0 fallbacks.** First pass got 35/56 real + 21/56
    `fallback_reason: "budget_exceeded"` (the app's shared monthly LLM
    token budget was exhausted partway through -- see the entry above);
    after the budget was raised, all 21 stuck rows were re-run
    successfully (333,054 tokens, real content confirmed, zero
    fallbacks). Real cost for the original 35: $3.02 exact (from real
    prompt/completion token counts at Sonnet 4.6 pricing, $3/$15 per
    MTok) -- within the original ~$3-4 estimate, not above it as
    initially miscalculated with a rough per-call heuristic before the
    real DB numbers were pulled.
- **RECOMMENDATION (2026-09-14) — dedicated pass: consolidate every
  remaining hardcoded rasi-name list/lookup onto the shared
  canonicalization utility (`app.utils.rasi_utils.to_english_rasi()`).**
  This is the 4th confirmed occurrence THIS SESSION of the same bug
  class (Tamil/English or inter-file Tamil-spelling rasi-name
  mismatches): (1) `gochara_engine.py`/`moon_transit_engine.py` reading
  Tamil rasi strings against English-keyed tables (fixed 2026-09-12),
  (2) `ashtakavarga_engine.py`'s same mismatch in its unreachable
  fallback branch (fixed defensively 2026-09-12), (3) the D9 divisional
  engines' own historical instance of this pattern, and now (4)
  `refined_av_engine.py`'s `RASI_NAMES` ("Midhunam", "Kadagam",
  "Simham") silently disagreeing with `ephemeris.py`'s own
  `RASI_NAMES` ("Mithunam", "Kadakam", "Simmam") for Gemini/Cancer/Leo
  — found while fixing A3's Ekadhipatya Shodhana, sidestepped there via
  longitude-based occupancy rather than name-matching, but not itself
  fixed. Four independent occurrences of the identical failure shape is
  a pattern, not a coincidence — recommend a named, prioritized future
  pass: grep the full codebase for every remaining hardcoded 12-entry
  rasi-name list or lookup table not yet routed through
  `to_english_rasi()`, and consolidate onto the one shared utility the
  way the Lagna/Gulika-segment/Tithi consolidations already did for
  their respective duplications.
- **RECOMMENDATION (2026-09-14) — include family predictions in
  whatever periodic narrative-grounding spot-check practice gets
  established.** `family_prediction_engine.py` was checked (B1) for the
  same score-vs-signal-count momentum miscalibration bug already found
  and fixed in `ai_interpretation_engine.py`'s `generate_interpretation()`
  — it doesn't have that bug, but only because it has NO numeric
  life-area scoring stage at all: it's a purely qualitative LLM
  narrative built from dasha-lord names, Sade Sati phase, and yoga
  names as text, with zero computational backstop checking whether the
  LLM's tone/claims match anything underneath. This clears it of the
  specific momentum bug but leaves it exposed to a softer version of
  the same ungrounded-narrative risk this session repeatedly found
  elsewhere (the chat fabrication bugs, the Overview tonal
  contradiction). Recommend treating family predictions as an
  explicitly-covered surface in any future grounding audit, not as
  "cleared" just because this one specific bug class doesn't apply to
  it.

- **PRIORITY — `ashtakavarga_engine.py`'s "classical" Sarvashtakavarga
  is not a real classical calculation, and it's used for LIVE Saturn/
  Jupiter transit validation** (investigated 2026-09-13, not fixed —
  needs a decision, not a unilateral patch). `_compute_sarvashtakavarga()`
  (source="classical" branch, the one actually reached in production —
  `prediction_envelope.py:321`'s only caller always supplies
  `natal_positions`/`lagna_longitude`) gives each of the 8 contributors
  (7 grahas + Lagna) exactly ONE fixed benefic-house list
  (`SUN_AV_BENEFIC_HOUSES`, etc.), applied identically regardless of
  which planet's chart is being assessed, summing to a fixed 57-bindu
  total.

  Confirmed via cross-referencing real classical Bhinnashtakavarga
  mechanics (web search, corroborated by multiple independent
  astrology-software sources): real Bhinnashtakavarga assigns each
  contributor a DIFFERENT benefic-house table depending on which planet
  is being assessed (64 separate (contributor, assessed-planet) tables,
  not 8) — e.g. "Saturn's contribution to the Sun's BAV" uses houses
  `[1,2,4,7,8,9,10,11]`, a different list than Saturn's contribution to
  any other planet's BAV. Each assessed planet's own complete BAV
  (summed across all 8 contributors) has a well-known FIXED total
  regardless of the chart — Sun 48, Moon 49, Mars 39, Mercury 54,
  Jupiter 56, Venus 52, Saturn 39, summing to 337 — and this is what
  real "Sarvashtakavarga" sums. `ashtakavarga_engine.py`'s single-list-
  per-contributor approach can't reproduce this: it was never computing
  a per-assessed-planet BAV at all, so there's no real "Sarvashtakavarga"
  or "Shodhita Ashtakavarga" being approximated here — it's a
  structurally different, seemingly ad-hoc calculation that happens to
  produce a plausible-looking 57-bindu total, despite the file's own
  docstring calling it "Full Classical Parashari Calculation."

  **This means the originally-proposed fix (just rename it to
  "Shodhita Ashtakavarga" for clarity) would be actively misleading** --
  that name claims a real classical reduction (Trikona + Ekadhipatya
  Shodhana applied to a real SAV) that this code was never doing.
  Deliberately not renamed to any classical-sounding term.

  **`bhinnashtakavarga_engine.py`'s classical BAV/SAV implementation is
  mostly correct, verified against the same real fixed totals above**
  — a real chart's computed totals exactly matched Sun (48), Mercury
  (54), Venus (52), Saturn (39), but Moon came out 48 (expected 49),
  Mars 41 (expected 39), Jupiter 57 (expected 56) — net SAV total 339
  vs. the classical 337. 4 of 7 exact matches suggests the overall
  8×8 `BAV_TABLES` structure/approach is correct, with 1-2 likely
  transcription errors in specific table cells for Moon/Mars/Jupiter's
  rows, not a structural problem. `refined_av_engine.py` (Trikona/
  Ekadhipatya Shodhana) is correctly built on top of this engine's real
  SAV output — that pipeline (`bhinnashtakavarga_engine.py` →
  `refined_av_engine.py`) is the legitimate one.

  **Not fixed — decision made on the destination, deferred on
  execution (2026-09-13)**: `ashtakavarga_engine.py`'s
  `compute_ashtakavarga_validation()` is live, used for real Saturn/
  Jupiter transit-strength validation feeding `remedy_engine.py` (via
  `prediction_envelope.py:321`). Decided: switch this call site to the
  already-more-correct `bhinnashtakavarga_engine.py` SAV +
  `refined_av_engine.py` Shodhita-reduction pipeline (not a rename, not
  "leave as-is" — the current heuristic is confirmed structurally wrong,
  not just unlabeled). This switch is gated on two preconditions, both
  still outstanding, before it ships:
  1. Fix and source `bhinnashtakavarga_engine.py`'s 3 known
     transcription discrepancies (Moon 48 vs. expected 49, Mars 41 vs.
     expected 39, Jupiter 57 vs. expected 56) against a verified
     reference table — switching to a "mostly correct" replacement
     without first closing this gap would trade one uncited-accuracy
     problem for a smaller but still real one.
  2. Run a before/after comparative audit across real charts showing
     EXACTLY which Saturn/Jupiter transit-strength labels
     (`strength`/`overall_support` in `compute_ashtakavarga_validation()`'s
     output) would change for real users under the new pipeline, before
     switching — per this project's standing rule that a score/label
     change is a product decision, not something to migrate silently.
     The scale difference alone (57-total heuristic vs. 337-total real
     SAV, then Shodhita-reduced) means `_classify_bindu_strength()`'s
     thresholds (`>=6 high_support`, etc., calibrated for the 0-8
     per-sign range the current heuristic happens to produce) will also
     need re-deriving for the new pipeline's actual output range, not
     reused as-is.
  Both preconditions require their own dedicated work sessions — not
  started here.
- **`transit_hits_engine.py`'s `_house_of()` uses a different house
  SYSTEM than the rest of the app, not just a differently-styled
  formula** — found 2026-09-13 while consolidating the whole-sign
  house-from-longitude formula (`app/utils/house_math.py`) across the
  files that share it. `_house_of(natal_planet_lon, lagna_lon)` computes
  `int((natal_planet_lon - lagna_lon) % 360.0 / 30.0) % 12 + 1` — this
  divides the raw angular DISTANCE between the two points by 30°, which
  is an Equal House calculation (cusps exactly 30° apart starting at the
  exact Lagna degree), not Whole Sign (which every other engine in this
  app uses — the whole point of `house_from_longitude()` is
  `int(target//30) - int(ref//30)`, i.e. "which SIGN, not which 30°
  angular slice"). Confirmed these genuinely disagree, not just
  differently-styled: random-sampled 2000 (target, reference) pairs,
  1003 disagreed (about half, as expected whenever the reference point
  isn't exactly at 0° of its sign — true for nearly every real Lagna).
  Deliberately NOT touched in the house_math.py consolidation — this
  needs its own investigation (is Equal House intentional for
  `transit_hits_engine.py`'s specific purpose — labeling which life area
  a transit-degree hit affects — or is it an accidental formula choice
  that should be Whole Sign like everywhere else?) before deciding
  whether to fix it, not a blind merge into the new shared helper.
- **Closed 2026-09-14: Southern Hemisphere and boundary-degree gaps,
  both confirmed working, not just "didn't error"** — flagged in the
  2026-09-13 comprehensive audit as untested edge cases; investigated
  with real data and closed. Permanent regression tests:
  `tests/engines/test_southern_hemisphere_chart.py`,
  `tests/engines/test_boundary_degree_chart.py`.
  - **Southern Hemisphere**: a real chart (Sydney, Australia, latitude
    -33.8688, 1990-01-15) run through natal generation, Gochara
    house-from-Moon/house-from-Lagna, and the full chat-grounding
    pipeline. Since planetary sidereal longitudes are geocentric and
    latitude-independent by construction, the only genuinely
    latitude-dependent pieces are the Lagna/Ascendant and sunrise/
    sunset-based calculations (Upagraha, daily panchangam) — both
    independently verified, not just run: Lagna cross-checked against
    the standard spherical-astronomy Ascendant formula (RAMC/obliquity/
    ayanamsa taken from Swiss Ephemeris as trusted sub-inputs, but the
    latitude-dependent `tan(lat)` trigonometric step — exactly where a
    Southern-Hemisphere sign bug would appear — computed independently
    in plain Python), matched to within 0.01°; sunrise/sunset (06:01/
    20:07 AEDT) matched Sydney's well-known real mid-January times. No
    bug found.
  - **Boundary-degree**: a real chart already in the DB
    (`11656fc5-c67b-4b0b-9929-c14a28105e56`) has Mars at 240.00705°,
    ~25 arcseconds past the Scorpio/Sagittarius cusp — and, coincidentally,
    240° is also exactly a nakshatra boundary (18×13°20′ = 240.0 exactly,
    the Jyeshtha/Mula cusp), so this one chart tests both at once.
    Checked every independent longitude-to-sign implementation found
    across the app this session (`ephemeris.py`, `gochara_engine.py`,
    `yoga_engine.py`, `ashtakavarga_engine.py`, `moon_transit_engine.py`,
    `divisional_charts/d9_navamsa.py`) plus nakshatra derivation — all
    agree (Sagittarius/Mula, not Scorpio/Jyeshtha), including through D9
    and the chat-grounding `planets_summary` field. No inconsistency
    found.
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
- **`LLM_MONTHLY_TOKEN_BUDGET` (`llm_interpretation_orchestrator.py`) has
  no admin visibility or alerting at all — it was exhausted silently on
  2026-09-15 and only discovered by accident** (a manual backfill run
  happened to hit the wall; nothing paged anyone, no dashboard showed
  it approaching the ceiling, and real users were silently getting
  deterministic-only fallback content for however long it took someone
  to notice). This is a different, unrelated gate from the dollar-based
  `llm_budget.llm_enabled` auto-pause that `admin_llm.py`'s `/budget`
  endpoint already surfaces — `get_monthly_token_usage()` has no
  equivalent admin-facing endpoint or field at all. Needs, at minimum,
  a loud log line (not just `logger.warning` buried per-call) when a
  request first hits `budget_exceeded` in a given month, and ideally a
  `/budget` response field (`token_budget`/`tokens_used`/
  `tokens_remaining`) so an admin can see it coming before it's already
  hit — the same category of gap as the per-account cap not being
  exposed above, just for the global ceiling instead. Not built —
  logged for a future pass, not urgent enough to justify scope-creeping
  into the 2026-09-15 emergency budget raise.
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
  for a PDF-specific bug).
  **Correction (2026-09-13):** this entry used to call
  `family-prediction-screen.tsx` "already-fixed" — that was wrong. Only
  its PDF download call site had actually been migrated; its other 3
  call sites (group fetch, predictions fetch, predictions delete) still
  used a local `apiJson()`/`apiFetch()` wrapper with the same gap, found
  during a broader duplication audit that specifically re-checked this
  claim rather than trusting it. Now genuinely fully migrated (all 4
  call sites), verified via `tsc --noEmit` (zero errors) and the
  existing frontend test suite. The other five screens listed above are
  still unfixed as of this correction — don't assume any of them are
  done without re-checking the file directly, the way this one's claim
  turned out not to hold.
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
- **CLOSED 2026-09-15: `life_area_scorer.py`'s `top_signals`/scoring gap
  that silently excluded every structurally house/planet-less signal**
  (yogas, Tara Bala, Ashtakavarga validation, Chandra Gati rhythm,
  Navamsa dignity, aspect-balance summaries, event-window confluence,
  some divisional-chart refinements) — first found 2026-09-11 during the
  front/back Overview-contradiction investigation, fixed and verified
  2026-09-15. Root cause confirmed exactly as originally diagnosed:
  `score_one()` computed `raw = (house_w + planet_w) * strength *
  src_bias * val_mult`, and any signal carrying neither a `house` nor a
  `planet` got `house_w = planet_w = 0.0` regardless of its own
  `strength`, so `raw` was always exactly `0` and `if abs(raw) > 0`
  silently excluded it from both scoring and `top_signals` — no matter
  how classically significant. A live signal-level trace found this
  applied to more signal types than the original note named (that note's
  literal `ASHTAKAVARGA_STRONG_SUPPORT` example turned out to be one of
  several dynamically-suffixed keys, e.g. `TARA_BALA_SAMPAT`; Yogakaraka-
  activation signals actually already carried a real `planet` field and
  were NOT affected — confirmed by direct trace, not assumed from the
  original note).

  **Fix**: two new declarative weight tables added per life area in
  `life_area_config.py` (same file, same philosophy as every other
  weight there — "the ONLY place where astrology opinions live"):
  `signal_key_weights` (exact-key overrides for signals whose classical
  relevance genuinely differs by area, e.g. a wealth yoga matters far
  more to "finance" than "health") and `signal_source_weights` (a
  per-`source` fallback for dynamically-suffixed keys, applied only when
  a signal has no house/planet AND no exact-key override). A signal that
  DOES carry a house/planet but legitimately scores 0 for a *specific*
  area (e.g. a Sun-related signal in an area that doesn't weight Sun) is
  untouched — confirmed by a dedicated regression test — that's a real
  "not relevant here", not the structural gap. Also fixed a related bug
  found while verifying: `top_signals` sliced `contributions[:top_k]` in
  raw insertion order, not by contribution magnitude, so a genuinely
  significant signal (e.g. a strong yoga) could still be invisible in
  the displayed `top_signals` even after getting real weight, simply by
  being appended later than 6 weaker ones. Now sorted by `abs(contrib)`
  descending before truncating.

  **Verified**: unit tests for every previously-zero signal type across
  all 5 areas, one real-chart-data regression test (chart `7c6e34be`,
  confirmed active Raja Yoga, run through the real `synthesize_from_envelope()`
  pipeline) that would have caught the original exclusion bug, and a
  real before/after comparison across all 38 real charts for a real
  September 2026 monthly envelope: 190 (chart, area) score comparisons,
  average delta +2.49, average |delta| 4.55, 180/190 scores changed,
  51/190 crossed a qualitative label boundary (ad-hoc 5-bucket scale
  used for this verification only — Needs Support/Mixed/Moderate
  Support/Strong Support/Excellent). See
  `tests/engines/test_life_area_scorer_signal_weights.py`.

  **Backfill: done, 76/76, after the budget raise.** Initially paused
  (the Ashtakavarga backfill immediately before this one had exhausted
  the shared `LLM_MONTHLY_TOKEN_BUDGET` -- see that entry above), then
  run after the emergency raise: 75/76 succeeded on the first pass;
  1 row (chart `f1eb7ec4`, monthly 2026-07) hit a real, unrelated
  pre-existing bug surfaced BY this fix -- `ai_interpretation_engine.py`'s
  signal-source inference for `top_signals` entries had an incomplete
  key-prefix list that only ever covered the signal types that could
  reach a non-empty `top_signals` BEFORE this fix (a real
  `MARAKA_ACTIVE_Mars` signal fell through every branch, producing a
  literal `"key": None` in the LLM payload's attribution and failing
  schema validation). Fixed by extracting a single shared
  `_infer_source_from_key()` (previously duplicated independently in
  two places, each incomplete) covering every real signal-key prefix;
  see `tests/engines/test_ai_interpretation_signal_source_inference.py`
  for the regression test built from this exact real chart/period/
  signal. Re-ran the one failed row clean afterward -- 76/76 final,
  0 fallbacks. Real cost: 1,196,012 tokens, $6.57 exact (from real
  prompt/completion token counts at Sonnet 4.6 pricing) -- close to the
  original ~$6-7 estimate.
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
- **Mean-node default now traced to a specific, named Vakya-tradition
  source, not just general "Tamil astrology sources"** (closed
  2026-09-14, per the earlier-flagged gap that prior node-type
  validation was never confirmed Vakya-specific). Prior validation
  (`67605ed`/`7685348`, 2026-09-12's ingress fix) confirmed mean-node
  output "matches external Tamil astrology sources" without naming
  which tradition within Tamil astrology those sources followed —
  Vakya and Thirukanitha (Drik Ganita) are two genuinely different
  calendrical schools that can disagree by hours to days on tithi/
  nakshatra boundaries, so agreement with an unnamed source didn't
  actually confirm this app's mean-node default matches Vakya
  specifically. Now sourced: Vākyapañcāṅga (the Vakya-tradition
  almanac) is built on the katapayadi-encoded verse-tables of
  *Vākyakaraṇa*, which compute planetary positions from constant MEAN
  motions, not observed/perturbed ones (per Wikipedia's
  [Vākyapañcāṅga](https://en.wikipedia.org/wiki/V%C4%81kyapa%C3%B1c%C4%81%E1%B9%85ga)
  and [Vākyakaraṇa](https://en.wikipedia.org/wiki/V%C4%81kyakara%E1%B9%87a)
  articles, corroborated by DrikPanchang's own Tamil-language
  [Thiruganita vs. Vakyam](https://www.drikpanchang.com/tamil/info/thiruganita-versus-vakyam-panchangam.html)
  comparison: "Vakya... computes the positions of planets based on the
  mean motions of planets," contrasted explicitly against Thirukanitha's
  modern ephemeris-based approach). Vakya's own root text for the
  lunar nodes traces to the Surya Siddhanta's node model — the nodes as
  "shadow planets" (chāyā grahāḥ) in constant retrograde MEAN motion,
  with no true-node oscillatory correction at all — so a mean-node
  default is not merely compatible with Vakya tradition, it's the only
  node model Vakya's own source astronomy defines. Further corroborated
  by B. V. Raman (a named, citable classical-Vedic-astrology authority):
  "For all practical purposes of horoscopy, the Mean Node should be
  used. The so-called True Node of Western tables introduces needless
  irregularity." This closes the gap cleanly in mean-node's favor — no
  contradiction found, unlike some of tonight's other "never
  independently verified" items.
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