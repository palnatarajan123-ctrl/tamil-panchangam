# tests/api/test_prospects.py
"""
Phase G1: chart-to-chart Porutham prospect links (app/api/prospects.py) --
the schema/data-model foundation G2 (chat), G3 (PDF), and G4 (frontend)
all build on. Live verification against real dev-DB data (real creation,
real cross-account 403, real duplicate 409, real delete+404, and a
byte-identical convert-to-family carryover) already proved this works
today; these mocked unit tests exist so a later refactor of this module
or an adjacent one (G2/G3/G4 touching the same helpers) has regression
protection, matching the rigor applied to every other new function this
session (_get_or_compute_porutham, _build_porutham_chat_block,
_resolve_porutham_for_pdf, _build_porutham()).

Route handlers are called directly as plain functions (user dict passed
positionally instead of through FastAPI's Depends(get_current_user)) --
same pattern this module's sibling test files don't yet use for full
endpoints, but is the natural way to unit test a FastAPI route function
without spinning up TestClient/dependency overrides.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.prospects import (
    CreateProspectRequest,
    _can_access_chart,
    _resolve_boy_girl_ids,
    _get_or_compute_prospect_porutham,
    create_prospect,
    list_prospects_for_chart,
    get_prospect_porutham,
    delete_prospect,
    convert_prospect_to_family,
)


def _seq_conn(*fetchone_values):
    """A mock DB connection whose successive .execute(...) calls each
    return a fresh mock yielding the next value in `fetchone_values` from
    .fetchone(). One value must be supplied per execute() call the code
    under test will make, in order -- including INSERT/UPDATE/DELETE
    calls whose fetchone() is never actually invoked (any placeholder,
    e.g. None, works for those slots)."""
    conn = MagicMock()
    mocks = []
    for v in fetchone_values:
        m = MagicMock()
        m.fetchone.return_value = v
        mocks.append(m)
    conn.execute.side_effect = mocks
    return conn


def _cm(conn):
    cm = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = False
    return cm


USER = {"id": "u1", "role": "user"}
OTHER_USER = {"id": "other-user", "role": "user"}
ADMIN = {"id": "admin1", "role": "admin"}


class TestResolveBoyGirlIds(unittest.TestCase):
    def test_source_is_boy(self):
        self.assertEqual(_resolve_boy_girl_ids("c1", "c2", "boy"), ("c1", "c2"))

    def test_source_is_girl(self):
        self.assertEqual(_resolve_boy_girl_ids("c1", "c2", "girl"), ("c2", "c1"))


class TestCanAccessChart(unittest.TestCase):
    """Ownership matrix: owned / not-owned / admin."""

    def test_admin_bypasses_without_db_call(self):
        conn = MagicMock()
        self.assertTrue(_can_access_chart(conn, "c1", ADMIN))
        conn.execute.assert_not_called()

    def test_owner_true(self):
        conn = _seq_conn(("row-id",))
        self.assertTrue(_can_access_chart(conn, "c1", USER))

    def test_non_owner_false(self):
        conn = _seq_conn(None)
        self.assertFalse(_can_access_chart(conn, "c1", USER))


class TestGetOrComputeProspectPorutham(unittest.TestCase):
    """Direct tests for the cache-first helper, mirroring
    payload_builder._get_or_compute_porutham()'s test structure."""

    def test_cache_hit_returns_stored_result_no_db_call(self):
        stored = {
            "boy": {"chart_id": "c1", "name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"},
            "girl": {"chart_id": "c2", "name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"},
            "porutham": {"total_score": 16, "max_score": 33, "grade": "Average", "points": []},
        }
        conn = MagicMock()
        result = _get_or_compute_prospect_porutham(conn, ("p1", "c1", "c2", "boy", stored))
        self.assertEqual(result, stored)
        conn.execute.assert_not_called()

    def test_cache_miss_computes_and_writes_full_shape(self):
        boy_payload = {
            "birth_details": {"name": "Ravi"},
            "ephemeris": {"moon": {"nakshatra": {"name": "Ashwini"}, "rasi": "Mesham"}},
        }
        girl_payload = {
            "birth_details": {"name": "Priya"},
            "ephemeris": {"moon": {"nakshatra": {"name": "Hasta"}, "rasi": "Kanni"}},
        }
        # 2 chart fetches (boy, girl) + 1 write-back UPDATE
        conn = _seq_conn(("c1", boy_payload, False), ("c2", girl_payload, False), None)

        result = _get_or_compute_prospect_porutham(conn, ("p1", "c1", "c2", "boy", None))

        self.assertIsNotNone(result)
        self.assertEqual(result["boy"], {"chart_id": "c1", "name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"})
        self.assertEqual(result["girl"], {"chart_id": "c2", "name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"})
        self.assertIn("total_score", result["porutham"])

        update_sql, update_params = conn.execute.call_args_list[2].args
        self.assertIn("UPDATE porutham_prospects", update_sql)
        written = json.loads(update_params[0])
        self.assertEqual(written["boy"]["nakshatra"], "Ashwini")
        self.assertEqual(written["girl"]["nakshatra"], "Hasta")

    def test_source_role_girl_swaps_boy_girl_assignment(self):
        """source_chart_id is the 'girl' input when source_role='girl' --
        the direction-sensitive categories depend on getting this right."""
        source_payload = {
            "birth_details": {"name": "Priya"},
            "ephemeris": {"moon": {"nakshatra": {"name": "Hasta"}, "rasi": "Kanni"}},
        }
        candidate_payload = {
            "birth_details": {"name": "Ravi"},
            "ephemeris": {"moon": {"nakshatra": {"name": "Ashwini"}, "rasi": "Mesham"}},
        }
        # boy_id resolves to candidate ("c2") first, girl_id to source ("c1")
        conn = _seq_conn(("c2", candidate_payload, False), ("c1", source_payload, False), None)

        result = _get_or_compute_prospect_porutham(conn, ("p1", "c1", "c2", "girl", None))

        self.assertEqual(result["boy"]["chart_id"], "c2")
        self.assertEqual(result["boy"]["name"], "Ravi")
        self.assertEqual(result["girl"]["chart_id"], "c1")
        self.assertEqual(result["girl"]["name"], "Priya")

    def test_missing_nak_rasi_returns_none_no_write(self):
        boy_payload = {"birth_details": {"name": "Ravi"}, "ephemeris": {}}
        girl_payload = {
            "birth_details": {"name": "Priya"},
            "ephemeris": {"moon": {"nakshatra": {"name": "Hasta"}, "rasi": "Kanni"}},
        }
        conn = _seq_conn(("c1", boy_payload, False), ("c2", girl_payload, False))
        result = _get_or_compute_prospect_porutham(conn, ("p1", "c1", "c2", "boy", None))
        self.assertIsNone(result)
        self.assertEqual(conn.execute.call_count, 2)  # no write attempted

    def test_chart_not_found_returns_none(self):
        conn = _seq_conn(None, ("c2", {}, False))
        result = _get_or_compute_prospect_porutham(conn, ("p1", "c1", "c2", "boy", None))
        self.assertIsNone(result)


class TestCreateProspect(unittest.TestCase):
    def _req(self, source="c1", candidate="c2", role="boy"):
        return CreateProspectRequest(source_chart_id=source, candidate_chart_id=candidate, source_role=role)

    def test_self_pair_rejected_no_db_call(self):
        with patch("app.api.prospects.get_conn") as mock_get_conn:
            with self.assertRaises(HTTPException) as ctx:
                create_prospect(self._req(source="c1", candidate="c1"), USER)
        self.assertEqual(ctx.exception.status_code, 400)
        mock_get_conn.assert_not_called()

    def test_invalid_source_role_rejected_no_db_call(self):
        with patch("app.api.prospects.get_conn") as mock_get_conn:
            with self.assertRaises(HTTPException) as ctx:
                create_prospect(self._req(role="other"), USER)
        self.assertEqual(ctx.exception.status_code, 400)
        mock_get_conn.assert_not_called()

    def test_source_chart_not_owned_rejected(self):
        conn = _seq_conn(None)  # source ownership check fails
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                create_prospect(self._req(), USER)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Source chart", ctx.exception.detail)
        self.assertEqual(conn.execute.call_count, 1)

    def test_candidate_chart_not_owned_rejected(self):
        conn = _seq_conn(("row",), None)  # source owned, candidate not
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                create_prospect(self._req(), USER)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Candidate chart", ctx.exception.detail)
        self.assertEqual(conn.execute.call_count, 2)

    def test_duplicate_link_rejected(self):
        conn = _seq_conn(("row",), ("row",), ("existing-id",))
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                create_prospect(self._req(), USER)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(conn.execute.call_count, 3)

    def test_admin_bypasses_ownership_checks(self):
        # No ownership-check execute() calls for admin -- only the
        # duplicate check and the INSERT.
        conn = _seq_conn(None, None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            result = create_prospect(self._req(), ADMIN)
        self.assertEqual(result["source_chart_id"], "c1")
        self.assertEqual(conn.execute.call_count, 2)

    def test_happy_path_creates_and_returns_link(self):
        conn = _seq_conn(("row",), ("row",), None, None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            result = create_prospect(self._req(role="girl"), USER)
        self.assertEqual(result["source_chart_id"], "c1")
        self.assertEqual(result["candidate_chart_id"], "c2")
        self.assertEqual(result["source_role"], "girl")
        self.assertIn("id", result)

        insert_sql, insert_params = conn.execute.call_args_list[3].args
        self.assertIn("INSERT INTO porutham_prospects", insert_sql)
        self.assertEqual(insert_params[1:], ["u1", "c1", "c2", "girl"])


class TestListProspectsForChart(unittest.TestCase):
    def test_not_owned_rejected(self):
        conn = _seq_conn(None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                list_prospects_for_chart("c1", USER)
        self.assertEqual(ctx.exception.status_code, 403)


class TestGetProspectPorutham(unittest.TestCase):
    def test_not_found(self):
        conn = _seq_conn(None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                get_prospect_porutham("p1", USER)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_not_owned_rejected(self):
        row = ("p1", "other-user", "c1", "c2", "boy", None)
        conn = _seq_conn(row)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                get_prospect_porutham("p1", USER)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_owner_cache_hit_returns_result(self):
        stored = {"boy": {"name": "Ravi"}, "girl": {"name": "Priya"}, "porutham": {"total_score": 16}}
        row = ("p1", "u1", "c1", "c2", "boy", stored)
        conn = _seq_conn(row)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            result = get_prospect_porutham("p1", USER)
        self.assertEqual(result, stored)

    def test_admin_can_read_another_users_prospect(self):
        stored = {"boy": {"name": "Ravi"}, "girl": {"name": "Priya"}, "porutham": {"total_score": 16}}
        row = ("p1", "other-user", "c1", "c2", "boy", stored)
        conn = _seq_conn(row)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            result = get_prospect_porutham("p1", ADMIN)
        self.assertEqual(result, stored)


class TestDeleteProspect(unittest.TestCase):
    def test_not_found(self):
        conn = _seq_conn(None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                delete_prospect("p1", USER)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_not_owned_rejected_no_delete_executed(self):
        conn = _seq_conn(("other-user",))
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                delete_prospect("p1", USER)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(conn.execute.call_count, 1)  # no DELETE ran

    def test_admin_can_delete_another_users_prospect(self):
        conn = _seq_conn(("other-user",), None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            delete_prospect("p1", ADMIN)
        delete_sql, delete_params = conn.execute.call_args_list[1].args
        self.assertIn("DELETE FROM porutham_prospects", delete_sql)
        self.assertEqual(delete_params, ["p1"])

    def test_owner_delete_executes_delete_statement(self):
        conn = _seq_conn(("u1",), None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            delete_prospect("p1", USER)
        delete_sql, delete_params = conn.execute.call_args_list[1].args
        self.assertIn("DELETE FROM porutham_prospects", delete_sql)
        self.assertEqual(delete_params, ["p1"])

    def test_delete_then_read_returns_404(self):
        """Delete + 404-after: delete_prospect() removes the row, and a
        subsequent get_prospect_porutham() call for the same id -- now
        finding no matching row, as a real second SELECT would after a
        real DELETE -- must 404, not resurrect stale data."""
        delete_select_row = ("u1",)  # delete_prospect's SELECT returns just user_id
        conn = _seq_conn(delete_select_row, None, None)  # delete's SELECT, DELETE, then get's SELECT -> gone
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            delete_prospect("p1", USER)
            with self.assertRaises(HTTPException) as ctx:
                get_prospect_porutham("p1", USER)
        self.assertEqual(ctx.exception.status_code, 404)


class TestConvertProspectToFamily(unittest.TestCase):
    def _cached_row(self, owner="u1"):
        stored = {
            "boy": {"chart_id": "c1", "name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"},
            "girl": {"chart_id": "c2", "name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"},
            "porutham": {
                "total_score": 16, "max_score": 33, "percent": 48.5, "grade": "Average",
                "mandatory_fail": False,
                "points": [{"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True}],
            },
        }
        return ("p1", owner, "c1", "c2", "boy", stored), stored

    def test_not_found(self):
        conn = _seq_conn(None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                convert_prospect_to_family("p1", USER)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_not_owned_rejected_no_group_created(self):
        row, _ = self._cached_row(owner="other-user")
        conn = _seq_conn(row)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            with self.assertRaises(HTTPException) as ctx:
                convert_prospect_to_family("p1", USER)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(conn.execute.call_count, 1)  # nothing else ran

    def test_byte_identical_porutham_carried_into_family_cache(self):
        """The core Phase G1 guarantee: convert-to-family must not
        recompute -- the porutham sub-dict written into
        family_porutham_cache must be byte-identical to what the prospect
        already had cached."""
        row, stored = self._cached_row()
        # SELECT prospect, INSERT group, INSERT husband member,
        # INSERT wife member, INSERT family_porutham_cache
        conn = _seq_conn(row, None, None, None, None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            result = convert_prospect_to_family("p1", USER)

        self.assertEqual(result["name"], "Ravi & Priya")
        self.assertEqual(result["member_count"], 2)
        self.assertEqual(conn.execute.call_count, 5)

        cache_sql, cache_params = conn.execute.call_args_list[4].args
        self.assertIn("INSERT INTO family_porutham_cache", cache_sql)
        written = json.loads(cache_params[3])
        self.assertEqual(written["porutham"], stored["porutham"])
        self.assertEqual(written["husband"], {"name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"})
        self.assertEqual(written["wife"], {"name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"})

        # husband/wife role mapping: boy -> husband, girl -> wife
        husband_sql, husband_params = conn.execute.call_args_list[2].args
        self.assertIn("'husband'", husband_sql)
        self.assertEqual(husband_params[2], "c1")  # boy's chart_id
        wife_sql, wife_params = conn.execute.call_args_list[3].args
        self.assertIn("'wife'", wife_sql)
        self.assertEqual(wife_params[2], "c2")  # girl's chart_id

    def test_admin_convert_creates_group_under_prospect_owner_not_admin(self):
        row, _ = self._cached_row(owner="other-user")
        conn = _seq_conn(row, None, None, None, None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            convert_prospect_to_family("p1", ADMIN)

        group_sql, group_params = conn.execute.call_args_list[1].args
        self.assertIn("INSERT INTO family_groups", group_sql)
        self.assertEqual(group_params[1], "other-user")  # not "admin1"

    def test_prospect_link_untouched_no_delete_or_update_of_prospect_row(self):
        row, _ = self._cached_row()
        conn = _seq_conn(row, None, None, None, None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            convert_prospect_to_family("p1", USER)
        for call in conn.execute.call_args_list:
            sql = call.args[0]
            self.assertNotIn("DELETE FROM porutham_prospects", sql)
            self.assertNotIn("UPDATE porutham_prospects", sql)


if __name__ == "__main__":
    unittest.main()
