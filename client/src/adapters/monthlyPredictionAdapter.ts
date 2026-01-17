export interface UILifeArea {
  name: string;
  score: number;
  confidence: number;
  text: string;
}

export interface UIMonthlyPrediction {
  periodLabel: string;
  mahaDasha: string;
  antarDasha?: string;
  lifeAreas: UILifeArea[];
  transits: Record<string, any>;
  explainability: any;
}

export function adaptMonthlyPrediction(raw: any): UIMonthlyPrediction {
  const envelope = raw?.details?.envelope ?? {};
  const synthesis = raw?.details?.synthesis ?? {};
  const interpretation = raw?.details?.interpretation ?? {};

  const dashaContext = envelope.dasha_context ?? {};

  const lifeAreas: UILifeArea[] = Object.entries(
    synthesis.life_areas ?? {}
  ).map(([key, value]: any) => ({
    name: key,
    score: value.score ?? 0,
    confidence: value.confidence ?? 0,
    text: interpretation.by_life_area?.[key]?.text ?? "",
  }));

  return {
    periodLabel: `${envelope.reference?.month}/${envelope.reference?.year}`,
    mahaDasha: dashaContext.maha_lord ?? "—",
    antarDasha: dashaContext.antar_lord,
    lifeAreas,
    transits: envelope.environment?.transits ?? {},
    explainability: raw.explainability ?? {},
  };
}
