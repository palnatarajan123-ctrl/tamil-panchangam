# app/repositories/prediction_repo.py

import json
from datetime import datetime
from app.db.duckdb import get_conn


# ============================================================
# READ: Monthly Prediction
# ============================================================

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


# ============================================================
# WRITE: Monthly Prediction
# ============================================================

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
    """
    Persist monthly prediction.
    Explainability is intentionally NOT persisted (EPIC-8).
    """

    prediction_id = f"{base_chart_id}:{year}:{month}"

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO monthly_predictions
            (id, base_chart_id, year, month, status, envelope, synthesis, interpretation, engine_version, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                base_chart_id = EXCLUDED.base_chart_id,
                year = EXCLUDED.year,
                month = EXCLUDED.month,
                status = EXCLUDED.status,
                envelope = EXCLUDED.envelope,
                synthesis = EXCLUDED.synthesis,
                interpretation = EXCLUDED.interpretation,
                engine_version = EXCLUDED.engine_version,
                created_at = EXCLUDED.created_at
            """,
            [
                prediction_id,
                base_chart_id,
                year,
                month,
                status,
                json.dumps(envelope),
                json.dumps(synthesis),
                json.dumps(interpretation) if interpretation else None,
                engine_version,
                datetime.utcnow(),
            ],
        )
        
def get_predictions_for_year(
    db,
    chart_id: str,
    year: int,
):
    """
    Fetch all persisted monthly predictions for a chart in a given year.
    Read-only. Used for PDF reporting.
    """

    query = """
        SELECT *
        FROM monthly_predictions
        WHERE base_chart_id = ?
          AND year = ?
        ORDER BY month ASC
    """

    return db.exec(query, (chart_id, year)).all()
