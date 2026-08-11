"""
Pratyantar Dasha Engine — Vimshottari sub-sub periods (3rd and 4th tier).

Computes Pratyantar Dasha (sub-sub period) and Sookshma Dasha (sub-sub-sub period)
for a given date, using the existing Vimshottari Mahadasha/Antardasha timeline.
"""

import logging
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Vimshottari planet years (total = 120)
PLANET_YEARS: Dict[str, int] = {
    "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16,
    "Saturn": 19, "Mercury": 17, "Ketu": 7, "Venus": 20,
}
TOTAL_YEARS = 120

DASHA_SEQUENCE = [
    "Sun", "Moon", "Mars", "Rahu", "Jupiter",
    "Saturn", "Mercury", "Ketu", "Venus",
]


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _compute_subperiods(
    start_dt: datetime,
    end_dt: datetime,
    sequence_start: str,
) -> List[Tuple[str, datetime, datetime]]:
    """Divide [start_dt, end_dt] into 9 proportional sub-periods starting from sequence_start."""
    total_secs = (end_dt - start_dt).total_seconds()
    idx = DASHA_SEQUENCE.index(sequence_start)
    seq = DASHA_SEQUENCE[idx:] + DASHA_SEQUENCE[:idx]

    result: List[Tuple[str, datetime, datetime]] = []
    cur = start_dt
    for planet in seq:
        dur_secs = total_secs * PLANET_YEARS[planet] / TOTAL_YEARS
        nxt = cur + timedelta(seconds=dur_secs)
        result.append((planet, cur, nxt))
        cur = nxt
    return result


def _period_dict(lord: str, start: datetime, end: datetime) -> Dict[str, Any]:
    dur = (end - start).total_seconds() / 86400.0
    return {
        "lord": lord,
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "duration_days": round(dur, 1),
    }


def compute_pratyantar(
    vimshottari: Dict[str, Any],
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Compute Pratyantar (sub-sub) and Sookshma (sub-sub-sub) Dasha for reference_date.

    Args:
        vimshottari: payload['dashas']['vimshottari'] dict.
        reference_date: date to evaluate; defaults to today UTC.

    Returns dict with keys md_lord, ad_lord, pratyantar, sookshma.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    ref_dt = datetime(
        reference_date.year, reference_date.month, reference_date.day,
        tzinfo=timezone.utc,
    )

    timeline = vimshottari.get("timeline") or vimshottari.get("periods", [])
    if not timeline:
        logger.warning("No timeline/periods in vimshottari")
        return {}

    md_lord = ad_lord = None
    ad_start = ad_end = None

    for md in timeline:
        try:
            md_s = _parse_dt(md["start"])
            md_e = _parse_dt(md["end"])
        except Exception:
            continue
        if not (md_s <= ref_dt < md_e):
            continue
        md_lord = md["mahadasha"]
        for ad in md.get("antar_dashas", []):
            try:
                ad_s = _parse_dt(ad["start"])
                ad_e = _parse_dt(ad["end"])
            except Exception:
                continue
            if ad_s <= ref_dt < ad_e:
                ad_lord = ad["antar_lord"]
                ad_start, ad_end = ad_s, ad_e
                break
        break

    if not md_lord:
        logger.warning("No Mahadasha found for %s", reference_date)
        return {}

    if not ad_lord or not ad_start:
        return {"md_lord": md_lord, "ad_lord": None, "pratyantar": None, "sookshma": None}

    # Pratyantar within current AD
    pratyantars = _compute_subperiods(ad_start, ad_end, ad_lord)
    pt_lord = pt_start = pt_end = None
    for pl, ps, pe in pratyantars:
        if ps <= ref_dt < pe:
            pt_lord, pt_start, pt_end = pl, ps, pe
            break

    if not pt_lord:
        logger.warning("No Pratyantar found for %s", reference_date)
        return {"md_lord": md_lord, "ad_lord": ad_lord, "pratyantar": None, "sookshma": None}

    # Sookshma within current Pratyantar
    sookshmas = _compute_subperiods(pt_start, pt_end, pt_lord)
    sk_lord = sk_start = sk_end = None
    for pl, ss, se in sookshmas:
        if ss <= ref_dt < se:
            sk_lord, sk_start, sk_end = pl, ss, se
            break

    return {
        "md_lord": md_lord,
        "ad_lord": ad_lord,
        "pratyantar": _period_dict(pt_lord, pt_start, pt_end),
        "sookshma": _period_dict(sk_lord, sk_start, sk_end) if sk_lord else None,
    }
