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
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.core.auth import get_current_user, get_current_user_optional
from app.db.postgres import get_conn

logger = logging.getLogger(__name__)

CHAT_LIMITS = {
    "free": 10,
    "user": 25,
    "admin": None,  # unlimited
}

SYSTEM_PROMPT_TEMPLATE = """You are Jyotishi, a warm and direct Jyotisha astrologer who knows {name}'s chart deeply.

CHART CONTEXT:
- Born: {date}, {time}, {place}
- Lagna: {lagna_sign} | Moon: {moon_sign} ({moon_nakshatra})
- Current Mahadasha: {mahadasha} | Antardasha: {antardasha}
- Key planets: {planets_summary}
- Active yogas: {yogas_summary}
- Monthly outlook: {monthly_summary}
- Yearly outlook: {yearly_summary}

ANSWER RULES:
1. Lead with a direct answer — yes/likely/unlikely/no — in the first sentence
2. Name the specific planet, house, or dasha that drives your answer
3. Give one practical suggestion the person can act on
4. Stay under 120 words unless the question genuinely needs more depth
5. Warm but grounded tone — like a trusted advisor, not a fortune teller
6. Never be vague — if the chart is mixed, say so and explain both sides
7. If the question is outside astrology scope, gently redirect"""

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    base_chart_id: str
    question: str
    history: list[ChatMessage] = []


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
        chart = conn.execute("""
            SELECT payload FROM base_charts WHERE id = ?
        """, [base_chart_id]).fetchone()

        monthly = conn.execute("""
            SELECT interpretation FROM monthly_predictions
            WHERE base_chart_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, [base_chart_id]).fetchone()

        yearly = conn.execute("""
            SELECT interpretation FROM yearly_predictions
            WHERE base_chart_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, [base_chart_id]).fetchone()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    payload = chart[0] if isinstance(chart[0], dict) else json.loads(chart[0])

    birth = payload.get("birth_details", {})
    ephemeris = payload.get("ephemeris", {})
    planets = ephemeris.get("planets", {})
    dasha = payload.get("dasha_periods", {})
    yogas = payload.get("yogas", {})

    # Build planets summary (top 5 most relevant)
    planet_bits = []
    for p in ["Sun", "Moon", "Mars", "Jupiter", "Saturn", "Rahu"]:
        pdata = planets.get(p, {})
        if pdata:
            planet_bits.append(
                f"{p} in {pdata.get('rasi', '')} ({pdata.get('house', '')}H)"
            )
    planets_summary = ", ".join(planet_bits[:5]) or "not available"

    # Dasha context
    current_dasha = dasha.get("current", {}) if isinstance(dasha, dict) else {}
    mahadasha = current_dasha.get("mahadasha", current_dasha.get("mahadasha_lord", "unknown"))
    antardasha = current_dasha.get("antardasha", current_dasha.get("antardasha_lord", "unknown"))

    # Yogas summary
    yoga_list = []
    if isinstance(yogas, dict):
        for yname, ydata in list(yogas.items())[:3]:
            if isinstance(ydata, dict) and ydata.get("present"):
                yoga_list.append(yname)
    yogas_summary = ", ".join(yoga_list) if yoga_list else "none notable"

    # Monthly/yearly summaries
    monthly_summary = "not available"
    if monthly:
        mdata = monthly[0] if isinstance(monthly[0], dict) else json.loads(monthly[0] or "{}")
        llm = mdata.get("llm_interpretation", {})
        if isinstance(llm, dict):
            exec_summary = llm.get("executive_summary", "")
            if exec_summary:
                monthly_summary = exec_summary[:200]

    yearly_summary = "not available"
    if yearly:
        ydata = yearly[0] if isinstance(yearly[0], dict) else json.loads(yearly[0] or "{}")
        llm = ydata.get("llm_interpretation", {})
        if isinstance(llm, dict):
            exec_summary = llm.get("executive_summary", "")
            if exec_summary:
                yearly_summary = exec_summary[:200]

    # Moon info
    moon_data = planets.get("Moon", {})
    moon_sign = moon_data.get("rasi", "unknown")
    moon_nakshatra = moon_data.get("nakshatra", "unknown")

    # Lagna
    lagna_sign = ephemeris.get("lagna", {}).get("rasi", payload.get("lagna_sign", "unknown"))

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

    async def generate():
        import anthropic
        full_response = []
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response.append(text)
                    yield f"data: {json.dumps({'text': text})}\n\n"

            # Save assistant response
            _save_chat_message(
                user_id, req.base_chart_id, session_id,
                "assistant", "".join(full_response)
            )
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
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
