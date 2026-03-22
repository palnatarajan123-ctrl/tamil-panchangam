import json
from datetime import datetime
from app.db.postgres import get_conn


def get_yearly_prediction(base_chart_id, year):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT envelope, synthesis, interpretation
            FROM yearly_predictions
            WHERE base_chart_id = ?
              AND year = ?
            """,
            [base_chart_id, year],
        ).fetchone()

    if not row:
        return None

    return {
        "envelope": row[0],
        "synthesis": row[1],
        "interpretation": row[2],
    }


def save_yearly_prediction(
    *,
    base_chart_id,
    year,
    status,
    envelope,
    synthesis,
    interpretation,
    engine_version,
):
    pid = f"{base_chart_id}:{year}"
    envelope = json.dumps(envelope) if isinstance(envelope, dict) else envelope
    synthesis = json.dumps(synthesis) if isinstance(synthesis, dict) else synthesis
    interpretation = json.dumps(interpretation) if isinstance(interpretation, dict) else interpretation
    with get_conn() as con:
        con.execute(
        """
        INSERT INTO yearly_predictions
        (id, base_chart_id, year, status, envelope, synthesis, interpretation, engine_version, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            base_chart_id = EXCLUDED.base_chart_id,
            year = EXCLUDED.year,
            status = EXCLUDED.status,
            envelope = EXCLUDED.envelope,
            synthesis = EXCLUDED.synthesis,
            interpretation = EXCLUDED.interpretation,
            engine_version = EXCLUDED.engine_version,
            created_at = EXCLUDED.created_at
        """,
        [
            pid,
            base_chart_id,
            year,
            status,
            envelope,
            synthesis,
            interpretation,
            engine_version,
            datetime.utcnow(),
        ],
    )
