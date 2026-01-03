"""
This module will compute Vimshottari Dasha:
- Mahadasha (major period)
- Antardasha (sub-period)
- Pratyantar Dasha (sub-sub-period)

Based on Moon's Nakshatra at birth.

DO NOT implement logic yet.
"""

DASHA_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17
}

NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
]

def get_birth_dasha(moon_nakshatra: int, nakshatra_pada: int, birth_datetime) -> dict:
    """Calculate birth dasha from Moon's position"""
    pass

def compute_mahadasha_periods(start_dasha: str, birth_datetime) -> list:
    """Compute all Mahadasha periods for lifetime"""
    pass

def compute_antardasha(mahadasha_lord: str, start_date, end_date) -> list:
    """Compute Antardasha within a Mahadasha"""
    pass

def get_current_dasha(birth_datetime, current_datetime) -> dict:
    """Get current running Mahadasha/Antardasha/Pratyantar"""
    pass
