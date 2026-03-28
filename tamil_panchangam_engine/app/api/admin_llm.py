# app/api/admin_llm.py
"""
Admin LLM API Endpoints v1.0

Provides endpoints for:
- LLM status check
- Monthly token usage
- Recent LLM calls
- Fallback summary
- Toggle LLM enabled/disabled

All endpoints are prefixed with /admin/llm
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.postgres import get_conn
from app.engines.budget_guard import get_monthly_summary
from app.engines.llm_interpretation_orchestrator import (
    is_llm_enabled,
    set_llm_enabled,
    get_monthly_token_usage,
    PROMPT_VERSION,
    LLM_MONTHLY_TOKEN_BUDGET
)
from app.llm.providers import anthropic_provider as openai_provider  # openai_provider alias kept for internal references

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/llm", tags=["Admin LLM"])


class LLMStatusResponse(BaseModel):
    llm_enabled: bool
    active_provider: str
    provider_available: bool
    current_prompt_version: str
    monthly_budget: int


class MonthlyUsageResponse(BaseModel):
    budget: int
    used: int
    remaining: int
    percent_used: float


class RecentCallEntry(BaseModel):
    id: str
    base_chart_id: str
    period_type: str
    period_key: str
    total_tokens: Optional[int]
    fallback_reason: Optional[str]
    created_at: str


class FallbackSummaryEntry(BaseModel):
    reason: str
    count: int


class ToggleRequest(BaseModel):
    enabled: bool


class ToggleResponse(BaseModel):
    success: bool
    llm_enabled: bool


@router.get("/status", response_model=LLMStatusResponse)
def get_llm_status():
    """Get current LLM status and configuration."""
    provider_info = openai_provider.get_provider_info()
    
    return LLMStatusResponse(
        llm_enabled=is_llm_enabled(),
        active_provider=provider_info["provider"] if provider_info["available"] else "none",
        provider_available=provider_info["available"],
        current_prompt_version=PROMPT_VERSION,
        monthly_budget=LLM_MONTHLY_TOKEN_BUDGET
    )


@router.get("/usage/monthly", response_model=MonthlyUsageResponse)
def get_monthly_usage():
    """Get token usage for current month."""
    usage = get_monthly_token_usage()
    return MonthlyUsageResponse(**usage)


@router.get("/usage/recent", response_model=List[RecentCallEntry])
def get_recent_calls(limit: int = 20):
    """Get recent LLM calls."""
    try:
        with get_conn() as conn:
            results = conn.execute("""
                SELECT id, base_chart_id, period_type, period_key,
                       total_tokens, fallback_reason, created_at
                FROM prediction_llm_interpretation
                ORDER BY created_at DESC
                LIMIT ?
            """, [limit]).fetchall()
            
            entries = []
            for row in results:
                entries.append(RecentCallEntry(
                    id=str(row[0]),
                    base_chart_id=str(row[1]),
                    period_type=str(row[2]),
                    period_key=str(row[3]),
                    total_tokens=row[4],
                    fallback_reason=row[5],
                    created_at=str(row[6])
                ))
            return entries
    except Exception as e:
        logger.error(f"Failed to get recent calls: {e}")
        return []


@router.get("/fallback-summary", response_model=List[FallbackSummaryEntry])
def get_fallback_summary():
    """Get fallback reasons summary for current month."""
    try:
        with get_conn() as conn:
            results = conn.execute("""
                SELECT 
                    COALESCE(fallback_reason, 'success') AS reason,
                    COUNT(*) AS count
                FROM prediction_llm_interpretation
                WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY fallback_reason
                ORDER BY count DESC
            """).fetchall()
            
            return [
                FallbackSummaryEntry(reason=str(row[0]), count=int(row[1]))
                for row in results
            ]
    except Exception as e:
        logger.error(f"Failed to get fallback summary: {e}")
        return []


@router.post("/toggle", response_model=ToggleResponse)
def toggle_llm(request: ToggleRequest):
    """Enable or disable LLM interpretation."""
    success = set_llm_enabled(request.enabled)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to toggle LLM state")

    # Also sync llm_budget singleton
    try:
        with get_conn() as conn:
            conn.execute("""
                UPDATE llm_budget SET
                    llm_enabled = ?,
                    paused_reason = CASE WHEN ? = FALSE THEN 'manual' ELSE NULL END,
                    paused_at = CASE WHEN ? = FALSE THEN CURRENT_TIMESTAMP ELSE NULL END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, [request.enabled, request.enabled, request.enabled])
    except Exception as e:
        logger.warning(f"Failed to sync llm_budget on toggle: {e}")

    return ToggleResponse(
        success=True,
        llm_enabled=request.enabled
    )


# ── New v2 endpoints ─────────────────────────────────────────────────────

@router.get("/summary")
def llm_summary_v2():
    """Monthly cost/budget summary for admin dashboard v2."""
    try:
        return get_monthly_summary()
    except Exception as e:
        logger.error(f"Failed to get LLM summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calls")
def llm_calls_list(page: int = 1, per_page: int = 20, call_type: Optional[str] = None):
    """Paginated list of LLM calls from llm_calls table."""
    offset = (page - 1) * per_page
    try:
        with get_conn() as conn:
            if call_type:
                rows = conn.execute("""
                    SELECT id, chart_id, call_type, period,
                           input_tokens, output_tokens, total_tokens,
                           cost_usd, status, fallback_reason, created_at
                    FROM llm_calls
                    WHERE call_type = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, [call_type, per_page, offset]).fetchall()
                total_row = conn.execute(
                    "SELECT COUNT(*) FROM llm_calls WHERE call_type = ?", [call_type]
                ).fetchone()
            else:
                rows = conn.execute("""
                    SELECT id, chart_id, call_type, period,
                           input_tokens, output_tokens, total_tokens,
                           cost_usd, status, fallback_reason, created_at
                    FROM llm_calls
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, [per_page, offset]).fetchall()
                total_row = conn.execute(
                    "SELECT COUNT(*) FROM llm_calls"
                ).fetchone()

        total = int(total_row[0]) if total_row else 0
        calls = [
            {
                "id": str(r[0]), "chart_id": str(r[1]) if r[1] else "",
                "call_type": str(r[2]) if r[2] else "prediction",
                "period": str(r[3]) if r[3] else "",
                "input_tokens": int(r[4] or 0), "output_tokens": int(r[5] or 0),
                "total_tokens": int(r[6] or 0), "cost_usd": float(r[7] or 0),
                "status": str(r[8]) if r[8] else "success",
                "fallback_reason": r[9], "created_at": str(r[10]),
            }
            for r in rows
        ]
        return {"calls": calls, "total": total, "page": page, "per_page": per_page}
    except Exception as e:
        logger.error(f"Failed to get LLM calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BudgetUpdateRequest(BaseModel):
    monthly_budget_usd: Optional[float] = None
    auto_pause_enabled: Optional[bool] = None
    auto_pause_threshold_pct: Optional[int] = None


@router.post("/budget")
def update_budget(request: BudgetUpdateRequest):
    """Update monthly budget config."""
    try:
        with get_conn() as conn:
            if request.monthly_budget_usd is not None:
                conn.execute(
                    "UPDATE llm_budget SET monthly_budget_usd = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                    [request.monthly_budget_usd]
                )
            if request.auto_pause_enabled is not None:
                conn.execute(
                    "UPDATE llm_budget SET auto_pause_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                    [request.auto_pause_enabled]
                )
            if request.auto_pause_threshold_pct is not None:
                conn.execute(
                    "UPDATE llm_budget SET auto_pause_threshold_pct = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                    [request.auto_pause_threshold_pct]
                )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to update budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ClearCacheRequest(BaseModel):
    base_chart_id: Optional[str] = None


class ClearCacheResponse(BaseModel):
    success: bool
    rows_deleted: int


@router.post("/clear-cache", response_model=ClearCacheResponse)
def clear_interpretation_cache(request: ClearCacheRequest):
    """Clear cached LLM interpretations. If base_chart_id provided, clears only that chart's cache."""
    try:
        with get_conn() as conn:
            if request.base_chart_id:
                count_result = conn.execute(
                    "SELECT COUNT(*) FROM prediction_llm_interpretation WHERE base_chart_id = ?",
                    [request.base_chart_id]
                ).fetchone()
                rows_deleted = count_result[0] if count_result else 0
                conn.execute(
                    "DELETE FROM prediction_llm_interpretation WHERE base_chart_id = ?",
                    [request.base_chart_id]
                )
            else:
                count_result = conn.execute(
                    "SELECT COUNT(*) FROM prediction_llm_interpretation"
                ).fetchone()
                rows_deleted = count_result[0] if count_result else 0
                conn.execute("DELETE FROM prediction_llm_interpretation")
            
        logger.info(f"Cleared {rows_deleted} cached interpretations")
        return ClearCacheResponse(success=True, rows_deleted=rows_deleted)
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
