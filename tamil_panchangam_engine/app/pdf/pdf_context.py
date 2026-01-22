from typing import Dict, List, Optional
from datetime import datetime

class PdfContext:
    pdf_context_version: str = "v1"

    metadata: Dict[str, str]  # chart_id, prediction_id, month, year, generated_at

    birth_summary: Dict[str, str]

    charts: Dict[str, str]  # { "d1_svg": "...", "d9_svg": "..." }

    narrative: Dict[str, str]

    life_areas: List[Dict[str, str]]

    explainability: List[Dict[str, str]]
