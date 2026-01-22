export function adaptMonthlyPrediction(details: any) {
  const synthesis = details?.synthesis?.life_areas ?? {};
  const interpretation = details?.interpretation?.by_life_area ?? {};

  const life_areas = Object.keys(synthesis).map(key => {
    const synth = synthesis[key];
    const interp = interpretation[key];

    const fullText = interp?.text ?? "";

    return {
      key,
      label: key.replace("_", " "),
      score: synth.score,
      confidence: synth.confidence,
      sentiment:
        synth.score >= 65 ? "Positive" :
        synth.score >= 45 ? "Mixed" :
        "Challenging",
      summary: fullText,          // ✅ DO NOT TRUNCATE
      detail: fullText,           // ✅ SAME SOURCE
    };
  });

  return {
    meta: {
      generated_at: details.generated_at,
      engine_version: details.synthesis?.engine_version,
      period_label: "Monthly Prediction",
    },
    overview: {
      headline: "Overall monthly influence summary",
      overall_score: Math.round(
        life_areas.reduce((a, b) => a + b.score, 0) / life_areas.length
      ),
      confidence: details.synthesis?.confidence?.overall,
      tone: "Balanced",
    },
    life_areas,
    timing: {
      dominant_pakshi:
        details.biological_rhythm?.pancha_pakshi_daily?.dominant_pakshi,
      recommended:
        details.biological_rhythm?.pancha_pakshi_daily?.recommended_activities,
      avoid:
        details.biological_rhythm?.pancha_pakshi_daily?.avoid_activities,
    },
    disclaimers: [
      details.interpretation?.note,
    ].filter(Boolean),
  };
}
