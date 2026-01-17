"""
Time and timezone utilities for astronomical calculations
"""

from datetime import datetime, timezone
import pytz
from timezonefinder import TimezoneFinder

tf = TimezoneFinder()

def get_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """Get timezone string from lat/long coordinates"""
    tz_name = tf.timezone_at(lat=latitude, lng=longitude)
    return tz_name if tz_name else "UTC"

def to_julian_day(dt: datetime) -> float:
    """Convert datetime to Julian Day Number"""
    year = dt.year
    month = dt.month
    day = dt.day + (dt.hour + dt.minute/60 + dt.second/3600) / 24
    
    if month <= 2:
        year -= 1
        month += 12
    
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    return jd

def from_julian_day(jd: float) -> datetime:
    """Convert Julian Day Number to datetime"""
    Z = int(jd + 0.5)
    F = jd + 0.5 - Z
    
    if Z < 2299161:
        A = Z
    else:
        alpha = int((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - int(alpha / 4)
    
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    
    day = B - D - int(30.6001 * E)
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    
    hours = F * 24
    hour = int(hours)
    minutes = (hours - hour) * 60
    minute = int(minutes)
    second = int((minutes - minute) * 60)
    
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

def local_to_utc(local_dt: datetime, timezone_str: str) -> datetime:
    """Convert local datetime to UTC"""
    tz = pytz.timezone(timezone_str)
    local_aware = tz.localize(local_dt)
    return local_aware.astimezone(pytz.UTC)

def utc_to_local(utc_dt: datetime, timezone_str: str) -> datetime:
    """Convert UTC datetime to local"""
    tz = pytz.timezone(timezone_str)
    return utc_dt.astimezone(tz)


def normalize_birth_time_to_utc(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone_str: str | None = None
) -> datetime:
    """
    Canonical entry point for birth-time normalization.

    Rules:
    - Accept HH:MM or HH:MM:SS
    - If timezone_str is provided, use it
    - Else derive timezone from lat/long
    - Return UTC-aware datetime
    """

    if not timezone_str:
        timezone_str = get_timezone_from_coordinates(latitude, longitude)

    # 🔑 EPIC-5 FIX: tolerate seconds
    time_format = "%H:%M:%S" if birth_time.count(":") == 2 else "%H:%M"

    local_dt = datetime.strptime(
        f"{birth_date} {birth_time}",
        f"%Y-%m-%d {time_format}"
    )

    return local_to_utc(local_dt, timezone_str)

def get_month_reference_date_utc(year: int, month: int) -> datetime:
    """
    Use mid-month UTC reference to avoid edge effects.
    """
    return datetime(year, month, 15, 12, 0, 0, tzinfo=timezone.utc)

