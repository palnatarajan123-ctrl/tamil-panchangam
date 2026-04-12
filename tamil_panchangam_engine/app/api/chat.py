# app/api/chat.py
"""
Jyotishi Chat — context-aware astrological Q&A per chart.
- Streaming responses via Server-Sent Events
- Question limits: free=10/month, registered=25/month, admin=unlimited
- Chat history stored per user+chart+month
- Context assembled from birth chart + current dasha + monthly/yearly prediction
"""
import os
import json
import logging
import uuid
from datetime import datetime, date, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.core.auth import get_current_user, get_current_user_optional
from app.db.postgres import get_conn
from app.engines.yoga_engine import compute_yogas
from app.engines.sade_sati_engine import compute_sade_sati
from app.engines.shadbala_engine import compute_shadbala
from app.engines.budget_guard import log_llm_call
from app.engines.dasha_resolver import resolve_antar_dasha

logger = logging.getLogger(__name__)

CHAT_LIMITS = {
    "free": 10,
    "user": 25,
    "admin": None,  # unlimited
}

SYSTEM_PROMPT_TEMPLATE = """You are Jyotishi, a warm and direct personal astrologer for {name}.

CHART CONTEXT:
- Born: {date}, {time}, {place}
- Lagna: {lagna_sign} | Moon: {moon_sign} ({moon_nakshatra})
- Current Mahadasha: {mahadasha} | Antardasha: {antardasha}
- Key planets: {planets_summary}
- Active yogas: {yogas_summary}
- Shadbala: {shadbala_summary}
- Saturn influence: {sade_sati_summary}
- Monthly outlook: {monthly_summary}
- Yearly outlook: {yearly_summary}

RESPONSE FORMAT — strictly follow this every time:
1. One direct answer in plain English — yes/likely/unlikely/no + one sentence why. No astrology jargon unless essential.
2. One practical suggestion the person can act on.
3. One short closing line — a memorable takeaway or gentle caution.

RULES:
- Talk to {name} directly — use "you" and "your"
- Only mention a planet or dasha by name if it directly explains the answer
- No long lists, no multiple paragraphs of analysis
- If the chart is mixed, say so simply: "Mixed signals here —"
- If the question is outside astrology scope, redirect warmly in one sentence

TIME HORIZON RULE:
- If the question is about a Mahadasha (6–20 years), answer in broad
  themes only. Do not name specific months or years.
- If the question is about an Antardasha, season-level language is fine.
- Never say 'this week' or 'next week' unless the user explicitly asked
  about the current week.
- Never give a specific date or month for broad questions.

AVOID REPEATING VISIBLE INFORMATION:
- Do not restate birth details, chart basics, or period names the user
  can already see on screen.
- Lead with the insight, not the chart data.

RESPONSE LENGTH:
- Conversational questions (yes/no, timing, quick reads): 3–5 sentences, under 80 words.
- Deep life questions (life purpose, major decisions, long-period analysis): up to 5 short paragraphs.
- Follow-up questions: always shorter than the preceding answer.
- Never pad with "Great question!", summaries, or restating the question."""

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    base_chart_id: str
    question: str
    history: list[ChatMessage] = []
    reading_as_name: Optional[str] = None  # family context: whose chart is being read
    context_type: Optional[str] = None  # "child:{member_id}" enriches prompt with cached prediction
    group_id: Optional[str] = None  # family group — triggers multi-member chart context


def _get_question_count(user_id: str, base_chart_id: str) -> int:
    """Get question count for current month."""
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    with get_conn() as conn:
        row = conn.execute("""
            SELECT question_count FROM chat_usage
            WHERE user_id = ? AND base_chart_id = ? AND month_key = ?
        """, [user_id, base_chart_id, month_key]).fetchone()
    return row[0] if row else 0


def _increment_question_count(user_id: str, base_chart_id: str) -> None:
    """Increment or insert question count for current month."""
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    with get_conn() as conn:
        existing = conn.execute("""
            SELECT id FROM chat_usage
            WHERE user_id = ? AND base_chart_id = ? AND month_key = ?
        """, [user_id, base_chart_id, month_key]).fetchone()
        if existing:
            conn.execute("""
                UPDATE chat_usage SET question_count = question_count + 1
                WHERE user_id = ? AND base_chart_id = ? AND month_key = ?
            """, [user_id, base_chart_id, month_key])
        else:
            conn.execute("""
                INSERT INTO chat_usage (id, user_id, base_chart_id, month_key, question_count)
                VALUES (?, ?, ?, ?, 1)
            """, [str(uuid.uuid4()), user_id, base_chart_id, month_key])


def _save_chat_message(user_id: str, base_chart_id: str, session_id: str, role: str, content: str) -> None:
    """Persist a single chat message."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO chat_messages (id, user_id, base_chart_id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [str(uuid.uuid4()), user_id, base_chart_id, session_id, role, content,
              datetime.now(timezone.utc).isoformat()])


def _build_chat_context(base_chart_id: str) -> dict:
    """Assemble chart context for system prompt."""
    with get_conn() as conn:
        chart = conn.execute(
            "SELECT payload FROM base_charts WHERE id = ?",
            [base_chart_id]
        ).fetchone()
        monthly = conn.execute(
            "SELECT interpretation FROM monthly_predictions WHERE base_chart_id = ? ORDER BY created_at DESC LIMIT 1",
            [base_chart_id]
        ).fetchone()
        yearly = conn.execute(
            "SELECT interpretation FROM yearly_predictions WHERE base_chart_id = ? ORDER BY created_at DESC LIMIT 1",
            [base_chart_id]
        ).fetchone()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    payload = chart[0] if isinstance(chart[0], dict) else json.loads(chart[0])
    birth = payload.get("birth_details", {})
    ephemeris = payload.get("ephemeris", {})
    planets = ephemeris.get("planets", {})
    dashas = payload.get("dashas", {})

    # Lagna
    lagna_sign = ephemeris.get("lagna", {}).get("rasi", "unknown")

    # Moon
    moon_data = ephemeris.get("moon", {})
    moon_sign = moon_data.get("rasi", planets.get("Moon", {}).get("rasi", "unknown"))
    nakshatra_raw = moon_data.get("nakshatra", {})
    moon_nakshatra = nakshatra_raw.get("name", "unknown") if isinstance(nakshatra_raw, dict) else str(nakshatra_raw) if nakshatra_raw else "unknown"

    # Planets summary
    planet_bits = []
    for p in ["Sun", "Moon", "Mars", "Jupiter", "Saturn", "Rahu", "Venus", "Mercury", "Ketu"]:
        pdata = planets.get(p, {})
        if isinstance(pdata, dict):
            rasi = pdata.get("rasi", "")
            if rasi:
                retro = " (R)" if pdata.get("is_retrograde") else ""
                planet_bits.append(f"{p} in {rasi}{retro}")
    planets_summary = ", ".join(planet_bits) or "not available"

    # Dasha
    mahadasha = "unknown"
    antardasha = "unknown"
    vimshottari = dashas.get("vimshottari", {}) if isinstance(dashas, dict) else {}
    if isinstance(vimshottari, dict):
        current = vimshottari.get("current", {})
        if isinstance(current, dict):
            mahadasha = current.get("lord", "unknown")
            antar = current.get("antar", {})
            if isinstance(antar, dict):
                antardasha = antar.get("lord", "unknown")

    # Yogas — compute fresh using yoga engine
    yogas_summary = "none notable"
    try:
        yogas = compute_yogas(payload)
        if isinstance(yogas, dict):
            present = [
                y.get("name", k)
                for k, y in yogas.items()
                if isinstance(y, dict) and y.get("present")
            ]
            if not present:
                present = yogas.get("present_yogas", [])
                if isinstance(present, list):
                    present = [y.get("name", str(y)) if isinstance(y, dict) else str(y) for y in present]
            if present:
                yogas_summary = ", ".join(str(y) for y in present[:5])
    except Exception as e:
        logger.warning(f"Yogas computation failed: {e}")

    # Shadbala — compute fresh
    shadbala_summary = "not available"
    try:
        shadbala = compute_shadbala(payload)
        if isinstance(shadbala, dict) and not shadbala.get("error"):
            strongest = shadbala.get("strongest_planet", "")
            weakest = shadbala.get("weakest_planet", "")
            if strongest or weakest:
                shadbala_summary = f"Strongest: {strongest}, Weakest: {weakest}"
    except Exception as e:
        logger.warning(f"Shadbala computation failed: {e}")

    # Sade Sati — compute fresh
    sade_sati_summary = "not active"
    try:
        sade_sati = compute_sade_sati(payload)
        if isinstance(sade_sati, dict):
            ss = sade_sati.get("sade_sati", {})
            ashtama = sade_sati.get("ashtama_shani", {})
            alert = sade_sati.get("alert_level", "")
            if isinstance(ss, dict) and ss.get("active"):
                phase = ss.get("phase", "")
                sade_sati_summary = f"Sade Sati active ({phase} phase), alert: {alert}"
            elif isinstance(ashtama, dict) and ashtama.get("active"):
                sade_sati_summary = f"Ashtama Shani active, alert: {alert}"
    except Exception as e:
        logger.warning(f"Sade Sati computation failed: {e}")

    # Monthly summary from stored LLM interpretation
    monthly_summary = "not available"
    if monthly:
        try:
            mdata = monthly[0] if isinstance(monthly[0], dict) else json.loads(monthly[0] or "{}")
            llm = mdata.get("llm_interpretation", {})
            if isinstance(llm, dict):
                exec_summary = llm.get("executive_summary", "")
                why = llm.get("why_this_period", {})
                why_text = why.get("plain_english", "") if isinstance(why, dict) else ""
                monthly_summary = (exec_summary[:150] + " " + why_text[:100]).strip() or "not available"
        except Exception:
            pass

    # Yearly summary
    yearly_summary = "not available"
    if yearly:
        try:
            ydata = yearly[0] if isinstance(yearly[0], dict) else json.loads(yearly[0] or "{}")
            llm = ydata.get("llm_interpretation", {})
            if isinstance(llm, dict):
                exec_summary = llm.get("executive_summary", "")
                if exec_summary:
                    yearly_summary = exec_summary[:200]
        except Exception:
            pass

    return {
        "name": birth.get("name", "the chart holder"),
        "date": birth.get("date_of_birth", "unknown"),
        "time": birth.get("time_of_birth", "unknown"),
        "place": birth.get("place_of_birth", "unknown"),
        "lagna_sign": lagna_sign,
        "moon_sign": moon_sign,
        "moon_nakshatra": moon_nakshatra,
        "mahadasha": mahadasha,
        "antardasha": antardasha,
        "planets_summary": planets_summary,
        "yogas_summary": yogas_summary,
        "shadbala_summary": shadbala_summary,
        "sade_sati_summary": sade_sati_summary,
        "monthly_summary": monthly_summary,
        "yearly_summary": yearly_summary,
    }


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """Streaming chat endpoint — returns SSE stream."""
    user_id = user["id"]
    user_role = user.get("role", "user")

    # Check question limit
    limit = CHAT_LIMITS.get(user_role)
    if limit is not None:
        count = _get_question_count(user_id, req.base_chart_id)
        if count >= limit:
            now = datetime.now(timezone.utc)
            reset_month = now.month + 1 if now.month < 12 else 1
            reset_year = now.year if now.month < 12 else now.year + 1
            raise HTTPException(
                status_code=429,
                detail=f"You've used your {limit} questions for this chart this month. "
                       f"Your questions reset on {reset_year}-{reset_month:02d}-01."
            )

    # Build context
    try:
        context = _build_chat_context(req.base_chart_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to build chat context: {e}")
        raise HTTPException(status_code=500, detail="Failed to load chart context")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(**context)
    if req.reading_as_name:
        system_prompt = f"Reading from {req.reading_as_name}'s chart.\n\n" + system_prompt

    # Build family member context if this is a family chat
    family_member_context = ""
    if req.group_id:
        with get_conn() as conn:
            members = conn.execute("""
                SELECT fm.role, fm.display_name, fm.chart_id,
                       bc.payload
                FROM family_members fm
                JOIN base_charts bc ON bc.id = fm.chart_id
                WHERE fm.group_id = %s
                ORDER BY fm.role
            """, (req.group_id,)).fetchall()

            member_lines = []
            for m in members:
                role, display_name, chart_id, payload_raw = m
                payload = payload_raw if isinstance(payload_raw, dict) \
                          else json.loads(payload_raw or "{}")
                birth = payload.get("birth_details", {})
                moon = payload.get("ephemeris", {}).get("moon", {})
                vimshottari = payload.get("dashas", {}).get("vimshottari", {})
                dasha = resolve_antar_dasha(
                    vimshottari=vimshottari,
                    reference_date=datetime.today()
                )
                ss = compute_sade_sati(payload)
                ss_data = ss.get("sade_sati", {}) if ss else {}

                name = display_name or birth.get("name", role)
                nak = moon.get("nakshatra", {})
                nak_name = nak.get("name", "") if isinstance(nak, dict) else nak
                rasi = moon.get("rasi", "")
                maha = dasha.get("maha", {}).get("lord", "—") if dasha else "—"
                antar = dasha.get("antar", {}).get("lord", "—") if dasha else "—"
                ss_active = ss_data.get("active", False)
                ss_phase = ss_data.get("phase_name", "")

                member_lines.append(
                    f"{role.upper()} — {name}: "
                    f"Nakshatra {nak_name}, Rasi {rasi}, "
                    f"Dasha {maha}›{antar}, "
                    f"Sade Sati: {'Active – ' + ss_phase if ss_active else 'None'}"
                )

            if member_lines:
                family_member_context = (
                    "\n\n## FAMILY CONTEXT\n"
                    "You are advising this couple/family. "
                    "Use ALL members' charts when answering family questions:\n"
                    + "\n".join(member_lines)
                )

    if family_member_context:
        system_prompt = system_prompt + family_member_context

    # Enrich with child prediction context if requested
    if req.context_type and req.context_type.startswith("child:"):
        member_id = req.context_type.split(":", 1)[1]
        with get_conn() as conn:
            child_pred = conn.execute("""
                SELECT overall_narrative, education, career_aptitude,
                       marriage_window, key_takeaways
                FROM family_child_predictions
                WHERE member_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, [member_id]).fetchone()
        if child_pred:
            overall = (child_pred[0] or "")[:500]
            education = (child_pred[1] or "")[:300]
            career = (child_pred[2] or "")[:300]
            takeaways = (child_pred[4] or "")[:300]
            child_context = f"""

## Child's Prediction Context
The user is asking about a child whose Jyotisha profile is:

Overall: {overall}

Education outlook: {education}

Career aptitude: {career}

Key takeaways: {takeaways}

When answering, refer to this child's specific profile.
Frame all responses in parent-friendly language.
"""
            system_prompt = system_prompt + child_context

    # Build messages array (last 6 pairs max)
    history_trimmed = req.history[-12:] if len(req.history) > 12 else req.history
    messages = [{"role": m.role, "content": m.content} for m in history_trimmed]
    messages.append({"role": "user", "content": req.question})

    # Session ID — reuse from history or create new
    session_id = str(uuid.uuid4())

    # Save user message
    _save_chat_message(user_id, req.base_chart_id, session_id, "user", req.question)
    _increment_question_count(user_id, req.base_chart_id)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM not configured")

    # Budget gate — check llm_budget before calling Anthropic
    with get_conn() as conn:
        budget_row = conn.execute(
            "SELECT llm_enabled, paused_reason FROM llm_budget WHERE id = 1"
        ).fetchone()

    async def generate():
        if budget_row and not budget_row[0]:
            yield f"data: {json.dumps({'error': 'llm_paused', 'reason': budget_row[1]})}\n\n"
            return

        import anthropic
        full_response = []
        input_tokens = 0
        output_tokens = 0
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=250,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response.append(text)
                    yield f"data: {json.dumps({'text': text})}\n\n"
                # Capture usage before exiting the stream context
                final_msg = stream.get_final_message()
                input_tokens = final_msg.usage.input_tokens
                output_tokens = final_msg.usage.output_tokens

            # Save assistant response
            _save_chat_message(
                user_id, req.base_chart_id, session_id,
                "assistant", "".join(full_response)
            )

            # Log to llm_calls and check budget
            with get_conn() as db:
                log_llm_call(
                    db=db,
                    chart_id=req.base_chart_id,
                    call_type="family_chat" if req.reading_as_name else "chat",
                    period="chat",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    status="success",
                )

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            # Log failed call
            try:
                with get_conn() as db:
                    log_llm_call(
                        db=db,
                        chart_id=req.base_chart_id,
                        call_type="family_chat" if req.reading_as_name else "chat",
                        period="chat",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        status="error",
                        fallback_reason=str(e)[:100],
                    )
            except Exception:
                pass
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history/{base_chart_id}")
def get_chat_history(
    base_chart_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Return recent chat history for a chart."""
    user_id = user["id"]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT role, content, created_at FROM chat_messages
            WHERE user_id = ? AND base_chart_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, [user_id, base_chart_id, limit]).fetchall()
    messages = [{"role": r[0], "content": r[1], "created_at": r[2]} for r in reversed(rows)]
    return {"messages": messages}


@router.get("/usage/{base_chart_id}")
def get_chat_usage(
    base_chart_id: str,
    user: dict = Depends(get_current_user),
):
    """Return question count and limit for current month."""
    user_id = user["id"]
    user_role = user.get("role", "user")
    count = _get_question_count(user_id, base_chart_id)
    limit = CHAT_LIMITS.get(user_role)
    return {
        "used": count,
        "limit": limit,
        "unlimited": limit is None,
        "remaining": None if limit is None else max(0, limit - count),
    }
