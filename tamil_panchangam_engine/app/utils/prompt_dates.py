"""
Unambiguous date rendering for text that reaches an LLM prompt.

Found 2026-10-02: with ISO dates the chat model restated "2029-05-22" as
"29 May 2029" in 2/3 live runs (the year's "29" bleeding into the day).
Digit-dash-digit forms are transposable; "22 May 2029" / "May 2029" are
not. Every date that reaches a chat system prompt goes through here.

  fmt_date("2029-05-22")   -> "22 May 2029"
  fmt_month("2026-12")     -> "Dec 2026"
  humanize_iso_dates(text) -> rewrites every ISO date / datetime /
                              year-month left in already-assembled text
"""
import re
from datetime import date, datetime
from typing import Union

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# YYYY-MM-DD, optionally followed by a time part (T or space) and offset.
_ISO_DATE_RE = re.compile(
    r"(?<![\d-])(\d{4})-(\d{2})-(\d{2})"
    r"(?:[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?"
    r"(?![\d-])"
)
# YYYY-MM on its own (not part of a full date, not a year range like 2028-2031).
_ISO_MONTH_RE = re.compile(r"(?<![\d-])(\d{4})-(\d{2})(?![\d-])")


def fmt_date(value: Union[str, date, datetime, None]) -> str:
    """'2029-05-22' / date / datetime -> '22 May 2029'. Unparseable -> as-is."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value.day} {_MONTHS[value.month - 1]} {value.year}"
    m = _ISO_DATE_RE.search(str(value))
    if not m:
        return str(value)
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return str(value)
    return f"{d} {_MONTHS[mo - 1]} {y}"


def fmt_month(value: Union[str, date, datetime, None]) -> str:
    """'2026-12' / '2026-12-05' / date -> 'Dec 2026'."""
    if value is None or value == "":
        return ""
    if isinstance(value, (date, datetime)):
        return f"{_MONTHS[value.month - 1]} {value.year}"
    m = re.match(r"(\d{4})-(\d{2})", str(value))
    if not m or not 1 <= int(m.group(2)) <= 12:
        return str(value)
    return f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)}"


def fmt_dasha_windows(windows) -> str:
    """[{'from','to','level','lord'}, ...] (children/marriage/health/wealth
    engines) -> 'Venus antardasha 1 Jan 2032 to 3 Apr 2033; ...'. Replaces
    printing the raw list of dicts (ISO strings) into the prompt."""
    if not windows:
        return "none in range"
    return "; ".join(
        f"{w.get('lord', '?')} {w.get('level', 'period')} {fmt_date(w.get('from'))} to {fmt_date(w.get('to'))}"
        for w in windows
    )


def _sub_date(m: "re.Match") -> str:
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return m.group(0)
    out = f"{d} {_MONTHS[mo - 1]} {y}"
    hhmm, tz = m.group(4), m.group(5)
    if hhmm and hhmm != "00:00":  # midnight is a date-only placeholder
        out += f" {hhmm}" + (" UTC" if tz in ("Z", "+00:00", "+0000") else (f" {tz}" if tz else ""))
    return out


def _sub_month(m: "re.Match") -> str:
    mo = int(m.group(2))
    if not 1 <= mo <= 12:
        return m.group(0)
    return f"{_MONTHS[mo - 1]} {m.group(1)}"


def humanize_iso_dates(text: str) -> str:
    """Rewrite every ISO date (with or without a time part) and bare
    YYYY-MM in `text`. Safety net applied to each chat's final system
    prompt, so a section added later can't reintroduce the misread."""
    if not text:
        return text
    return _ISO_MONTH_RE.sub(_sub_month, _ISO_DATE_RE.sub(_sub_date, text))


def contains_iso_date(text: str) -> bool:
    """True if humanize_iso_dates() would rewrite anything in `text`."""
    return humanize_iso_dates(text or "") != (text or "")
