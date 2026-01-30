"""
Chart SVG Models

Data structures for chart rendering.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChartSvgInput:
    """Input data for SVG chart rendering."""
    chart_type: str                      # "D1" or "D9"
    planet_signs: Dict[str, List[str]]   # {"Aries": ["Sun", "Moon"], ...}
    title: str
    dignity: Optional[Dict[str, str]] = None
