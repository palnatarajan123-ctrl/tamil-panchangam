export type LifeArea =
  | "career"
  | "finance"
  | "relationships"
  | "health"
  | "education"
  | "family"
  | "spirituality";

export interface ExplainabilityGate {
  area: LifeArea;
  score: number;          // 0–100
  signal: "positive" | "neutral" | "challenging";
  rationale: string[];    // short bullet reasons
  planets?: string[];
  houses?: number[];
}

export interface ExplainabilitySummary {
  overall_tone: "supportive" | "mixed" | "challenging";
  dominant_areas: LifeArea[];
}

export interface ExplainabilityUI {
  summary: ExplainabilitySummary;
  gates: ExplainabilityGate[];
}
