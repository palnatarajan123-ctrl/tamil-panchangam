"""
Smoke test for family chat — validates the entire code path
WITHOUT hitting the LLM or Render. Run locally.

Usage:
    cd tamil_panchangam_engine
    python ../smoke_test_family_chat.py
"""
import sys, json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# ── 1. resolve_antar_dasha signature ────────────────────────────────────────
print("1. Testing resolve_antar_dasha accepts datetime with timezone...")
try:
    from app.engines.dasha_resolver import resolve_antar_dasha
    # Build a minimal vimshottari stub
    now = datetime.now(timezone.utc)
    stub_vimshottari = {
        "timeline": [
            {
                "lord": "Saturn",
                "start": "2020-01-01T00:00:00+00:00",
                "end": "2039-01-01T00:00:00+00:00",
                "antardashas": [
                    {
                        "lord": "Mercury",
                        "start": "2024-01-01T00:00:00+00:00",
                        "end": "2027-01-01T00:00:00+00:00"
                    }
                ]
            }
        ]
    }
    result = resolve_antar_dasha(vimshottari=stub_vimshottari, reference_date=now)
    print(f"   ✅ resolve_antar_dasha OK → maha={result.get('maha',{}).get('lord')} antar={result.get('antar',{}).get('lord')}")
except Exception as e:
    print(f"   ❌ resolve_antar_dasha FAILED: {e}")

# ── 2. compute_sade_sati accepts full chart dict ─────────────────────────────
print("2. Testing compute_sade_sati accepts full chart dict...")
try:
    from app.engines.sade_sati_engine import compute_sade_sati
    stub_chart = {
        "ephemeris": {
            "moon": {"longitude": 45.0, "rasi": "Rishabam", "nakshatra": {"name": "Krittika"}},
            "saturn": {"longitude": 15.0}
        },
        "birth_details": {"name": "Test"}
    }
    ss = compute_sade_sati(stub_chart)
    print(f"   ✅ compute_sade_sati OK → active={ss.get('sade_sati',{}).get('active')}")
except Exception as e:
    print(f"   ❌ compute_sade_sati FAILED: {e}")

# ── 3. DB query shape — base_charts has payload ──────────────────────────────
print("3. Testing DB query uses base_charts.payload (not user_charts)...")
try:
    from app.db.postgres import get_conn
    with get_conn() as conn:
        row = conn.execute("""
            SELECT bc.payload
            FROM base_charts bc
            LIMIT 1
        """, ()).fetchone()
        print(f"   ✅ base_charts.payload accessible → {'has data' if row and row[0] else 'empty table (OK)'}")
except Exception as e:
    print(f"   ❌ base_charts.payload query FAILED: {e}")

# ── 4. family_members query with %s placeholder ──────────────────────────────
print("4. Testing family_members JOIN base_charts with %s placeholder...")
try:
    from app.db.postgres import get_conn
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT fm.role, fm.display_name, fm.chart_id, bc.payload
            FROM family_members fm
            JOIN base_charts bc ON bc.id = fm.chart_id
            WHERE fm.group_id = %s
            ORDER BY fm.role
        """, ("nonexistent-group-id",)).fetchall()
        print(f"   ✅ family_members JOIN query OK → {len(rows)} rows (0 expected for dummy ID)")
except Exception as e:
    print(f"   ❌ family_members JOIN query FAILED: {e}")

# ── 5. Full member_lines construction ────────────────────────────────────────
print("5. Testing member_lines construction from payload...")
try:
    stub_payload = {
        "birth_details": {"name": "Test User"},
        "ephemeris": {
            "moon": {"rasi": "Mesham", "nakshatra": {"name": "Ashwini"}}
        },
        "dashas": {
            "vimshottari": stub_vimshottari
        }
    }
    payload = stub_payload
    birth = payload.get("birth_details", {})
    moon = payload.get("ephemeris", {}).get("moon", {})
    vimshottari = payload.get("dashas", {}).get("vimshottari", {})
    dasha = resolve_antar_dasha(vimshottari=vimshottari, reference_date=datetime.now(timezone.utc))
    ss = compute_sade_sati(payload)
    ss_data = ss.get("sade_sati", {}) if ss else {}
    name = birth.get("name", "role")
    nak = moon.get("nakshatra", {})
    nak_name = nak.get("name", "") if isinstance(nak, dict) else nak
    rasi = moon.get("rasi", "")
    maha = dasha.get("maha", {}).get("lord", "—") if dasha else "—"
    antar = dasha.get("antar", {}).get("lord", "—") if dasha else "—"
    ss_active = ss_data.get("active", False)
    ss_phase = ss_data.get("phase", "")
    line = (
        f"HUSBAND — {name}: "
        f"Nakshatra {nak_name}, Rasi {rasi}, "
        f"Dasha {maha}›{antar}, "
        f"Sade Sati: {'Active (' + ss_phase + ')' if ss_active else 'None'}"
    )
    print(f"   ✅ member_lines OK → {line}")
except Exception as e:
    print(f"   ❌ member_lines construction FAILED: {e}")

print("\nDone. Fix any ❌ before deploying.")