from typing import Dict

AREA_DISPLAY_NAMES = {
    "career": "Career",
    "finance": "Finance",
    "relationships": "Relationships",
    "health": "Health",
    "personal_growth": "Personal Growth",
}

AREA_SPECIFIC_GUIDANCE = {
    "career": {
        "strong_positive": (
            "This is an excellent month for career advancement. Your professional efforts are well-supported by planetary alignments. "
            "Consider initiating new projects, seeking promotions, or expanding your professional network. "
            "Decision-making ability is enhanced, making this ideal for strategic moves."
        ),
        "positive": (
            "Career prospects are favorable this month. Progress in professional matters comes with steady effort. "
            "This is a good time to consolidate gains, complete pending work, and build credibility. "
            "Collaborative ventures are particularly well-aspected."
        ),
        "mixed": (
            "Career matters show a balanced outlook this month. While opportunities exist, careful evaluation is advised before major decisions. "
            "Focus on refining skills and strengthening workplace relationships. "
            "Avoid impulsive job changes; patience brings better clarity."
        ),
        "challenging": (
            "Career requires extra attention this month. Workplace dynamics may feel more demanding than usual. "
            "Focus on completing essential tasks and avoid confrontations with colleagues or superiors. "
            "This is a period for consolidation rather than expansion."
        ),
    },
    "finance": {
        "strong_positive": (
            "Financial prospects are highly favorable this month. Investments and income sources are well-supported. "
            "This is an opportune time for financial planning, negotiations, or starting new income streams. "
            "Unexpected gains or positive developments in monetary matters are possible."
        ),
        "positive": (
            "Finances show a positive trend this month. Regular income remains stable with potential for modest growth. "
            "Budgeting and disciplined spending will amplify benefits. "
            "Consider reviewing investments or exploring additional income opportunities."
        ),
        "mixed": (
            "Financial matters require balanced attention this month. Income remains steady but unexpected expenses may arise. "
            "Maintain a conservative approach to spending and avoid speculative investments. "
            "Focus on building savings and clearing any pending obligations."
        ),
        "challenging": (
            "Financial caution is advised this month. Expenditures may exceed expectations, requiring careful budget management. "
            "Postpone major purchases or investments if possible. "
            "Focus on essentials and avoid lending or borrowing during this period."
        ),
    },
    "relationships": {
        "strong_positive": (
            "Relationships flourish this month with strong planetary support for emotional connections. "
            "This is an excellent time for deepening bonds, resolving past misunderstandings, or starting new relationships. "
            "Social interactions bring joy and meaningful connections are likely."
        ),
        "positive": (
            "Relationship harmony is favored this month. Communication flows well with family and loved ones. "
            "Existing partnerships strengthen through mutual understanding. "
            "This is a good period for social gatherings and reconnecting with distant relatives or friends."
        ),
        "mixed": (
            "Relationships show mixed influences this month. While connections remain stable, minor misunderstandings may occur. "
            "Practice patience and clear communication to navigate sensitive topics. "
            "Avoid making assumptions; seek clarity through open dialogue."
        ),
        "challenging": (
            "Relationships require extra care this month. Emotional sensitivities may be heightened, leading to potential friction. "
            "Choose words thoughtfully and give space when needed. "
            "Focus on maintaining peace rather than proving points. Healing comes through patience."
        ),
    },
    "health": {
        "strong_positive": (
            "Health and vitality are strongly supported this month. Energy levels are high and recovery from any ailments is swift. "
            "This is an excellent time to start new fitness routines or health practices. "
            "Mental clarity and emotional balance complement physical wellbeing."
        ),
        "positive": (
            "Health outlook is favorable this month. Maintaining regular routines supports overall wellbeing. "
            "Minor ailments resolve quickly with proper rest. "
            "This is a good period for preventive health measures and stress management practices."
        ),
        "mixed": (
            "Health requires mindful attention this month. While no major concerns are indicated, fatigue or minor discomfort may occur. "
            "Prioritize adequate sleep, balanced nutrition, and regular exercise. "
            "Address stress proactively to maintain equilibrium."
        ),
        "challenging": (
            "Health matters need extra attention this month. Energy levels may fluctuate, requiring more rest than usual. "
            "Avoid overexertion and pay attention to early warning signs. "
            "Stress management and self-care practices are particularly important during this period."
        ),
    },
    "personal_growth": {
        "strong_positive": (
            "Personal growth opportunities abound this month. Spiritual practices, learning, and self-reflection are deeply rewarding. "
            "This is an ideal time for pursuing new knowledge, starting courses, or deepening meditation practices. "
            "Insights gained now have lasting positive impact."
        ),
        "positive": (
            "Personal development is well-supported this month. Learning new skills comes naturally and self-improvement efforts yield results. "
            "Reading, contemplation, and creative pursuits are particularly beneficial. "
            "Trust your intuition in matters of personal direction."
        ),
        "mixed": (
            "Personal growth continues at a steady pace this month. While major breakthroughs may not occur, consistent effort builds foundation. "
            "Focus on integrating past lessons rather than seeking new ones. "
            "Reflection on values and priorities brings useful clarity."
        ),
        "challenging": (
            "Personal growth may feel slower this month. Inner restlessness or lack of direction is temporary. "
            "Use this time for rest and consolidation rather than pushing for progress. "
            "Journaling and quiet reflection help process underlying patterns."
        ),
    },
}


def _get_tone_from_score(score: float) -> str:
    if score >= 75:
        return "strong_positive"
    elif score >= 65:
        return "positive"
    elif score >= 45:
        return "mixed"
    else:
        return "challenging"


def _get_summary_for_area(area: str, score: float) -> str:
    tone = _get_tone_from_score(score)
    area_guidance = AREA_SPECIFIC_GUIDANCE.get(area, {})
    return area_guidance.get(tone, f"{AREA_DISPLAY_NAMES.get(area, area)} shows balanced influences this month.")


def build_interpretation(
    synthesis: Dict,
    narrative_style: str = "short"
) -> Dict:
    life_areas = synthesis.get("life_areas", {})
    interpretation = {}

    for area, data in life_areas.items():
        score = data.get("score", 50)
        confidence = data.get("confidence", 0.5)

        tone = _get_tone_from_score(score)
        summary = _get_summary_for_area(area, score)

        interpretation[area] = {
            "summary": summary,
            "tone": tone,
            "confidence": confidence,
            "confidence_explanation": None,
        }

    return {
        "interpretation": interpretation,
        "narrative_style": narrative_style,
        "engine_version": "interpretation-builder-v4",
    }
