"""
Pratyantar Dasha Engine — Vimshottari sub-sub periods (3rd and 4th tier).

Computes Pratyantar Dasha (sub-sub period) and Sookshma Dasha (sub-sub-sub period)
for a given date, using the existing Vimshottari Mahadasha/Antardasha timeline.
"""

import logging
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple
from app.utils.prompt_dates import fmt_date

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


def compute_dasha_snapshot(
    vimshottari: Dict[str, Any],
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Live current + next Mahadasha/Antardasha/Pratyantar periods, with dates,
    resolved from the natal Vimshottari timeline for reference_date (default
    today UTC). Pure date arithmetic -- for chat, which must not read the
    month-scoped predictive_signals cache or the creation-time
    vimshottari["current"] field (both go stale).

    Returns {} if the date isn't covered by the timeline. Each period is a
    _period_dict(); "next_*" entries may cross into the next Mahadasha.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()
    ref_dt = datetime(reference_date.year, reference_date.month, reference_date.day, tzinfo=timezone.utc)

    # Flatten every Antardasha in order, tagged with its Mahadasha.
    ads: List[Tuple[str, str, datetime, datetime, datetime, datetime]] = []
    for md in vimshottari.get("timeline") or vimshottari.get("periods", []):
        try:
            md_s, md_e = _parse_dt(md["start"]), _parse_dt(md["end"])
        except Exception:
            continue
        for ad in md.get("antar_dashas", []):
            try:
                ads.append((md["mahadasha"], ad["antar_lord"], md_s, md_e,
                            _parse_dt(ad["start"]), _parse_dt(ad["end"])))
            except Exception:
                continue

    idx = next((i for i, a in enumerate(ads) if a[4] <= ref_dt < a[5]), None)
    if idx is None:
        return {}

    md_lord, ad_lord, md_s, md_e, ad_s, ad_e = ads[idx]
    pts = _compute_subperiods(ad_s, ad_e, ad_lord)
    pt_i = next(i for i, (_, s, e) in enumerate(pts) if s <= ref_dt < e)

    snapshot: Dict[str, Any] = {
        "mahadasha": _period_dict(md_lord, md_s, md_e),
        "antardasha": _period_dict(ad_lord, ad_s, ad_e),
        "pratyantar": _period_dict(*pts[pt_i]),
        "next_antardasha": None,
        "next_pratyantar": None,
        "next_mahadasha": None,
    }

    nxt = ads[idx + 1] if idx + 1 < len(ads) else None
    if nxt:
        snapshot["next_antardasha"] = _period_dict(nxt[1], nxt[4], nxt[5])

    if pt_i + 1 < len(pts):
        snapshot["next_pratyantar"] = _period_dict(*pts[pt_i + 1])
    elif nxt:
        # First Pratyantar of the next Antardasha starts with that AD's own lord.
        snapshot["next_pratyantar"] = _period_dict(*_compute_subperiods(nxt[4], nxt[5], nxt[1])[0])

    later_md = next((a for a in ads[idx + 1:] if a[0] != md_lord), None)
    if later_md:
        snapshot["next_mahadasha"] = _period_dict(later_md[0], later_md[2], later_md[3])

    return snapshot


def _ym(iso_date: str) -> str:
    return datetime.fromisoformat(iso_date).strftime("%b %Y")


def format_dasha_snapshot_context(snap: Dict[str, Any]) -> str:
    """Verbose multi-line rendering for chat.py's system prompt."""
    if not snap:
        return ""
    lines = []
    for key, label in (
        ("mahadasha", "Current Mahadasha (major period)"),
        ("antardasha", "Current Antardasha (sub-period)"),
        ("pratyantar", "Current Pratyantar (sub-sub-period)"),
        ("next_pratyantar", "Next Pratyantar"),
        ("next_antardasha", "Next Antardasha"),
        ("next_mahadasha", "Next Mahadasha"),
    ):
        p = snap.get(key)
        if p:
            lines.append(f"- {label}: {p['lord']}, {fmt_date(p['start'])} to {fmt_date(p['end'])}")
    return "\n".join(lines)


def format_dasha_snapshot_compact(snap: Dict[str, Any]) -> str:
    """One-clause rendering for family.py's per-member line."""
    if not snap:
        return ""
    # Every period named with an explicit "Mon YYYY–Mon YYYY" range: terser
    # "then X to Y" phrasing was misread by the model as X STARTING at Y,
    # and omitting the next Pratyantar led it to invent one.
    md, ad, pt = snap["mahadasha"], snap["antardasha"], snap["pratyantar"]
    parts = [f"{ad['lord']} sub-period {_ym(ad['start'])}–{_ym(ad['end'])}"]
    nad = snap.get("next_antardasha")
    if nad:
        parts.append(f"next sub-period {nad['lord']} {_ym(nad['start'])}–{_ym(nad['end'])}")
    parts.append(f"{pt['lord']} sub-sub-period {_ym(pt['start'])}–{_ym(pt['end'])}")
    npt = snap.get("next_pratyantar")
    if npt:
        parts.append(f"next sub-sub-period {npt['lord']} {_ym(npt['start'])}–{_ym(npt['end'])}")
    return f"Dasha {md['lord']}›{ad['lord']}›{pt['lord']} ({'; '.join(parts)})"
