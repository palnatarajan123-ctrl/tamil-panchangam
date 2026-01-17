def paraphrase_interpretation(
  interpretation: dict,
  *,
  enabled: bool = False
) -> dict:
  """
  EPIC-4.4
  Optional paraphrasing layer.

  Rules:
  - Text only
  - Same structure in / out
  - Safe fallback if disabled
  """

  if not enabled:
      return interpretation

  paraphrased = {}

  for area, content in interpretation["by_life_area"].items():
      original_text = content["text"]

      # ---------------------------------------------
      # v1: Deterministic light rewrite (NO LLM)
      # ---------------------------------------------
      rewritten = (
          original_text
          .replace("this period appears", "this month shows")
          .replace("sets the overall theme", "establishes the broader context")
          .replace("shape day-to-day outcomes", "influence everyday experiences")
      )

      paraphrased[area] = {
          **content,
          "text": rewritten,
      }

  return {
      **interpretation,
      "by_life_area": paraphrased,
      "note": interpretation.get(
          "note",
          "This interpretation is derived from astrological factors."
      )
  }
