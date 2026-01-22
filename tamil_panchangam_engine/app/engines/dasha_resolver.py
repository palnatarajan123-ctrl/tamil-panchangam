from datetime import datetime
from typing import Optional, Dict, Any


def _parse(dt: Any) -> datetime:
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

    raise TypeError(f"Unsupported datetime type: {type(dt).__name__}")


def resolve_antar_dasha(
    *,
    vimshottari: dict,
    reference_date: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Resolve the active Antar Dasha for a given reference date.

    EXPECTED vimshottari schema (LOCKED):
    {
        "timeline": [
            {
                "mahadasha": str,
                "start": ISO str,
                "end": ISO str,
                "antar_dashas": [
                    {
                        "antar_lord": str,
                        "start": ISO str,
                        "end": ISO str
                    }
                ]
            }
        ]
    }

    RETURNS (if active):
    {
        "maha": {
            "lord": str,
            "start": ISO str,
            "end": ISO str,
            "is_partial": bool
        },
        "antar": {
            "lord": str,
            "start": ISO str,
            "end": ISO str,
            "confidence_weight": float
        }
    }
    """

    reference_date = _parse(reference_date)

    periods = vimshottari.get("timeline", [])
    if not periods:
        return None

    for maha in periods:
        maha_start = _parse(maha.get("start"))
        maha_end = _parse(maha.get("end"))

        if not (maha_start <= reference_date < maha_end):
            continue

        antar_list = maha.get("antar_dashas", [])
        if not antar_list:
            return None

        for antar in antar_list:
            antar_start = _parse(antar.get("start"))
            antar_end = _parse(antar.get("end"))

            if antar_start <= reference_date < antar_end:
                duration = (antar_end - antar_start).total_seconds()
                elapsed = (reference_date - antar_start).total_seconds()

                # Confidence peaks mid-period, tapers toward edges
                progress = elapsed / duration if duration > 0 else 0.5
                confidence_weight = round(
                    1.0 - abs(0.5 - progress),
                    2,
                )

                return {
                    "maha": {
                        "lord": maha.get("mahadasha"),
                        "start": maha.get("start"),
                        "end": maha.get("end"),
                        "is_partial": maha.get("is_partial", False),
                    },
                    "antar": {
                        "lord": antar.get("antar_lord"),
                        "start": antar.get("start"),
                        "end": antar.get("end"),
                        "confidence_weight": confidence_weight,
                    },
                }

    return None
