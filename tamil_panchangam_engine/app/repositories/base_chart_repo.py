# app/repositories/base_chart_repo.py

import json


def user_owns_chart(conn, user: dict, chart_id: str) -> bool:
    """
    Ownership check for a base_chart (security fix, 2026-09-08).

    Admins always pass (matches the existing role-check convention used
    throughout base_chart.py, family.py, prospects.py). Everyone else must
    have a user_charts row linking them to chart_id -- same join-table
    pattern already used by list_base_charts()'s owner filter.

    Single canonical implementation, used by every chart_id/base_chart_id-
    scoped endpoint, so the query can't drift between call sites the way
    this project's duplicated-implementation bugs have before (see
    family.py/chat.py's two chat implementations, and payload_builder.py's
    two family-Porutham-cache implementations, both found earlier this
    project). Callers should raise a 404 (not 403) on a False result, to
    avoid confirming the chart exists at all to a non-owner.
    """
    if user.get("role") == "admin":
        return True
    row = conn.execute(
        "SELECT id FROM user_charts WHERE user_id = ? AND base_chart_id = ?",
        [user["id"], chart_id],
    ).fetchone()
    return row is not None


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
