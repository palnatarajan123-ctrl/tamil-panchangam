// EPIC-9+ ONLY — DO NOT USE IN EPIC-6 / EPIC-8

export function adaptExplainabilityLifeAreas(raw: any) {
  if (!raw || !raw.life_areas) {
    return {
      summary: {
        overall_tone: "mixed",
        dominant_areas: [],
      },
      gates: [],
    };
  }

  const gates = Object.entries(raw.life_areas).map(
    ([area, data]: any) => ({
      area,
      score: data.score ?? 50,
      signal:
        data.score > 65
          ? "positive"
          : data.score < 40
          ? "challenging"
          : "neutral",
      rationale: data.notes ?? [],
      planets: data.planets ?? [],
      houses: data.houses ?? [],
    })
  );

  return {
    summary: {
      overall_tone: gates.some(g => g.signal === "challenging")
        ? "mixed"
        : "supportive",
      dominant_areas: gates
        .filter(g => g.score >= 65)
        .map(g => g.area),
    },
    gates,
  };
}
