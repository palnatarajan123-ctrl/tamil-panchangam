"""
This module will compute Divisional Charts (Varga Charts):
- D1 (Rasi) - Birth chart
- D9 (Navamsa) - Marriage and dharma
- D2 (Hora) - Wealth
- D3 (Drekkana) - Siblings
- D7 (Saptamsa) - Children
- D10 (Dasamsa) - Career
- D12 (Dwadasamsa) - Parents
- D60 (Shashtiamsa) - Overall destiny

"""

from typing import Dict, List

# Fixed South Indian Rasi order
RASI_ORDER = [
    "Mesham", "Rishabam", "Mithunam", "Kadakam",
    "Simmam", "Kanni", "Thulam", "Vrischikam",
    "Dhanusu", "Makaram", "Kumbham", "Meenam"
]

def build_d1_chart(
    lagna_rasi: str,
    planets: Dict[str, Dict]
) -> Dict[str, List[str]]:
    """
    Build D1 (Rasi) chart structure.
    Returns a dict of rasi -> list of planet symbols.
    """

    chart = {rasi: [] for rasi in RASI_ORDER}

    # Mark Lagna
    chart[lagna_rasi].append("La")

    for planet, data in planets.items():
        rasi = data["rasi"]
        chart[rasi].append(planet)

    return chart
