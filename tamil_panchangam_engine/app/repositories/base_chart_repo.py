# app/repositories/base_chart_repo.py

import json

def get_base_chart_by_id(conn, chart_id: str):
    row = conn.execute(
        """
        SELECT id, payload, locked
        FROM base_charts
        WHERE id = ?
        """,
        [chart_id],
    ).fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "payload": row[1],
        "locked": row[2],
    }


def insert_base_chart(conn, *, chart_id: str, payload: dict, locked: bool):
    conn.execute(
        """
        INSERT INTO base_charts (id, payload, locked)
        VALUES (?, ?, ?)
        """,
        [
            chart_id,
            json.dumps(payload),
            locked,
        ],
    )
