from datetime import datetime
from app.db.duckdb import get_conn


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
    con = get_conn()
    pid = f"{base_chart_id}:{year}"

    con.execute(
        """
        INSERT OR REPLACE INTO yearly_predictions
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
