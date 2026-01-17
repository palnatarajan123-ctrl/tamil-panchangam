def build_interpretation_from_synthesis(
  *,
  envelope: dict,
  synthesis: dict
) -> dict:
  """
  EPIC-4.3
  Build deterministic narrative interpretation from synthesis + envelope.

  Output:
  - Structured text by life area
  - No paraphrasing
  - No LLM
  """

  interpretations = {}

  life_areas = synthesis["life_areas"]

  dasha = envelope["time_ruler"]["vimshottari_dasha"]
  dasha_lord = dasha.get("lord")

  transits = envelope["environment"]["transits"]
  pakshi = envelope["biological_rhythm"]["pancha_pakshi_daily"]

  for area, metrics in life_areas.items():
      score = metrics["score"]
      confidence = metrics["confidence"]

      # -------------------------------------------------
      # Tone selection
      # -------------------------------------------------
      if score >= 70:
          tone = "strongly favorable"
      elif score >= 55:
          tone = "moderately supportive"
      elif score >= 45:
          tone = "mixed"
      else:
          tone = "challenging"

      # -------------------------------------------------
      # Confidence modifier
      # -------------------------------------------------
      if confidence >= 0.85:
          certainty = "with high confidence"
      elif confidence >= 0.7:
          certainty = "with reasonable confidence"
      else:
          certainty = "with caution"

      # -------------------------------------------------
      # Deterministic narrative
      # -------------------------------------------------
      text = (
          f"For {area.replace('_', ' ')}, this period appears {tone} "
          f"{certainty}. "
          f"The active {dasha_lord} dasha sets the overall theme, "
          f"while current planetary transits and Pancha Pakshi timing "
          f"shape day-to-day outcomes."
      )

      interpretations[area] = {
          "text": text,
          "score": score,
          "confidence": confidence,
      }

  return {
      "by_life_area": interpretations,
      "note": (
          "This interpretation is derived from astrological factors. "
          "Use it as guidance, not as deterministic prediction."
      ),
  }
