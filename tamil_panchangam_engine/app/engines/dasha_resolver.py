from datetime import datetime
from typing import Optional


def _parse(dt) -> datetime:
    """
    Parse ISO datetime safely using stdlib only.
    Handles trailing 'Z' for UTC.
    """
    if isinstance(dt, datetime):
        return dt

    if isinstance(dt, str):
        if dt.endswith("Z"):
            dt = dt.replace("Z", "+00:00")
        return datetime.fromisoformat(dt)

    raise TypeError(f"Unsupported datetime type: {type(dt)}")


def resolve_antar_dasha(
    *,
    vimshottari: dict,
    reference_date: datetime,
) -> Optional[dict]:
    """
    EPIC-6 + EPIC-6.2
    Resolve the active Antar Dasha for a given reference date.

    Returns:
        {
            "maha_lord": str,
            "antar_lord": str,
            "start": ISO str,
            "end": ISO str,
            "confidence_weight": float (0–1)
        }
        or None if not found
    """

    reference_date = _parse(reference_date)

    periods = vimshottari.get("periods", [])
    if not periods:
        return None

    for maha in periods:
        maha_start = _parse(maha["start"])
        maha_end = _parse(maha["end"])

        if not (maha_start <= reference_date < maha_end):
            continue

        for antar in maha.get("antar_dashas", []):
            antar_start = _parse(antar["start"])
            antar_end = _parse(antar["end"])

            if antar_start <= reference_date < antar_end:
                # Simple proportional weighting (can evolve later)
                duration = (antar_end - antar_start).total_seconds()
                elapsed = (reference_date - antar_start).total_seconds()
                progress = elapsed / duration if duration > 0 else 0.5

                # Mid-period = higher confidence
                confidence_weight = round(1.0 - abs(0.5 - progress), 2)

                return {
                    "maha_lord": maha["maha_lord"],
                    "antar_lord": antar["antar_lord"],
                    "start": antar["start"],
                    "end": antar["end"],
                    "confidence_weight": confidence_weight,
                }

    return None
