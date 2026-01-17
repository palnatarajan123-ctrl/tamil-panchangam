// client/src/models/prediction.ts

export type PredictionUIModel = {
  baseChartId: string;
  asOf: string;

  period: {
    type: "MONTH" | "EVENT";
    startDate: string;
    endDate: string;
    label: string;
  };

  dashaContext: {
    system: "VIMSHOTTARI";
    active: {
      maha: { lord: string; start: string; end: string };
      antara: { lord: string; start: string; end: string };
      pratyantara?: { lord: string; start: string; end: string };
    };
    overlap: {
      coverageRatio: number;
      dominantSegment: "maha" | "antara" | "pratyantara";
    };
  };

  gates: {
    eligible: boolean;
    reasons: string[];
  };

  confidence: {
    score: number;
    band: "LOW" | "MEDIUM" | "HIGH";
    signals: {
      code: string;
      weight: number;
      value: number;
    }[];
    notes: string[];
  };

  timeline: {
    start: string;
    end: string;
    strength: number;
    tags: string[];
  }[];
};

export type PredictionExplainability = {
  summary?: string;
  dominant_dasha?: string;
  transit_highlights?: string[];
};
