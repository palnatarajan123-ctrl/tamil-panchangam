// client/src/adapters/aiInterpretationAdapter.ts
// AI Interpretation Engine v1.0 → Prediction UI View Model Adapter
// 
// This adapter is the SINGLE source of truth for mapping AI Interpretation
// output to UI-ready view models. The UI renders ONLY what this adapter returns.
//
// Hard constraints:
// - No fallback text generation
// - No default values for missing interpretation data
// - Omit fields if not present in AI Interpretation output
// - Apply explainability filtering (minimal/standard/full)

export type ExplainabilityLevel = "minimal" | "standard" | "full";

export interface DominantForce {
  type: string;
  description: string;
}

export interface WindowSummaryViewModel {
  momentum: string;
  overview: string;
  outcomeMode: string;
  dominantForces?: DominantForce[];
  timingGuidance?: string;
}

export interface LifeAreaAttribution {
  planets?: string[];
  dasha?: string;
  engines?: string[];
  signalsUsed?: Array<{
    engine: string;
    weight: number;
    valence: string;
  }>;
}

export interface LifeAreaViewModel {
  key: string;
  label: string;
  score: number;
  outlook: string;
  summary: string;
  deeperExplanation?: string;
  attribution?: LifeAreaAttribution;
}

export interface PredictionViewModel {
  engineVersion: string;
  generatedAt: string;
  windowSummary: WindowSummaryViewModel;
  lifeAreas: LifeAreaViewModel[];
  explainabilityLevel: ExplainabilityLevel;
}

export interface AIInterpretationV1 {
  engine_version: string;
  generated_at: string;
  window_summary: {
    momentum: string;
    overview: string;
    outcome_mode: string;
    dominant_forces?: Array<{ type: string; description: string }>;
    timing_guidance?: string;
  };
  life_areas: {
    [key: string]: {
      score: number;
      outlook: string;
      summary: string;
      deeper_explanation?: string;
      attribution?: {
        planets?: string[];
        dasha?: string;
        engines?: string[];
        signals_used?: Array<{
          engine: string;
          weight: number;
          valence: string;
        }>;
      };
    };
  };
  _visibility?: {
    level?: string;
    show_dominant_forces?: boolean;
    show_timing_guidance?: boolean;
    show_deeper_explanation?: boolean;
    show_attribution?: boolean;
    show_signals_used?: boolean;
  };
}

const LIFE_AREA_LABELS: Record<string, string> = {
  career: "Career",
  finance: "Finance",
  relationships: "Relationships",
  health: "Health",
  personal_growth: "Personal Growth",
};

const LIFE_AREA_ORDER = ["career", "finance", "relationships", "health", "personal_growth"];

export function adaptAIInterpretation(
  aiInterpretation: AIInterpretationV1,
  level: ExplainabilityLevel = "full"
): PredictionViewModel {
  // Combine UI level with backend visibility (AND logic - more restrictive wins)
  const visibility = aiInterpretation._visibility;
  
  // If backend provides a level, derive implied flags from it
  const backendLevel = visibility?.level as ExplainabilityLevel | undefined;
  const backendShowDominant = backendLevel ? backendLevel !== "minimal" : true;
  const backendShowTiming = backendLevel ? backendLevel !== "minimal" : true;
  const backendShowDeeper = backendLevel ? backendLevel !== "minimal" : true;
  const backendShowAttr = backendLevel ? backendLevel === "full" : true;
  const backendShowSignals = backendLevel ? backendLevel === "full" : true;
  
  // UI wants to show, but backend may restrict - use AND logic
  const uiShowDominant = level !== "minimal";
  const uiShowTiming = level !== "minimal";
  const uiShowDeeper = level !== "minimal";
  const uiShowAttr = level === "full";
  const uiShowSignals = level === "full";

  // Combine: explicit flags override level-derived flags, then AND with UI
  const showDominantForces = uiShowDominant && (visibility?.show_dominant_forces ?? backendShowDominant);
  const showTimingGuidance = uiShowTiming && (visibility?.show_timing_guidance ?? backendShowTiming);
  const showDeeperExplanation = uiShowDeeper && (visibility?.show_deeper_explanation ?? backendShowDeeper);
  const showAttribution = uiShowAttr && (visibility?.show_attribution ?? backendShowAttr);
  const showSignalsUsed = uiShowSignals && (visibility?.show_signals_used ?? backendShowSignals);

  const windowSummary: WindowSummaryViewModel = {
    momentum: aiInterpretation.window_summary.momentum,
    overview: aiInterpretation.window_summary.overview,
    outcomeMode: aiInterpretation.window_summary.outcome_mode,
  };

  if (
    showDominantForces &&
    aiInterpretation.window_summary.dominant_forces &&
    aiInterpretation.window_summary.dominant_forces.length > 0
  ) {
    windowSummary.dominantForces = aiInterpretation.window_summary.dominant_forces;
  }

  if (showTimingGuidance && aiInterpretation.window_summary.timing_guidance) {
    windowSummary.timingGuidance = aiInterpretation.window_summary.timing_guidance;
  }

  const lifeAreas: LifeAreaViewModel[] = LIFE_AREA_ORDER
    .filter(key => key in aiInterpretation.life_areas)
    .map(key => {
      const area = aiInterpretation.life_areas[key];

      const viewModel: LifeAreaViewModel = {
        key,
        label: LIFE_AREA_LABELS[key] ?? key,
        score: area.score,
        outlook: area.outlook,
        summary: area.summary,
      };

      if (showDeeperExplanation && area.deeper_explanation) {
        viewModel.deeperExplanation = area.deeper_explanation;
      }

      if (showAttribution && area.attribution) {
        const attribution: LifeAreaAttribution = {};

        if (area.attribution.planets && area.attribution.planets.length > 0) {
          attribution.planets = area.attribution.planets;
        }

        if (area.attribution.dasha && area.attribution.dasha !== "X") {
          attribution.dasha = area.attribution.dasha;
        }

        if (area.attribution.engines && area.attribution.engines.length > 0) {
          attribution.engines = area.attribution.engines;
        }

        if (
          showSignalsUsed &&
          area.attribution.signals_used &&
          area.attribution.signals_used.length > 0
        ) {
          attribution.signalsUsed = area.attribution.signals_used;
        }

        if (Object.keys(attribution).length > 0) {
          viewModel.attribution = attribution;
        }
      }

      return viewModel;
    });

  return {
    engineVersion: aiInterpretation.engine_version,
    generatedAt: aiInterpretation.generated_at,
    windowSummary,
    lifeAreas,
    explainabilityLevel: level,
  };
}

export function hasValidAIInterpretation(details: any): boolean {
  return (
    details?.interpretation?.ai_interpretation?.engine_version === "ai-interpretation-v1.0" &&
    details?.interpretation?.ai_interpretation?.window_summary != null &&
    details?.interpretation?.ai_interpretation?.life_areas != null
  );
}

export function extractAIInterpretation(details: any): AIInterpretationV1 | null {
  if (!hasValidAIInterpretation(details)) {
    return null;
  }
  return details.interpretation.ai_interpretation as AIInterpretationV1;
}
