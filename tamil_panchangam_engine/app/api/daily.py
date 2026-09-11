# app/api/daily.py
"""
Daily Dinaphalam API

GET /api/prediction/daily?base_chart_id=<id>&date=YYYY-MM-DD

Returns daily Panchangam + inauspicious windows for a given chart and date.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from app.db.postgres import get_conn
from app.core.auth import get_current_user
from app.core.limiter import limiter
from app.engines.dinaphalam_engine import compute_dinaphalam
from app.engines.llm_interpretation_orchestrator import is_llm_enabled
from app.utils.time_utils import get_timezone_from_coordinates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prediction", tags=["Prediction"])


def _get_base_chart_payload(base_chart_id: str) -> dict:
    """Fetch base chart payload from DB."""
    import json
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT payload FROM base_charts WHERE id = %s",
                (base_chart_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Base chart not found")
            raw = row[0]
            if isinstance(raw, str):
                return json.loads(raw)
            return raw
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB error fetching chart {base_chart_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load base chart")


def _generate_daily_llm_guidance(
    result: dict, chart_name: str, base_chart_id: str, user_id: Optional[str] = None,
) -> tuple[Optional[str], bool, bool]:
    """2-3 sentence personalized daily guidance. Low token usage.

    Returns (guidance, capped, paused). Unlike natal_interpretation.py's
    two routes (whose entire value IS the LLM output, hard-429'd on cap --
    see that file), this route already computes and returns real,
    non-LLM Panchangam data (tithi/nakshatra/yoga/rahu-kaalam/etc.)
    regardless of LLM outcome. Discarding that with a 429 just because
    the LLM commentary specifically is capped/paused would be a strictly
    worse response than graceful degradation -- a per-account budget cap
    and the global admin pause are both the same *kind* of condition
    (temporary LLM unavailability, not an identity/security failure like
    Turnstile/auth), so both get graceful-degradation treatment, not
    Turnstile's hard-stop treatment. The caller surfaces `capped` and
    `paused` as distinct `llm_capped`/`llm_paused` response keys.

    `paused` (Part A, 2026-09-11 follow-up) is distinct from `capped`:
    capped is per-account (this user specifically hit their own daily
    cap); paused is global (an admin disabled AI for everyone, or the
    monthly $ budget auto-paused it). Previously both the disabled case
    and the missing-API-key case collapsed into the same silent
    (None, False) return as "no guidance, unspecified reason" -- no way
    for the frontend to show a real "AI is paused" message distinct from
    any other silent-null case.
    """
    if not is_llm_enabled():
        return None, False, True

    # Per-account daily cap (Task 3/backlog #1, 2026-09-10): checked at the
    # same point as the global is_llm_enabled() gate above, before making
    # the paid Anthropic call.
    if user_id:
        from app.engines.budget_guard import check_user_llm_cap
        try:
            with get_conn() as conn:
                check_user_llm_cap(conn, user_id)
        except HTTPException as e:
            if e.status_code == 429:
                return None, True, False
            raise

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, False, False

    try:
        nak = result.get("nakshatra", {})
        tara = result.get("tara_bala", {})
        rahu = result.get("rahu_kaalam", {})
        yama = result.get("yamagandam", {})
        gulika = result.get("gulika_kaalam", {})
        tithi = result.get("tithi", {})
        date_str = result.get("date", "")

        try:
            weekday = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
        except Exception:
            weekday = ""

        prompt = (
            f"You are a Tamil Jyotishi giving brief daily guidance.\n\n"
            f"Date: {date_str} ({weekday})\n"
            f"Person: {chart_name}\n"
            f"Moon Nakshatra today: {nak.get('name', '')} Pada {nak.get('pada', '')}\n"
            f"Tara Bala: {tara.get('name', '')} ({tara.get('quality', '')})\n"
            f"Tithi: {tithi.get('name', '')} {tithi.get('paksha', '')} Paksha\n"
            f"Rahu Kaalam: {rahu.get('start', '')} to {rahu.get('end', '')}\n"
            f"Yamagandam: {yama.get('start', '')} to {yama.get('end', '')}\n"
            f"Gulika Kaalam: {gulika.get('start', '')} to {gulika.get('end', '')}\n\n"
            f"Write exactly 2-3 sentences of practical daily guidance in plain English. "
            f"Be specific to today's tara bala quality and tithi. "
            f"Naturally mention Rahu Kaalam as 'avoid new starts between X and Y'. "
            f"No generic advice. No preamble. Return only the guidance sentences."
        )

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )

        guidance = response.content[0].text.strip()

        try:
            from app.engines.budget_guard import log_llm_call
            with get_conn() as conn:
                log_llm_call(
                    conn,
                    chart_id=base_chart_id,
                    call_type="daily_guidance",
                    period=date_str,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    user_id=user_id,
                )
        except Exception as log_err:
            logger.warning(f"daily_guidance log_llm_call failed: {log_err}")

        return guidance, False, False

    except Exception as e:
        logger.warning(f"Daily LLM guidance failed: {e}")
        return None, False, False


@limiter.limit("10/hour")
@router.get("/daily")
def get_daily_prediction(
    request: Request,
    base_chart_id: str = Query(..., description="Base chart ID"),
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (defaults to today UTC)"),
    user: dict = Depends(get_current_user),
):
    """
    Return daily Panchangam and inauspicious windows for a base chart.

    Requires auth (Depends(get_current_user), REQUIRED not optional) --
    this endpoint makes a direct synchronous LLM call on every request with
    no caching, and was previously reachable with zero auth and zero rate
    limit (see security audit, 2026-09-08). Rate limit added as defense-in-
    depth on top of auth, matching the 10/hour convention used elsewhere
    (prediction.py's /monthly, prediction_yearly.py's /yearly).

    Response includes:
    - rahu_kaalam, yamagandam, gulika_kaalam (start/end local time)
    - nakshatra (today's Moon nakshatra + pada)
    - tara_bala (quality relative to birth nakshatra)
    - tithi (lunar day + paksha)
    - sunrise / sunset (local time)
    """
    payload = _get_base_chart_payload(base_chart_id)

    # Parse target date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        today = datetime.now(timezone.utc)
        target_date = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Extract chart coordinates
    birth_details = payload.get("birth_details", {})
    latitude = birth_details.get("latitude")
    longitude = birth_details.get("longitude")
    if latitude is None or longitude is None:
        raise HTTPException(status_code=422, detail="Chart missing latitude/longitude")

    # Determine birth nakshatra index from stored ephemeris data
    moon_eph = payload.get("ephemeris", {}).get("moon", {})
    nak_data = moon_eph.get("nakshatra", {})
    birth_nak_index = nak_data.get("index")
    if birth_nak_index is None:
        moon_lon = moon_eph.get("longitude_deg", 0.0)
        birth_nak_index = int(moon_lon / (360 / 27)) % 27

    # Determine UTC offset — prefer stored timezone, fall back to coordinate lookup
    try:
        tz_name = birth_details.get("timezone") or get_timezone_from_coordinates(latitude, longitude)
        import pytz
        from datetime import timedelta
        tz = pytz.timezone(tz_name)
        aware = target_date.astimezone(tz)
        utc_offset = aware.utcoffset().total_seconds() / 3600
    except Exception:
        utc_offset = 5.5  # fallback to IST

    ayanamsa = payload.get("chart_metadata", {}).get("ayanamsa", "lahiri")

    result = compute_dinaphalam(
        date_utc=target_date,
        latitude=latitude,
        longitude=longitude,
        birth_nakshatra_index=int(birth_nak_index),
        utc_offset_hours=utc_offset,
        ayanamsa=ayanamsa,
    )

    llm_guidance, llm_capped, llm_paused = _generate_daily_llm_guidance(
        result=result,
        chart_name=birth_details.get("name", ""),
        base_chart_id=base_chart_id,
        user_id=user["id"],
    )

    return {
        "base_chart_id": base_chart_id,
        **result,
        "llm_guidance": llm_guidance,
        "llm_capped": llm_capped,
        "llm_paused": llm_paused,
    }
