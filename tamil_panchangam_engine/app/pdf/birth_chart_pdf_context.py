from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class BirthChartPdfContext:
    metadata: Dict[str, Any]
    birth_summary: Dict[str, Any]
    charts: Dict[str, str]   # {"d1_svg": "...", "d9_svg": "..."}
    highlights: List[str]
    explainability: List[str]
