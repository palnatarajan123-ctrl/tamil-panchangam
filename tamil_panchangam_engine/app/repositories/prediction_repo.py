import json
from datetime import datetime
from app.db.duckdb import get_conn

def get_monthly_prediction(base_chart_id, year, month):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT envelope, synthesis, interpretation
            FROM monthly_predictions
            WHERE base_chart_id = ?
              AND year = ?
              AND month = ?
            """,
            [base_chart_id, year, month],
        ).fetchone()

    if not row:
        return None

    return {
        "envelope": row[0],
        "synthesis": row[1],
        "interpretation": row[2],
    }

def save_monthly_prediction(
    _,
    base_chart_id,
    year,
    month,
    status,
    envelope,
    synthesis,
    interpretation,
    engine_version,
):
    con = get_conn()
    pid = f"{base_chart_id}:{year}:{month}"

    con.execute(
        """
        INSERT OR REPLACE INTO monthly_predictions
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            pid,
            base_chart_id,
            year,
            month,
            status,
            envelope,
            synthesis,
            interpretation,
            engine_version,
            datetime.utcnow(),
        ],
    )
