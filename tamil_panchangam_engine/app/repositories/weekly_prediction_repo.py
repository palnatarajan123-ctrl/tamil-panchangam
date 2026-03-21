import json
from datetime import datetime
from app.db.postgres import get_conn


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
        INSERT INTO weekly_predictions
        (id, base_chart_id, year, week, status, envelope, synthesis, interpretation, engine_version, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            base_chart_id = EXCLUDED.base_chart_id,
            year = EXCLUDED.year,
            week = EXCLUDED.week,
            status = EXCLUDED.status,
            envelope = EXCLUDED.envelope,
            synthesis = EXCLUDED.synthesis,
            interpretation = EXCLUDED.interpretation,
            engine_version = EXCLUDED.engine_version,
            generated_at = EXCLUDED.generated_at
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
