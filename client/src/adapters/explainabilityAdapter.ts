// EPIC-8 explainability adapter (drivers, not life areas)

export type ExplainabilityUI = {
  summary?: string;
  dominant_dasha?: string;
  transit_highlights?: string[];
};

export function adaptExplainability(raw: any): ExplainabilityUI | undefined {
  if (!raw) return undefined;

  return {
    summary: raw.summary,
    dominant_dasha: raw.dominant_dasha,
    transit_highlights: raw.transit_highlights ?? [],
  };
}
