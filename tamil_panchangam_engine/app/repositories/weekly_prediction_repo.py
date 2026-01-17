import json
from datetime import datetime
from app.db.duckdb import get_conn


def get_weekly_prediction(base_chart_id, year, week):
    """
    Fetch a persisted weekly prediction.
    """
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT envelope, synthesis, interpretation
            FROM weekly_predictions
            WHERE base_chart_id = ?
              AND year = ?
              AND week = ?
            """,
            [base_chart_id, year, week],
        ).fetchone()

    if not row:
        return None

    return {
        "envelope": row[0],
        "synthesis": row[1],
        "interpretation": row[2],
    }


def save_weekly_prediction(
    *,
    base_chart_id,
    year,
    week,
    status,
    envelope,
    synthesis,
    interpretation,
    engine_version,
):
    """
    Persist weekly prediction to DuckDB.

    NOTE:
    - Explainability is NOT persisted (derived only)
    - Mirrors save_monthly_prediction behavior
    """
    con = get_conn()
    pid = f"{base_chart_id}:{year}:W{week}"

    con.execute(
        """
        INSERT OR REPLACE INTO weekly_predictions
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            pid,
            base_chart_id,
            year,
            week,
            status,
            envelope,
            synthesis,
            interpretation,
            engine_version,
            datetime.utcnow(),
        ],
    )
