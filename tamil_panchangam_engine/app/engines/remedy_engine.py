"""
Remedy Engine - EPIC Signal Expansion

Suggests remedies based on:
- Challenging gochara (transits)
- Weak tara bala
- Heavy Saturn/Rahu influence
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SATURN_REMEDIES = {
    "janma_sani": [
        "Worship Hanuman on Saturdays",
        "Light sesame oil lamp on Saturdays",
        "Feed crows with rice and black lentils",
        "Donate black cloth or iron items on Saturdays",
    ],
    "ashtama_sani": [
        "Recite Shani Stotra or Hanuman Chalisa",
        "Offer blue flowers at Shani temple",
        "Practice patience and avoid major decisions",
        "Donate to elderly or disabled persons",
    ],
    "kantaka_sani": [
        "Perform Shani Shanti puja",
        "Wear blue sapphire after proper consultation",
        "Feed black dogs or crows on Saturdays",
        "Avoid conflicts and practice humility",
    ],
}

RAHU_REMEDIES = [
    "Worship Lord Ganesha before new ventures",
    "Recite Durga Chalisa on Tuesdays",
    "Donate mustard oil on Saturdays",
    "Avoid making major decisions during eclipses",
    "Keep surroundings clean and organized",
]

KETU_REMEDIES = [
    "Worship Lord Ganesha",
    "Donate gray or multi-colored cloth",
    "Practice meditation and spiritual study",
    "Feed street dogs",
    "Avoid excessive attachment to outcomes",
]

JUPITER_WEAK_REMEDIES = [
    "Worship Lord Vishnu on Thursdays",
    "Donate yellow items on Thursdays",
    "Wear yellow clothes on Thursdays",
    "Respect teachers and elders",
    "Study sacred texts or philosophy",
]

TARA_BALA_REMEDIES = {
    "vipat": [
        "Avoid signing contracts or major commitments",
        "Practice extra caution in travel",
        "Recite protective mantras",
    ],
    "pratyak": [
        "Be mindful of small obstacles",
        "Double-check important communications",
        "Maintain patience in dealings",
    ],
    "naidhana": [
        "Avoid starting new projects",
        "Focus on rest and recuperation",
        "Practice pranayama for energy",
    ],
}

DAY_RECOMMENDATIONS = {
    "Sunday": "Good for spiritual activities and meeting authorities",
    "Monday": "Favorable for new beginnings and travel",
    "Tuesday": "Avoid major decisions, good for courage-related activities",
    "Wednesday": "Excellent for business, learning, and communication",
    "Thursday": "Highly auspicious for education, marriage, and expansion",
    "Friday": "Good for relationships, arts, and financial matters",
    "Saturday": "Practice patience, good for service and discipline",
}


def compute_remedies(
    gochara: Optional[Dict] = None,
    nakshatra_context: Optional[Dict] = None,
    ashtakavarga: Optional[Dict] = None,
) -> Dict:
    """
    Compute remedies based on current astrological situation.
    
    Aggregates recommendations from multiple signal sources.
    """
    logger.debug("DEBUG: Remedy engine computing recommendations")
    
    recommended = []
    cautions = []
    favorable_activities = []
    
    try:
        if gochara:
            saturn = gochara.get("saturn", {})
            saturn_phase = saturn.get("phase", "neutral")
            saturn_effect = saturn.get("effect", "neutral")
            
            if saturn_phase in SATURN_REMEDIES:
                recommended.extend(SATURN_REMEDIES[saturn_phase][:2])
            
            if saturn_effect == "challenging":
                cautions.append("Major life decisions require extra consideration during Saturn transit")
            
            jupiter = gochara.get("jupiter", {})
            jupiter_effect = jupiter.get("effect", "neutral")
            
            if jupiter_effect == "challenging":
                recommended.extend(JUPITER_WEAK_REMEDIES[:2])
            elif jupiter_effect == "favorable":
                favorable_activities.append("Education, spiritual growth, and expansion activities are supported")
            
            rahu_ketu = gochara.get("rahu_ketu", {})
            rahu_effect = rahu_ketu.get("effect", "neutral")
            
            if rahu_effect == "disruptive":
                recommended.extend(RAHU_REMEDIES[:2])
                cautions.append("Avoid impulsive decisions and verify important information")
        
        if nakshatra_context:
            tara_bala = nakshatra_context.get("tara_bala", "")
            quality = nakshatra_context.get("quality", "neutral")
            
            if tara_bala in TARA_BALA_REMEDIES:
                recommended.extend(TARA_BALA_REMEDIES[tara_bala][:2])
            
            if quality == "favorable":
                favorable_activities.append("Current nakshatra supports new initiatives and important decisions")
            elif quality == "challenging":
                cautions.append(nakshatra_context.get("note", "Extra care advised"))
        
        if ashtakavarga:
            overall_support = ashtakavarga.get("overall_support", "balanced")
            
            if overall_support == "needs_remedies":
                saturn_strength = ashtakavarga.get("saturn", {}).get("strength", "")
                jupiter_strength = ashtakavarga.get("jupiter", {}).get("strength", "")
                
                if saturn_strength == "resistance":
                    recommended.append("Strengthen Saturn through service and discipline")
                if jupiter_strength == "resistance":
                    recommended.append("Strengthen Jupiter through learning and gratitude")
            elif overall_support == "strong_support":
                favorable_activities.append("Ashtakavarga indicates strong support for major initiatives")
        
        recommended = list(dict.fromkeys(recommended))[:5]
        cautions = list(dict.fromkeys(cautions))[:3]
        favorable_activities = list(dict.fromkeys(favorable_activities))[:3]
        
        if not recommended and not favorable_activities:
            recommended = ["Maintain regular spiritual practices", "Practice gratitude and mindfulness"]
        
        remedies = {
            "recommended": recommended,
            "cautions": cautions,
            "favorable_activities": favorable_activities,
            "day_guidance": DAY_RECOMMENDATIONS,
            "note": "Remedies are suggested based on current transit configurations",
        }
        
        logger.debug(f"DEBUG: Remedies computed: {len(recommended)} recommendations, {len(cautions)} cautions")
        
        return remedies
        
    except Exception as e:
        logger.error(f"ERROR: Remedy computation failed: {e}")
        return {
            "recommended": ["Maintain regular spiritual practices"],
            "cautions": [],
            "favorable_activities": [],
            "error": str(e),
        }
