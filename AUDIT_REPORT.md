# Tamil Panchangam Codebase Audit Report

**Generated:** 2026-05-06  
**Auditor:** Claude Code (read-only audit — no source files modified)

---

## Step 1 — Directory Inventory

### `app/engines/` (source files only, excluding `__pycache__`)

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `ai_interpretation_engine.py` | Orchestrates AI interpretation generation |
| `antar_explanation_engine.py` | Builds Antardasha explanations |
| `ashtakavarga_engine.py` | Sarvashtakavarga bindu computation |
| `budget_guard.py` | LLM cost guard / token logging |
| `child_prediction_engine.py` | Per-child astrological profile + milestones |
| `children_timing_engine.py` | Santana Bhagya timing windows |
| `corner_case_detector.py` | Detects planets near sign cusps |
| `d9_strength_engine.py` | Navamsa (D9) dignity strength |
| `dasha_resolver.py` | Resolves active Antar Dasha at a reference date |
| `dasha_vimshottari.py` | Full Vimshottari timeline (Maha + Antar) |
| `divisional.py` | Divisional chart helpers (legacy) |
| `divisional_charts/d2_hora.py` | D2 Hora chart (wealth) |
| `divisional_charts/d7_saptamsa.py` | D7 Saptamsa chart (creativity/children) |
| `divisional_charts/d9_navamsa.py` | D9 Navamsa chart (dharma/maturity) |
| `divisional_charts/d10_dasamsa.py` | D10 Dasamsa chart (career) |
| `drishti_engine.py` | Natal planetary aspects (Drishti) |
| `ephemeris.py` | Swiss Ephemeris wrapper — sidereal positions, Lagna |
| `event_window_engine.py` | Event timing windows from transits |
| `explainability_engine.py` | Explainability signal assembly |
| `explainability_filter.py` | Filters signals per explainability mode |
| `family_prediction_engine.py` | Family-level combined prediction |
| `functional_role_engine.py` | Yogakaraka / benefic / malefic classification |
| `gochara_engine.py` | Transit (Gochara) engine — Jupiter, Saturn, Rahu/Ketu |
| `house_mappings.py` | House configuration data |
| `house_semantics.py` | House plain-English theme mappings |
| `house_strength_engine.py` | House strength calculation |
| `house_weights.py` | Scoring weights per house |
| `interpretation.py` | Legacy interpretation helpers |
| `interpretation_builder.py` | Interpretation assembly |
| `interpretation_engine.py` | Deterministic interpretation from synthesis |
| `interpretation_fragments.py` | Text fragments library |
| `interpretive_hints.py` | Hint strings per signal type |
| `kp_sublords.py` | KP Sub-lord / Sub-sub-lord calculation |
| `life_area_config.py` | Life-area configuration (career, finance, etc.) |
| `life_area_scorer.py` | Scores life areas from signals |
| `llm_interpretation_orchestrator.py` | Manages LLM call lifecycle + caching |
| `moon_transit_engine.py` | Monthly moon transit (Chandra Gati) |
| `nakshatra_engine.py` | Nakshatra context + Tara Bala |
| `narrative_engine.py` | Dasha narrative text |
| `navamsa_engine.py` | Legacy Navamsa (D9) builder |
| `pancha_pakshi.py` | Pancha Pakshi bird + daily guidance |
| `panchangam.py` | Tithi, Nakshatra, Yoga, Karana, Vara |
| `paraphraser.py` / `paraphrasing_engine.py` | Text paraphrasing |
| `planet_semantics.py` | Planet meaning descriptions |
| `planet_strength_engine.py` | Planet strength helpers |
| `porutham_engine.py` | 10-point Jathagam Porutham (Kuta) |
| `prediction_engine.py` | Prediction orchestration |
| `prediction_envelope.py` | Monthly prediction envelope assembly |
| `realtime_context_engine.py` | Real-time context for chat/UI |
| `remedy_engine.py` | Classical remedy computation |
| `sade_sati_engine.py` | Sade Sati / Ashtama Shani / Kantaka Shani |
| `shadbala_engine.py` | 6-fold planetary strength (Shadbala) |
| `synthesis.py` / `synthesis_engine.py` | Signal synthesis into life-area scores |
| `timeline_aggregator.py` | Family timeline building |
| `transits.py` | Simple monthly transit snapshot (legacy) |
| `weekly_prediction_envelope.py` | Weekly prediction envelope |
| `yearly_prediction_envelope.py` | Yearly prediction envelope |
| `yoga_engine.py` | Yoga detection (Raja, Dhana, Pancha Mahapurusha, etc.) |

### `app/api/`

`admin.py`, `admin_llm.py`, `auth.py`, `base_chart.py`, `canonical_report.py`, `chat.py`, `family.py`, `interpretation.py`, `natal_interpretation.py`, `prediction.py`, `prediction_request.py`, `prediction_weekly.py`, `prediction_yearly.py`, `predictions_ui.py`, `realtime_context.py`, `ui_birth_chart.py`, `ui_reports.py`, `user_charts.py`

### `app/llm/`

`payload_builder.py`, `token_estimator.py`, `providers/anthropic_provider.py`, `providers/openai_provider.py`

### `app/llm/prompts/`

`child_prediction_prompt.txt`, `children_timing_prompt.txt`, `family_prediction_prompt.txt`, `interpretation_prompt_v1.txt`, `interpretation_prompt_v2.txt` (not read — superseded), `interpretation_prompt_v3.txt`, `interpretation_prompt_v4.txt`

### `app/db/`

`bootstrap.py`, `duckdb.py` (shim → postgres), `models.py`, `postgres.py`, `session.py`, `sqlite_patch.py`

---

## Step 2 — Engine Audit

### `ephemeris.py`
**a) What it computes:** Sidereal planetary longitudes, speeds, declinations, Lagna, Moon Nakshatra/Pada, and Rahu/Ketu using Swiss Ephemeris.  
**b) Primary output fields:** `julian_day`, `node_type`, `ayanamsa`, `lagna.{longitude_deg, rasi}`, `moon.{longitude_deg, rasi, nakshatra}`, `planets.{Sun…Ketu}.{longitude_deg, rasi, speed_deg_per_day, is_retrograde, declination}`  
**c) Ayanamsa mode:** Supports both Lahiri (`SIDM_LAHIRI`) and KP (`SIDM_KRISHNAMURTI`) via `ayanamsa` param.  
**d) API route:** Called in `POST /base-chart/create` and in `build_birth_chart_report_data`.  
**e) Stored:** Full ephemeris dict is serialised inside `base_charts.payload` JSONB column.

---

### `panchangam.py`
**a)** Computes the five Panchangam elements at birth: Tithi, Nakshatra (via ephemeris), Yoga, Karana, Vara (weekday), Tamil month.  
**b)** `{tithi, nakshatra, yoga, karana, weekday, tamil_month}`  
**c)** Ayanamsa-agnostic (uses pre-computed longitudes). Works with either.  
**d)** Called in `POST /base-chart/create`.  
**e)** Stored in `base_charts.payload` as `panchangam_birth`. Exposed via `build_birth_chart_view_model` as `panchangam` key.

---

### `dasha_vimshottari.py`
**a)** Computes the full 120-year Vimshottari Dasha timeline (9 Mahadashas with 9 Antardashas each) plus current active Maha/Antar dasha.  
**b)** `{starting_dasha, balance_years, timeline[{mahadasha, start, end, is_partial, antar_dashas}], current.{lord, start, end, antar}}`  
**c)** Ayanamsa-independent (uses Moon longitude from ephemeris).  
**d)** Called in `POST /base-chart/create`. Also used by prediction envelope and resolver.  
**e)** Stored in `base_charts.payload` under `dashas.vimshottari`.

---

### `kp_sublords.py`
**a)** Computes KP Star-lord, Sub-lord, and Sub-sub-lord for every planet, Moon, and Lagna using Vimshottari proportional sub-division.  
**b)** Per planet: `{longitude, star_lord, sub_lord, sub_sub_lord}`  
**c)** KP mode only — called conditionally when `ayanamsa == "kp"`.  
**d)** Called in `POST /base-chart/create` (KP branch only). Exposed via `GET /ui/birth-chart` as `kp_sublords`.  
**e)** Stored in `base_charts.payload` as `kp_sublords` (null for Lahiri charts).

---

### `ashtakavarga_engine.py`
**a)** Computes classical Sarvashtakavarga (57 total bindus across 12 signs, 8 contributors) and validates Saturn/Jupiter transits against their bindu strength.  
**b)** `{saturn.{transit_rasi, bindus, strength}, jupiter.{transit_rasi, bindus, strength}, overall_support, source, sarvashtakavarga}`  
**c)** Ayanamsa-independent; receives pre-computed natal positions.  
**d)** Called inside `build_monthly_prediction_envelope` (prediction envelope) and `build_birth_chart_report_data` (PDF).  
**e)** Not stored in `base_charts.payload`. Stored inside `monthly_predictions.envelope` JSONB as `ashtakavarga` key. The `sarvashtakavarga` sub-dict is forwarded to the PDF data loader.

---

### `shadbala_engine.py`
**a)** Computes the classical 6-fold planetary strength (Sthana, Dig, Chesta, Naisargika, Drik Bala) for 7 planets in Shashtiamsas/Rupas.  
**b)** Per planet: `{total_shashtiamsas, rupas, percent_strength, strength_label, components.{sthana_bala, dig_bala, chesta_bala, naisargika_bala, drik_bala}, is_retrograde}` + `ranking`, `strongest_planet`, `weakest_planet`, `summary`  
**c)** Ayanamsa-independent.  
**d)** Called fresh by `prediction_envelope.py` (`_compute_shadbala_safe`). Also called in `birth_chart_builder.py` for the UI view.  
**e)** **Not stored** in `base_charts.payload` directly. Stored in `monthly_predictions.envelope` JSONB as `shadbala`. The UI view re-computes it on every request via `build_birth_chart_view_model`.

---

### `yoga_engine.py`
**a)** Detects 9 yoga types: Gaja Kesari, Dhana, Viparita Raja, Neecha Bhanga Raja, Raja Yoga, Pancha Mahapurusha, Budhaditya, Chandra-Mangala, Kemadruma.  
**b)** `{yogas[{name, present, strength, effects, rationale}], summary.{total_yogas, has_gaja_kesari, has_dhana_yoga, has_raja_yoga, has_pancha_mahapurusha, has_budhaditya, has_kemadruma, yoga_names}}`  
**c)** Ayanamsa-independent.  
**d)** Called in `build_monthly_prediction_envelope` and `birth_chart_builder.py` (for UI view).  
**e)** Not independently stored in `base_charts` (yogas are re-computed at prediction and UI-view time). Present in `monthly_predictions.envelope` as `yogas` key.

---

### `sade_sati_engine.py`
**a)** Computes Sade Sati (Saturn in 12th/1st/2nd from natal Moon), Ashtama Shani (8th), and Kantaka Shani (4th) using a hardcoded Saturn transit table (2020–2032).  
**b)** `{moon_sign, moon_sign_name, current_saturn_sign, saturn_house_from_moon, sade_sati.{active, phase, phase_name, effects, remedies, current_phase_ends, all_windows, summary}, ashtama_shani.{active, effects, remedies}, kantaka_shani.{active, effects}, alert_level}`  
**c)** Ayanamsa-independent.  
**d)** Called by `prediction_envelope.py` and `birth_chart_builder.py`.  
**e)** Stored in `monthly_predictions.envelope` as `sade_sati`. Re-computed in UI view.

---

### `navamsa_engine.py` / `divisional_charts/d9_navamsa.py`
**a)** Computes the D9 Navamsa chart (9 divisions per sign per Parashara method) plus dignity assessment (exalted/debilitated/neutral) for each planet.  
**b)** Per planet: `{navamsa_sign, dignity}` (D9 new format adds more metadata).  
**c)** Both Lahiri and KP (uses sidereal longitudes regardless of ayanamsa).  
**d)** Called in `POST /base-chart/create`.  
**e)** Legacy format stored in `base_charts.payload` under `charts.D9`; new format under `divisional_charts.D9`.

---

### `transits.py` (simple) / `gochara_engine.py` (full)
**a)** `transits.py` is a simple snapshot (Saturn/Jupiter/Mars from natal Moon). `gochara_engine.py` is the full Gochara engine covering Jupiter, Saturn, Rahu/Ketu with house-from-moon, Drishti bonus, phase detection, and retrograde.  
**b)** Gochara output: `{jupiter.{transit_rasi, from_moon_house, effect, drishti_aspect_bonus}, saturn.{transit_rasi, transit_phase, from_moon_house, phase, drishti_aspect_bonus}, rahu_ketu.{rahu_rasi, ketu_rasi, rahu_from_moon_house, ketu_from_moon_house, effect, axis, theme}}`  
**c)** Both (uses sidereal positions computed with chosen ayanamsa).  
**d)** Gochara called in `build_monthly_prediction_envelope`. Simple transits used in legacy prediction pipeline.  
**e)** Stored in `monthly_predictions.envelope` as `gochara`.

---

### `porutham_engine.py`
**a)** Computes 10-point Jathagam Porutham (Kuta matching) between two charts: Dinam, Ganam, Yoni, Rasi, Rasiyathipaty, Rajju, Vedha, Mahendra, Stree Deergha, Nadi (max 33 points).  
**b)** `{total_score, max_score, percent, grade, mandatory_fail, points[{name, score, max, pass, mandatory?}]}`  
**c)** Ayanamsa-independent.  
**d)** Called from `GET /family/groups/{group_id}/porutham`.  
**e)** Not persistently cached in DB (computed on demand).

---

### Other notable engines (summary)

| Engine | What | KP/Lahiri | API route | DB cached |
|--------|------|-----------|-----------|-----------|
| `drishti_engine.py` | Natal aspects | Both | via envelope | In `monthly_predictions.envelope` |
| `house_strength_engine.py` | House-level strength | Both | via envelope | In `monthly_predictions.envelope` |
| `functional_role_engine.py` | Yogakaraka/benefic/malefic | Both | `GET /base-chart/{id}` (on-the-fly) | Not persisted |
| `nakshatra_engine.py` | Monthly Nakshatra context + Tara Bala | Both | via envelope | In `monthly_predictions.envelope` |
| `moon_transit_engine.py` | Chandra Gati (monthly moon transits) | Both | via envelope | In `monthly_predictions.envelope` |
| `event_window_engine.py` | Event timing windows | Both | via envelope | In `monthly_predictions.envelope` |
| `pancha_pakshi.py` | Pancha Pakshi daily guidance | N/A | via base chart | In `base_charts.payload` as `pancha_pakshi_birth` |
| `remedy_engine.py` | Classical remedies | Both | via envelope | In `monthly_predictions.envelope` |
| `divisional_charts/d2_hora.py` | D2 Hora (wealth) | Both | via base chart | In `base_charts.payload.divisional_charts.D2` |
| `divisional_charts/d7_saptamsa.py` | D7 Saptamsa (children) | Both | via base chart | In `base_charts.payload.divisional_charts.D7` |
| `divisional_charts/d10_dasamsa.py` | D10 Dasamsa (career) | Both | via base chart | In `base_charts.payload.divisional_charts.D10` |
| `family_prediction_engine.py` | Family combined predictions | Both | `GET /family/groups/{id}/predict` | In `family_predictions` table |
| `child_prediction_engine.py` | Per-child chart milestones | Both | Family API | In `family_child_predictions` table |
| `children_timing_engine.py` | Santana Bhagya timing | Both | Family API | In `family_children_timing` table |

---

## Step 3 — Chart Data Flow

### Birth chart assembly (`POST /base-chart/create`)

**Inputs:** `name`, `place_of_birth`, `latitude`, `longitude`, `date_of_birth`, `time_of_birth`, `timezone`, `node_type`, `ayanamsa`, `turnstile_token`

**Engines called (in order):**
1. `compute_sidereal_positions` → ephemeris
2. `compute_kp_sublords` (KP mode only)
3. `compute_panchangam` → panchangam_birth
4. `compute_vimshottari_dasha` → dashas.vimshottari
5. `get_birth_pakshi` → pancha_pakshi_birth
6. `build_hora_chart`, `build_saptamsa_chart`, `build_navamsa_chart`, `build_dasamsa_chart` → divisional_charts
7. `compute_functional_roles` → functional_roles
8. Legacy `build_navamsa_chart` → charts.D9

**Top-level keys of `base_chart` dict (the full payload stored in DB):**

```
birth_details          # name, place, lat, lon, timezone, dob, tob
birth_utc              # ISO UTC string
ephemeris              # full planet positions, lagna, moon, nodes
panchangam_birth       # tithi, nakshatra, yoga, karana, weekday, tamil_month
charts                 # D9 (legacy navamsa format)
divisional_charts      # D2, D7, D9, D10 (standardized format)
chart_metadata         # ayanamsa, division_method, precision, node_type
dashas                 # {vimshottari: {starting_dasha, balance_years, timeline, current}}
pancha_pakshi_birth    # {pakshi, nature}
functional_roles       # yogakaraka, functional benefics/malefics
kp_sublords            # star_lord, sub_lord, sub_sub_lord per planet (KP only, else null)
```

**What is NOT stored in base_charts.payload:**
- Yogas (computed on-demand in UI view and prediction envelope)
- Shadbala (computed on-demand)
- Sade Sati (computed on-demand)
- Ashtakavarga full computation (computed in prediction envelope)
- Drishti / aspects (computed in prediction envelope)
- Gochara / transits (computed in prediction envelope)

---

## Step 4 — LLM Context Audit

### `interpretation_prompt_v1.txt` (v1.0 — still in use as fallback)
**a)** Filename: `interpretation_prompt_v1.txt`  
**b)** Inputs: `overall_context.{period_type, lagna, moon_rasi, moon_nakshatra, active_dasha, explainability_mode, current_transits, dasha_timing}`, `life_areas[{name, score, strength, signals}]`  
**c)** Does NOT receive: yogas, sade_sati, shadbala, nakshatra_pada, birth_year, lagnadipathi, Rahu/Ketu axis, KP sublords, chandrashtama, D2/D7/D10 chart signals  
**d)** Output: `{window_summary.{momentum, outcome_mode, overview, dominant_forces, timing_guidance}, life_areas.{career, finance, relationships, health, personal_growth}.{score, outlook, summary}}`

---

### `interpretation_prompt_v3.txt` (v3.0 — Siddhar tradition)
**a)** Filename: `interpretation_prompt_v3.txt`  
**b)** Inputs: `overall_context.{period_type, period_label, lagna, moon_rasi, moon_nakshatra, nakshatra_pada, active_dasha, explainability_mode, current_transits, dasha_timing, birth_year, life_stage, lagnadipathi_status, saturn_phase, rahu_ketu_axis, yogas, chandrashtama_periods}`, `life_areas[{name, score, strength, signals.{summary, rationale, interpretive_hint, planet, house, valence}}]`  
**c)** Does NOT receive: shadbala per-planet details (only summary labels), ashtakavarga (only embedded in transit description), D2/D7/D10 chart placement signals (not forwarded to LLM signals)  
**d)** Output: `{yearly_mantra, dasha_transit_synthesis, life_areas.{career, finance, relationships, health, personal_growth}.{score, outlook, summary}, danger_windows[], veda_remedy.{primary_remedy, supporting_practice, specific_remedies[]}, closing.{key_takeaways[], encouragement}}`

---

### `interpretation_prompt_v4.txt` (v4.0 — Plain-English interpreter — current default)
**a)** Filename: `interpretation_prompt_v4.txt`  
**b)** Inputs: Same enriched `overall_context` as v3, additionally `sade_sati` (active/phase/effects), `shadbala_summary` (strongest/weakest planets + ranking), `chart_system.{ayanamsa, is_kp}`, `kp_active_sublords` (Moon, Lagna, Sun sub-lords when KP mode). Life-area `signals` include `planet`, `house`, `house_plain`, `valence`, `interpretive_hint`  
**c)** Does NOT receive: Full Shadbala Rupa scores per planet (only summary labels), Sarvashtakavarga per-sign bindu table, individual Bhinnashtakavarga tables, D2/D7/D10 placement signals (these divisional chart placements are not extracted as individual signals in `payload_builder.py`), Porutham data  
**d)** Output: `{executive_summary.{main_theme, year_in_one_line, strongest_area, watch_area, best_use, one_lines}, why_this_period.{dasha_plain, transit_plain, overlap_summary, supportive[], watchouts[]}, life_areas.{career, finance, relationships, health, personal_growth}.{score, outlook, plain_english, real_life_patterns, do[], avoid[], astrological_basis}, remedies.{primary, supporting}, caution_windows[], key_takeaways[], _visibility}`

---

### `child_prediction_prompt.txt`
**a)** Filename: `child_prediction_prompt.txt`  
**b)** Inputs: child name, DOB, nakshatra, rasi, current Mahadasha/Antardasha, key house lords (4th, 5th, 10th, 7th, 12th), current year  
**c)** Does NOT receive: full ephemeris, yogas, shadbala, KP sublords, Sade Sati, divisional charts  
**d)** Output: `{overall_narrative, education[], career_aptitude, marriage_window, leaving_home, health_cautions[], key_takeaways[]}`

---

### `children_timing_prompt.txt`
**a)** Filename: `children_timing_prompt.txt`  
**b)** Inputs: husband/wife nakshatra, rasi, 5th house lord, 5th house lord Dasha periods, Jupiter placement, current Dasha, Sade Sati status, year range  
**c)** Does NOT receive: full ephemeris, yogas, D7 (Saptamsa chart for children) data  
**d)** Output: `{overall_outlook, combined_windows[], jupiter_insight, remedies[]}`

---

### `family_prediction_prompt.txt`
**a)** Filename: `family_prediction_prompt.txt`  
**b)** Inputs: family name, each member's name/role/nakshatra/rasi/mahadasha/antardasha/sade_sati, Porutham score (husband+wife), current year  
**c)** Does NOT receive: full ephemeris, yogas, shadbala, divisional charts, KP sublords  
**d)** Output: `{executive_summary, financial_peaks[], caution_windows[], child_milestones[], key_takeaways[]}`

---

### LLM payload assembly (`payload_builder.py` — `build_llm_payload` / `extract_payload_inputs`)

What gets pulled from the chart dict before sending to LLM:

| Data | Sent to LLM? | Notes |
|------|-------------|-------|
| Lagna rasi | Yes | As `overall_context.lagna` |
| Moon rasi + Nakshatra + Pada | Yes | |
| Active Maha + Antar Dasha | Yes | |
| Dasha timing (start/end dates) | Yes | |
| Current transits (Jupiter/Saturn/Rahu/Ketu) | Yes | Sign + house from Moon + effect |
| Saturn phase (Sade Sati phase name) | Yes | Only if active |
| Sade Sati full status | Yes (v4) | active/phase/effects summary |
| Rahu-Ketu axis karmic theme | Yes | |
| Yogas (up to 4, name + effects) | Yes | |
| Chandrashtama periods | Yes | |
| Lagnadipathi (lord, house, dignity) | Yes | |
| Birth year / life stage | Yes | |
| Shadbala summary (strongest/weakest) | Yes (v4) | Only top-level ranking, NOT per-planet Rupas |
| KP sublords (Moon, Lagna, Sun) | Yes (KP mode only) | |
| Life-area scores | Yes | From synthesis |
| Per-area signals (planet, house, rationale, hint) | Yes (trimmed) | Max 2-3 per area |
| **Full Shadbala Rupa scores per planet** | **No** | Only summary sent |
| **Sarvashtakavarga per-sign table** | **No** | Only Saturn/Jupiter bindus in transit description |
| **D2/D7/D10 planet placements** | **No** | Not extracted into life-area signals |
| **Ashtakavarga individual bindu tables** | **No** | |
| **Porutham data** | **No** | Only in family_prediction_prompt (indirect) |
| **Natal Panchangam (Tithi/Vara/Yoga)** | **No** | |

---

## Step 5 — PDF Audit

### PDF generation files
- **Entry point:** `app/pdf/canonical_report/report_builder.py` → `build_canonical_report()` / `build_birth_chart_report()`
- **Data loader:** `app/pdf/canonical_report/data_loader.py` → `build_report_data()` / `build_birth_chart_report_data()`
- **Renderer:** `app/pdf/canonical_report/pdf_renderer.py` (uses ReportLab)
- **Family PDF:** `app/pdf/family_report/family_pdf_renderer.py`
- **Chart SVG:** `app/pdf/charts/south_indian_svg.py`, `app/pdf/charts/reportlab_chart.py`

### PDF sections and data fields

**a) Sections rendered:**
- Birth details header (name, DOB, time, place)
- Birth reference (Janma Nakshatra, Janma Rasi, Lagna, nakshatra lord, starting dasha)
- Chart images: D1 Rasi (SVG), D9 Navamsa (SVG), D2 Hora (SVG), D7 Saptamsa (SVG), D10 Dasamsa (SVG)
- Dasha context (Mahadasha, Antardasha, balance, functional benefics/malefics)
- Transit context (Jupiter/Saturn/Rahu-Ketu positions with Ashtakavarga bindus)
- Nakshatra timing (Tara Bala, Chandra Gati)
- Pakshi rhythm (dominant Pakshi)
- Prediction overview (LLM narrative or deterministic fallback)
- Life areas (career, finance, relationships, health, personal_growth) with scores
- v3 extras: yearly_mantra, dasha_transit_synthesis, veda_remedy, closing
- v4 extras: executive_summary, why_this_period, per-area do/avoid, key_takeaways
- Methodology info (ephemeris source, ayanamsa, node type, calculation confidence)
- Sarvashtakavarga (per-sign bindu table if present)
- Yogas (detected yogas from envelope)
- Sade Sati status from envelope
- Shadbala summary from envelope
- KP Sub-lords table (KP charts only)
- Natal interpretation sections (who_you_are, where_you_shine, relationships, current_chapter, life_by_decade, dasha_life_map)

**b) Data fields pulled:**
- `base_charts.payload` → `ephemeris`, `birth_details`, `charts.D9`, `divisional_charts`, `chart_metadata`, `kp_sublords`
- `monthly_predictions.envelope` → `gochara`, `ashtakavarga`, `nakshatra_context`, `chandra_gati`, `biological_rhythm`, `dasha_context`, `functional_roles`, `yogas`, `sade_sati`, `shadbala`
- `prediction_llm_interpretation.content_json` → LLM output (v1/v2/v3/v4)

**c) KP data in PDF:** YES — KP Sub-lords table rendered when `kp_sublords` is non-null (KP charts only).

**d) Shadbala in PDF:** YES (PARTIAL) — Shadbala summary (strongest/weakest planet labels) pulled from `monthly_predictions.envelope.shadbala`. Per-planet Rupa scores not rendered in a dedicated table; only the summary label appears.

**e) Ashtakavarga in PDF:** YES (PARTIAL) — Sarvashtakavarga per-sign bindu table is rendered when available (pulled from `envelope.ashtakavarga.sarvashtakavarga`). Individual planet Bhinnashtakavarga tables are not rendered.

**f) Yogas in PDF:** YES — Yoga list from `monthly_predictions.envelope.yogas` is included. For natal PDF, attempts to read from `base_charts.payload.yogas` (which is null — yogas are not stored there; this is a gap — see Step 7).

---

## Step 6 — Frontend Audit

### `client/src/pages/chart-detail.tsx`
**API endpoints called:**
- `GET /api/ui/birth-chart?base_chart_id={id}` → birth chart view model
- `GET /api/realtime/context/{id}` → real-time transit context

**Data displayed:**
- Tabbed chart viewer: D1 Rasi, D2 Hora, D7 Saptamsa, D9 Navamsa, D10 Dasamsa (South Indian SVG format)
- Birth details (date, time, place)
- Astro context table (lagna, nakshatra, rasi, current dasha)
- Dasha timeline (Mahadasha with Antardasha breakdown)
- Yogas panel (`ui.yogas`) — YES, shown for D1 tab
- Sade Sati panel (`ui.sade_sati`) — YES, shown for D1 tab
- Shadbala panel (`ui.shadbala`) — YES, shown for D1 tab
- Natal interpretation panel (LLM narrative)
- KP sublords (`kp_sublords` from response) — YES, forwarded to `TabbedChartViewer`

**Hidden / not displayed:** Ashtakavarga bindu table, per-planet Shadbala Rupa scores, Porutham, Tithi/Vara/Yoga/Karana (natal Panchangam is not rendered on this screen beyond what's in the astro context table)

---

### `client/src/screens/prediction-screen.tsx`
**API endpoints called:**
- `GET /api/prediction/{base_chart_id}/{year}/{month}` (monthly)
- `GET /api/prediction/yearly/{base_chart_id}/{year}` (yearly)
- PDF download via `GET /api/reports/...`

**Data displayed:**
- Monthly/yearly prediction with life-area scores (career, finance, relationships, health, personal_growth)
- LLM interpretation (v1/v3/v4 depending on stored version)
- Dasha timeline
- Chat panel (AI chat)
- Explainability drawer (signal details per life area)

**Hidden:** Ashtakavarga bindu table, Sarvashtakavarga map, per-planet Shadbala Rupas, Porutham, Tithi (prediction context only)

---

### `client/src/screens/family-screen.tsx`
**Data displayed:** Family group members, Porutham score (YES — displayed), Sade Sati per member, Dasha summary

---

### `client/src/pages/MonthlyView.tsx`
Deprecated — returns static "deprecated" message.

---

## Step 7 — Gap Summary Table

| Feature | Computed | Stored in DB | Sent to LLM | In PDF | In Frontend |
|---------|----------|--------------|-------------|--------|-------------|
| Natal chart (D1) | Yes | Yes (`base_charts.payload.ephemeris`) | Partial (lagna, moon via `overall_context`) | Yes (SVG) | Yes |
| Navamsa (D9) | Yes | Yes (`base_charts.payload.divisional_charts.D9`) | No (not as signals) | Yes (SVG) | Yes (tab) |
| D2 Hora | Yes | Yes (`base_charts.payload.divisional_charts.D2`) | No | Yes (SVG) | Yes (tab) |
| D7 Saptamsa | Yes | Yes (`base_charts.payload.divisional_charts.D7`) | No | Yes (SVG) | Yes (tab) |
| D10 Dasamsa | Yes | Yes (`base_charts.payload.divisional_charts.D10`) | No | Yes (SVG) | Yes (tab) |
| KP chart | Yes (KP mode) | Yes (`base_charts.payload.kp_sublords`) | Partial (Moon/Lagna/Sun only) | Yes (KP only) | Yes (KP only) |
| Shadbala | Yes | Partial (in envelope, not base chart) | Partial (summary labels only) | Partial (summary only) | Yes (UI panel) |
| Ashtakavarga (Sarvashtakavarga) | Yes | Partial (in envelope only) | No (bindu table not sent) | Partial (total table only) | No |
| Bhinnashtakavarga (per-planet) | No | No | No | No | No |
| Yogas | Yes | Partial (in envelope; NOT in base_charts.payload) | Partial (up to 4 names + effects) | Partial (from envelope; natal PDF gap) | Yes (UI panel) |
| Vimshottari Dasha | Yes | Yes (`base_charts.payload.dashas`) | Yes (Maha+Antar+timing) | Yes | Yes |
| Transits (Gochara) | Yes | Yes (in envelope per prediction) | Yes (Jupiter/Saturn/Rahu/Ketu) | Yes | Partial (summary in prediction view) |
| Sade Sati | Yes | Partial (in envelope; NOT in base_charts.payload) | Partial (active phase only) | Yes | Yes (UI panel) |
| Porutham | Yes | No (computed on demand) | Partial (score passed to family prompt) | No | Yes (family screen) |
| Upagrahas (Gulika, Mandi) | No | No | No | No | No |
| Tithi/Vara at birth | Yes | Yes (`base_charts.payload.panchangam_birth`) | No | No | No |
| Tithi/Vara current | No engine | No | No | No | No |
| Dinaphalam | No engine | No | No | No | No |
| Pancha Pakshi | Yes | Yes (`base_charts.payload.pancha_pakshi_birth`) | No | Partial (dominant pakshi only) | No |

---

## Step 8 — Wire Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BIRTH INPUT                                            │
│  (name, DOB, time, lat/lon, timezone, node_type, ayanamsa)                      │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
                        POST /base-chart/create
                                   │
            ┌──────────────────────▼────────────────────────────────────┐
            │                   ENGINES (base chart)                     │
            │  ephemeris → panchangam → vimshottari → pancha_pakshi     │
            │  D2/D7/D9/D10 divisional charts → functional_roles        │
            │  kp_sublords (KP mode only)                               │
            └──────────────────────┬────────────────────────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │   DB: base_charts (PostgreSQL)   │
                    │   payload JSONB stores:          │
                    │   - ephemeris, panchangam_birth  │
                    │   - dashas.vimshottari           │
                    │   - divisional_charts (D2-D10)   │
                    │   - charts.D9 (legacy)           │
                    │   - pancha_pakshi_birth          │
                    │   - functional_roles             │
                    │   - kp_sublords (KP only)        │
                    └──────────────┬─────────────────┘
                                   │
              ┌────────────────────┼──────────────────────────────────┐
              │                    │                                  │
              ▼                    ▼                                  ▼
    ┌─────────────────┐  ┌─────────────────────────┐      ┌──────────────────────┐
    │  GET /ui/birth- │  │ POST /prediction/...     │      │ family/* routes      │
    │  chart endpoint │  │ build_monthly/yearly/    │      │ porutham, family     │
    │                 │  │ weekly_prediction_envelope│      │ prediction, children │
    │ build_birth_    │  │                          │      │ timing               │
    │ chart_view_model│  │ Engines called fresh:    │      └──────────────────────┘
    │                 │  │  gochara, sade_sati,     │
    │ Re-computes:    │  │  shadbala, ashtakavarga, │
    │  yogas          │  │  drishti, house_strength,│
    │  shadbala       │  │  yogas, nakshatra_ctx,   │
    │  sade_sati      │  │  chandra_gati, remedies, │
    │                 │  │  event_windows           │
    └────────┬────────┘  └──────────┬──────────────┘
             │                      │
             │                      ▼
             │           DB: monthly_predictions /
             │           yearly_predictions /
             │           weekly_predictions
             │           (envelope JSONB = all fresh-computed signals)
             │           (interpretation JSONB = deterministic)
             │           (prediction_llm_interpretation = LLM output)
             │                      │
             │         ┌────────────┼──────────────────────┐
             │         │            │                       │
             ▼         ▼            ▼                       ▼
         ┌───────┐  ┌──────┐  ┌──────────┐          ┌──────────┐
         │React  │  │ LLM  │  │ PDF      │          │  Chat    │
         │Frontend│  │(Claude│  │(ReportLab│          │ (Claude  │
         │       │  │/GPT-4)│  │+ SVG)   │          │  API)    │
         │chart- │  │       │  │          │          │          │
         │detail,│  │payload│  │data_     │          │ realtime_│
         │predict│  │builder│  │loader    │          │ context  │
         │-screen│  │→prompt│  │reads DB  │          │ engine   │
         └───────┘  └──────┘  └──────────┘          └──────────┘
```

---

## Biggest Gaps

### 1. Divisional charts (D2, D7, D10) are computed and stored but never sent to LLM
D2 (wealth), D7 (children), and D10 (career) planetary placements are computed at chart creation and stored in `base_charts.payload.divisional_charts`. They appear as SVG charts in the PDF and frontend tabs. However, `payload_builder.py` does not extract these placements as life-area signals. The LLM receives at most a mention that "D10 chart signals if present" should be referenced, but the data is never actually forwarded. Career and finance interpretations would be significantly richer with D10 and D2 planet placements as input signals.

### 2. Yogas not stored in `base_charts.payload` — natal PDF has a gap
Yogas are re-computed fresh by `birth_chart_builder.py` for the UI view and by `prediction_envelope.py` for monthly/yearly predictions. They are stored in `monthly_predictions.envelope` but not in `base_charts.payload`. The `build_birth_chart_report_data()` function for the natal-only PDF tries to read `payload.get("yogas")` which returns `None`. This means the natal chart PDF currently renders no yogas section despite the UI panel showing yogas correctly (because the UI view re-computes them live).

### 3. Shadbala sent to LLM as summary labels only — not the Rupa scores
The payload builder sends only `{strongest_planet, weakest_planet, ranking[:3], weak_count}` to the LLM. Per-planet Rupa values, Sthana Bala, Dig Bala, and Drik Bala components are never forwarded. The LLM cannot reason about, e.g., why a planet is weak (debilitated vs. retrograde vs. directional weakness) or whether a planet's strength offsets a challenging transit.

### 4. Bhinnashtakavarga (per-planet AV tables) not computed
Only the Sarvashtakavarga (sum across all 8 contributors) is computed. Individual planet-level Bhinnashtakavarga tables (e.g., Saturn's own AV for validating Saturn transits through each sign) are not implemented. The engine currently uses Sarvashtakavarga bindus as a proxy for all transit validation, which is a classical approximation rather than the full Parashara method.

### 5. Upagrahas (Gulika, Mandi, etc.) not implemented
There is no upagraha engine. Gulika and Mandi are significant in Tamil Jyotisha tradition (especially for timing death-related matters and inauspicious periods). No upagraha data flows anywhere in the system.

### 6. Tithi/Vara at birth stored but never sent to LLM or rendered in PDF
The natal Panchangam (Tithi, Nakshatra, Yoga, Karana, Vara, Tamil month) is stored in `base_charts.payload.panchangam_birth` and exposed in the UI view model. However, it is not forwarded to the LLM payload and does not appear in the PDF report sections. A user's birth Tithi and Vara have classical significance for the nature of the chart but are invisible in the AI interpretation and PDF.

### 7. Dinaphalam not implemented
Dinaphalam (daily planetary strength based on weekday rulers) is mentioned in the domain glossary but no engine exists. Rahu Kalam and Yamagandam are referenced in the CLAUDE.md domain glossary but are also absent from the engine layer.

### 8. Shadbala and Sade Sati not persisted in base_charts — re-computed on every prediction and UI view
Both Shadbala and Sade Sati are computed fresh at every prediction envelope call and every `build_birth_chart_view_model` call. These are deterministic (given fixed natal data + reference date), so caching them in `base_charts.payload` would eliminate redundant computation. Shadbala in particular is computationally non-trivial.

### 9. Porutham not cached — no DB persistence
Porutham is computed on every `GET /family/groups/{id}/porutham` call. The result (a deterministic 33-point score from two nakshatras/rasis) is not stored in the database, causing needless recomputation on each API call.

### 10. Monthly Panchangam (current Tithi/Vara) not tracked
While birth-time Panchangam is stored, there is no engine that tracks the current day's Tithi, Vara, Nakshatra, Yoga, Karana for use in predictions or the chat. This was listed as a core product feature in the domain glossary.
