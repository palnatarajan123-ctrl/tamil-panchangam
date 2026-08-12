#!/usr/bin/env python3
"""
Part 1 diagnostic: call generate_llm_interpretation directly for DN chart Sep 2026.
Prints every decision point: prompt loaded, Anthropic raw response, validation result.
"""
import sys, json, os
sys.path.insert(0, ".")

# Load .env manually (postgres.py only loads DATABASE_URL, not ANTHROPIC_API_KEY)
from pathlib import Path
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

CHART_ID = "6ffd91fb-3c4e-4b45-9aa9-a69a047a9dae"
YEAR, MONTH = 2026, 9

# ── 0. Patch _load_prompt_template to print which file was loaded ─────────────

import app.engines.llm_interpretation_orchestrator as orch_mod

_original_load = orch_mod._load_prompt_template

def _debug_load(version="v2"):
    from pathlib import Path
    prompt_file = f"interpretation_prompt_{version}.txt"
    paths = [
        Path(orch_mod.__file__).parent.parent / "llm" / "prompts" / prompt_file,
        Path(f"tamil_panchangam_engine/app/llm/prompts/{prompt_file}"),
    ]
    for p in paths:
        if p.exists():
            text = p.read_text()
            print(f"\n[PROMPT] Loaded: {p}")
            print(f"[PROMPT] Length: {len(text)} chars")
            print(f"[PROMPT] First 300 chars:\n{text[:300]}")
            return text
    print(f"\n[PROMPT] WARNING: {prompt_file} NOT FOUND — returning stub fallback")
    return _original_load(version)

orch_mod._load_prompt_template = _debug_load

# ── 1. Patch call_openai to intercept raw Anthropic response ─────────────────

import app.llm.providers.anthropic_provider as ap_mod

_original_call = ap_mod.call_llm

def _debug_call(system_prompt, user_prompt, max_tokens=1500):
    print(f"\n[ANTHROPIC] Calling claude with max_tokens={max_tokens}")
    print(f"[ANTHROPIC] system_prompt length: {len(system_prompt)} chars")
    print(f"[ANTHROPIC] user_prompt length: {len(user_prompt)} chars")
    result, usage, error = _original_call(system_prompt, user_prompt, max_tokens)
    if error:
        print(f"[ANTHROPIC] ERROR: {error}")
    else:
        raw = json.dumps(result)
        print(f"[ANTHROPIC] Response received: {len(raw)} chars")
        print(f"[ANTHROPIC] First 500 chars of response:\n{raw[:500]}")
        print(f"[ANTHROPIC] engine_version in response: {result.get('engine_version', '(MISSING)')}")
        if usage:
            print(f"[ANTHROPIC] Tokens: {usage.get('total_tokens')} total "
                  f"({usage.get('prompt_tokens')} in / {usage.get('completion_tokens')} out)")
    return result, usage, error

ap_mod.call_llm = _debug_call
# call_openai is an alias — patch it too
ap_mod.call_openai = _debug_call
# The orchestrator imported openai_provider as an alias — re-patch it on the module
orch_mod.openai_provider.call_openai = _debug_call

# ── 2. Patch _validate_llm_output to show which check fails ──────────────────

_original_validate = orch_mod._validate_llm_output

def _debug_validate(output):
    result = _original_validate(output)
    ev = output.get("engine_version", "(missing)")
    print(f"\n[VALIDATE] engine_version={ev!r}  → {'PASS ✓' if result else 'FAIL ✗'}")
    return result

orch_mod._validate_llm_output = _debug_validate

# ── 3. Load base chart from DB ────────────────────────────────────────────────

from app.db.postgres import get_conn
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.repositories.prediction_repo import get_monthly_prediction

print(f"\n{'='*60}")
print(f"[DB] Loading base chart {CHART_ID}")

with get_conn() as conn:
    base_chart = get_base_chart_by_id(conn, CHART_ID)

if base_chart is None:
    print("[DB] ERROR: chart not found"); sys.exit(1)

base_chart_payload = (
    base_chart["payload"]
    if isinstance(base_chart["payload"], dict)
    else json.loads(base_chart["payload"])
)
print(f"[DB] Chart loaded. Keys: {list(base_chart_payload.keys())[:8]}")
print(f"[DB] has upagrahas: {'upagrahas' in base_chart_payload}")
print(f"[DB] has predictive_signals: {'predictive_signals' in base_chart_payload}")

# ── 4. Load or build envelope + synthesis ────────────────────────────────────

existing = get_monthly_prediction(CHART_ID, YEAR, MONTH)

if existing:
    print(f"\n[DB] Found existing monthly prediction — using its envelope/synthesis")
    envelope = existing["envelope"] if isinstance(existing["envelope"], dict) else json.loads(existing["envelope"])
    synthesis = existing["synthesis"] if isinstance(existing["synthesis"], dict) else json.loads(existing["synthesis"])
    interp = existing.get("interpretation")
    if interp:
        interp = interp if isinstance(interp, dict) else json.loads(interp)
    llm_interp = interp.get("llm_interpretation") if interp else None
    if llm_interp:
        print(f"[DB] Existing llm_interpretation engine_version: {llm_interp.get('engine_version', '(missing)')}")
    else:
        print(f"[DB] No llm_interpretation merged yet")
    ai_interp = interp.get("ai_interpretation", {}) if interp else {}
else:
    print(f"\n[DB] No existing prediction — building envelope + synthesis fresh")
    from app.engines.prediction_envelope import build_monthly_prediction_envelope
    from app.engines.synthesis_engine import synthesize_from_envelope
    from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation
    envelope = build_monthly_prediction_envelope(base_chart=base_chart_payload, year=YEAR, month=MONTH)
    synthesis = synthesize_from_envelope(envelope)
    life_areas = synthesis.get("life_areas")
    if isinstance(life_areas, dict) and "scores" in life_areas:
        synthesis["life_areas"] = life_areas["scores"]
    ai_interp = generate_interpretation(envelope=envelope, synthesis=synthesis, year=YEAR, month=MONTH)

# ── 5. Clear any cached v7 entry so we force a fresh Anthropic call ──────────

period_key = f"{YEAR}-{MONTH:02d}"
print(f"\n[CACHE] Clearing prediction_llm_interpretation for {CHART_ID}/{period_key}/v7")
with get_conn() as conn:
    conn.execute(
        """DELETE FROM prediction_llm_interpretation
           WHERE base_chart_id = %s AND period_type = 'monthly'
             AND period_key = %s AND prompt_version = 'v7'""",
        (CHART_ID, period_key)
    )

# ── 6. Call generate_llm_interpretation directly ─────────────────────────────

from app.engines.llm_interpretation_orchestrator import generate_llm_interpretation

print(f"\n{'='*60}")
print(f"[LLM] Calling generate_llm_interpretation for {CHART_ID} monthly {YEAR}-{MONTH:02d}")

result = generate_llm_interpretation(
    base_chart_id=CHART_ID,
    envelope=envelope,
    synthesis=synthesis,
    deterministic_interpretation=ai_interp,
    year=YEAR,
    period_type="monthly",
    period_key=period_key,
    feature_name="prediction",
    explainability_mode="full",
    base_chart_payload=base_chart_payload,
)

print(f"\n{'='*60}")
print(f"[RESULT] llm_metadata: {json.dumps(result.get('llm_metadata', {}), indent=2)}")
llm = result.get("llm_interpretation") or {}
final_ev = llm.get("engine_version", "(missing)") if isinstance(llm, dict) else "(not a dict)"
print(f"[RESULT] Final engine_version stored: {final_ev}")
if isinstance(llm, dict) and "executive_summary" in llm:
    main_theme = llm.get("executive_summary", {}).get("main_theme", "")
    print(f"[RESULT] executive_summary.main_theme: {main_theme[:120]}")
if isinstance(llm, dict) and "event_predictions" in llm:
    ep = llm["event_predictions"]
    print(f"[RESULT] event_predictions count: {len(ep) if isinstance(ep, list) else 'not a list'}")
print(f"\n{'='*60} DONE")
