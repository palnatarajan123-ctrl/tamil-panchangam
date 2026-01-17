def interpret_monthly_guidance(
  synthesis: Dict,
  prediction: Dict,
) -> Dict:
  """
  Converts synthesis scores into human-readable guidance.
  Non-deterministic. No astrology math.
  """

  life_areas = synthesis["life_areas"]
  interpretations = {}

  for area, data in life_areas.items():
      score = data["score"]
      confidence = data["confidence"]

      # --- Resolve tone ---
      tone = "neutral"
      for low, high, label in SCORE_BANDS:
          if low <= score <= high:
              tone = label
              break

      # --- Resolve confidence label ---
      confidence_label = "low"
      for low, high, label in CONFIDENCE_BANDS:
          if low <= confidence <= high:
              confidence_label = label
              break

      pace = PACE_BY_CONFIDENCE[confidence_label]

      template = LIFE_AREA_TEMPLATES.get(area)
      if not template:
          continue

      text = template.format(
          tone=tone,
          pace=pace,
      )

      interpretations[area] = {
          "summary": text,
          "tone": tone,
          "confidence": confidence_label,
      }

  return {
      "interpretation_version": "interpretation-v1",
      "life_area_guidance": interpretations,
      "disclaimer": (
          "This interpretation provides reflective guidance only. "
          "It does not predict outcomes or replace personal judgment."
      ),
  }
