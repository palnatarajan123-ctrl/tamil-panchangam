# app/engines/budget_guard.py
"""
Budget guard — call after every LLM call is logged.
Automatically disables LLM if monthly spend hits the threshold.
"""
import uuid
import logging
from datetime import date
import calendar

from app.db.postgres import get_conn

logger = logging.getLogger(__name__)

# Anthropic claude-sonnet-4 pricing (per token)
COST_PER_INPUT_TOKEN = 3.0 / 1_000_000
COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000


def compute_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)


def log_llm_call(db, chart_id: str, call_type: str, period: str,
                 input_tokens: int, output_tokens: int,
                 status: str = "success", fallback_reason: str = None) -> float:
    """
    Unified logger for all LLM calls (prediction + chat).
    Returns cost_usd logged.
    """
    cost_usd = compute_cost(input_tokens, output_tokens)
    total_tokens = input_tokens + output_tokens

    db.execute("""
        INSERT INTO llm_calls
            (id, chart_id, call_type, period, input_tokens, output_tokens,
             total_tokens, cost_usd, status, fallback_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [str(uuid.uuid4()), chart_id, call_type, period, input_tokens, output_tokens,
          total_tokens, cost_usd, status, fallback_reason])

    if status == "success":
        _check_budget(db)

    return cost_usd


def _check_budget(db) -> None:
    """Auto-pause LLM if monthly spend crosses threshold."""
    # llm_budget columns: id(0), monthly_budget_usd(1), auto_pause_enabled(2),
    #   auto_pause_threshold_pct(3), llm_enabled(4), paused_reason(5), paused_at(6), updated_at(7)
    try:
        budget = db.execute(
            "SELECT * FROM llm_budget WHERE id = 1"
        ).fetchone()

        if not budget or not budget[2] or not budget[4]:
            return

        result = db.execute("""
            SELECT COALESCE(SUM(cost_usd), 0.0) AS total
            FROM llm_calls
            WHERE DATE_TRUNC('month', created_at::TIMESTAMP) = DATE_TRUNC('month', NOW())
              AND status = 'success'
        """).fetchone()

        spend = result[0] if result else 0.0
        threshold = budget[1] * (budget[3] / 100.0)

        if spend >= threshold:
            db.execute("""
                UPDATE llm_budget SET
                    llm_enabled = FALSE,
                    paused_reason = 'budget_exceeded',
                    paused_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """)
    except Exception as e:
        logger.warning(f"Budget check failed: {e}")


def get_monthly_summary() -> dict:
    """Returns full summary dict for the admin dashboard API."""
    with get_conn() as db:
        # llm_budget: id(0), monthly_budget_usd(1), auto_pause_enabled(2),
        #   auto_pause_threshold_pct(3), llm_enabled(4), paused_reason(5)
        budget_row = db.execute("SELECT * FROM llm_budget WHERE id = 1").fetchone()
        monthly_budget = budget_row[1] if budget_row else 50.0
        auto_pause_enabled = bool(budget_row[2]) if budget_row else True
        auto_pause_threshold_pct = int(budget_row[3]) if budget_row else 90
        llm_enabled = bool(budget_row[4]) if budget_row else True
        paused_reason = budget_row[5] if budget_row else None

        # MTD spend: spend_mtd(0), input_tokens(1), output_tokens(2), total_tokens(3), total_calls(4)
        spend_row = db.execute("""
            SELECT
                COALESCE(SUM(cost_usd), 0.0)    AS spend_mtd,
                COALESCE(SUM(input_tokens), 0)  AS input_tokens_mtd,
                COALESCE(SUM(output_tokens), 0) AS output_tokens_mtd,
                COALESCE(SUM(total_tokens), 0)  AS total_tokens_mtd,
                COUNT(*)                         AS total_calls
            FROM llm_calls
            WHERE DATE_TRUNC('month', created_at::TIMESTAMP) = DATE_TRUNC('month', NOW())
              AND status = 'success'
        """).fetchone()

        spend_mtd = float(spend_row[0]) if spend_row else 0.0
        input_tokens_mtd = int(spend_row[1]) if spend_row else 0
        output_tokens_mtd = int(spend_row[2]) if spend_row else 0
        total_tokens_mtd = int(spend_row[3]) if spend_row else 0
        total_calls = int(spend_row[4]) if spend_row else 0

        pct_used = round((spend_mtd / monthly_budget * 100), 1) if monthly_budget > 0 else 0.0

        # Burn rate + forecast
        today = date.today()
        days_elapsed = today.day
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_remaining = days_in_month - days_elapsed
        burn_rate = round(spend_mtd / days_elapsed, 6) if days_elapsed > 0 else 0.0
        forecast_eom = round(burn_rate * days_in_month, 4)

        # Breakdown by call_type: call_type(0), calls(1), cost_usd(2)
        breakdown_rows = db.execute("""
            SELECT call_type,
                   COUNT(*) AS calls,
                   COALESCE(SUM(cost_usd), 0.0) AS cost_usd
            FROM llm_calls
            WHERE DATE_TRUNC('month', created_at::TIMESTAMP) = DATE_TRUNC('month', NOW())
              AND status = 'success'
            GROUP BY call_type
        """).fetchall()

        breakdown = {}
        for row in breakdown_rows:
            breakdown[row[0]] = {
                "calls": int(row[1]),
                "cost_usd": round(float(row[2]), 4),
            }

        # Fallback reasons: reason(0), count(1)
        fallback_rows = db.execute("""
            SELECT
                COALESCE(fallback_reason, status) AS reason,
                COUNT(*) AS count
            FROM llm_calls
            WHERE DATE_TRUNC('month', created_at::TIMESTAMP) = DATE_TRUNC('month', NOW())
            GROUP BY reason
        """).fetchall()

        fallbacks = {row[0]: int(row[1]) for row in fallback_rows}

    return {
        "spend_mtd": round(spend_mtd, 4),
        "budget": monthly_budget,
        "pct_used": pct_used,
        "remaining": round(monthly_budget - spend_mtd, 4),
        "total_tokens_mtd": total_tokens_mtd,
        "input_tokens_mtd": input_tokens_mtd,
        "output_tokens_mtd": output_tokens_mtd,
        "total_calls": total_calls,
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "days_remaining": days_remaining,
        "burn_rate_per_day": burn_rate,
        "forecast_eom": forecast_eom,
        "will_exceed_budget": forecast_eom > monthly_budget,
        "llm_enabled": llm_enabled,
        "paused_reason": paused_reason,
        "auto_pause_enabled": auto_pause_enabled,
        "auto_pause_threshold_pct": auto_pause_threshold_pct,
        "breakdown": breakdown,
        "fallbacks": fallbacks,
    }
