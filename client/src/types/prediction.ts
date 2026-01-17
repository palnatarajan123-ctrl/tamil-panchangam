export type Tone = "positive" | "neutral" | "caution";

export interface LifeAreaScore {
  raw_score: number;
  score: number;          // -100 → +100
  confidence: number;     // 0 → 1
}

export interface LifeAreas {
  career: LifeAreaScore;
  finance: LifeAreaScore;
  relationships: LifeAreaScore;
  health: LifeAreaScore;
  learning: LifeAreaScore;
  spirituality: LifeAreaScore;
}

export interface MonthlySynthesis {
  life_areas: LifeAreas;
  engine_version: string;
  generated_at: string;
}

export interface AreaInterpretation {
  summary: string;
  tone: Tone;
  confidence: number;
}

export interface MonthlyInterpretation {
  interpretation: Record<string, AreaInterpretation>;
  narrative_style: "short" | "practical" | "reflective";
  engine_version: string;
}

export interface MonthlyPredictionResponse {
  base_chart_id: string;
  checksum: string;
  prediction: any; // we’ll visualize this later
  synthesis: MonthlySynthesis;
}
