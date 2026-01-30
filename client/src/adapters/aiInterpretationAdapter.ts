// client/src/adapters/aiInterpretationAdapter.ts
// AI Interpretation Engine v1.0/v2.0 → Prediction UI View Model Adapter
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

// V2 Monthly Theme
export interface MonthlyThemeViewModel {
  title: string;
  narrative: string;
}

// V2 Overview (enhanced)
export interface OverviewViewModel {
  energyPattern: string;
  keyFocus?: string[];
  avoidOrBeMindful?: string[];
}

// V2 Practices & Reflection
export interface PracticesViewModel {
  dailyPractice?: string;
  weeklyPractice?: string;
  reflectionQuestion?: string;
}

// V2 Closing
export interface ClosingViewModel {
  keyTakeaways?: string[];
  encouragement?: string;
}

// V1 Window Summary (legacy)
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

// V2 Life Area (enhanced)
export interface LifeAreaViewModel {
  key: string;
  label: string;
  score: number;
  outlook: string;
  summary: string;
  deeperExplanation?: string;
  opportunity?: string;
  watchOut?: string;
  oneAction?: string;
  attribution?: LifeAreaAttribution;
}

// Unified Prediction View Model (supports v1 and v2)
export interface PredictionViewModel {
  engineVersion: string;
  generatedAt: string;
  // V2 fields
  monthlyTheme?: MonthlyThemeViewModel;
  overview?: OverviewViewModel;
  practicesAndReflection?: PracticesViewModel;
  closing?: ClosingViewModel;
  // V1 legacy field
  windowSummary?: WindowSummaryViewModel;
  // Shared
  lifeAreas: LifeAreaViewModel[];
  explainabilityLevel: ExplainabilityLevel;
}

// V2 Input Schema
export interface AIInterpretationV2 {
  engine_version: "ai-interpretation-v2.0";
  generated_at: string;
  monthly_theme: {
    title: string;
    narrative: string;
  };
  overview: {
    energy_pattern: string;
    key_focus?: string[];
    avoid_or_be_mindful?: string[];
  };
  life_areas: {
    [key: string]: {
      score: number;
      outlook: string;
      summary: string;
      opportunity?: string;
      watch_out?: string;
      one_action?: string;
    };
  };
  practices_and_reflection: {
    daily_practice?: string;
    weekly_practice?: string;
    reflection_question?: string;
  };
  closing: {
    key_takeaways?: string[];
    encouragement?: string;
  };
  _visibility?: {
    level?: string;
    show_monthly_theme?: boolean;
    show_overview?: boolean;
    show_practices?: boolean;
    show_closing?: boolean;
  };
}

// V1 Input Schema (legacy)
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
  health_and_energy: "Health & Energy",
  personal_growth: "Personal Growth",
};

const LIFE_AREA_ORDER = ["career", "finance", "relationships", "health", "health_and_energy", "personal_growth"];

function isV2Interpretation(obj: any): obj is AIInterpretationV2 {
  return obj?.engine_version === "ai-interpretation-v2.0";
}

function isV1Interpretation(obj: any): obj is AIInterpretationV1 {
  return (
    obj?.engine_version === "ai-interpretation-v1.0" ||
    (obj?.window_summary != null && obj?.life_areas != null)
  );
}

export function adaptAIInterpretationV2(
  aiInterpretation: AIInterpretationV2,
  level: ExplainabilityLevel = "full"
): PredictionViewModel {
  const visibility = aiInterpretation._visibility;
  const showTheme = level !== "minimal" && (visibility?.show_monthly_theme !== false);
  const showOverview = level !== "minimal" && (visibility?.show_overview !== false);
  const showPractices = level !== "minimal" && (visibility?.show_practices !== false);
  const showClosing = level !== "minimal" && (visibility?.show_closing !== false);

  const result: PredictionViewModel = {
    engineVersion: aiInterpretation.engine_version,
    generatedAt: aiInterpretation.generated_at,
    lifeAreas: [],
    explainabilityLevel: level,
  };

  if (showTheme && aiInterpretation.monthly_theme) {
    result.monthlyTheme = {
      title: aiInterpretation.monthly_theme.title,
      narrative: aiInterpretation.monthly_theme.narrative,
    };
  }

  if (showOverview && aiInterpretation.overview) {
    result.overview = {
      energyPattern: aiInterpretation.overview.energy_pattern,
    };
    if (aiInterpretation.overview.key_focus?.length) {
      result.overview.keyFocus = aiInterpretation.overview.key_focus;
    }
    if (aiInterpretation.overview.avoid_or_be_mindful?.length) {
      result.overview.avoidOrBeMindful = aiInterpretation.overview.avoid_or_be_mindful;
    }
  }

  if (showPractices && aiInterpretation.practices_and_reflection) {
    const practices: PracticesViewModel = {};
    if (aiInterpretation.practices_and_reflection.daily_practice) {
      practices.dailyPractice = aiInterpretation.practices_and_reflection.daily_practice;
    }
    if (aiInterpretation.practices_and_reflection.weekly_practice) {
      practices.weeklyPractice = aiInterpretation.practices_and_reflection.weekly_practice;
    }
    if (aiInterpretation.practices_and_reflection.reflection_question) {
      practices.reflectionQuestion = aiInterpretation.practices_and_reflection.reflection_question;
    }
    if (Object.keys(practices).length > 0) {
      result.practicesAndReflection = practices;
    }
  }

  if (showClosing && aiInterpretation.closing) {
    const closing: ClosingViewModel = {};
    if (aiInterpretation.closing.key_takeaways?.length) {
      closing.keyTakeaways = aiInterpretation.closing.key_takeaways;
    }
    if (aiInterpretation.closing.encouragement) {
      closing.encouragement = aiInterpretation.closing.encouragement;
    }
    if (Object.keys(closing).length > 0) {
      result.closing = closing;
    }
  }

  result.lifeAreas = LIFE_AREA_ORDER
    .filter(key => key in aiInterpretation.life_areas)
    .map(key => {
      const area = aiInterpretation.life_areas[key];
      const viewModel: LifeAreaViewModel = {
        key,
        label: LIFE_AREA_LABELS[key] ?? key,
        score: area.score,
        outlook: area.outlook ?? "neutral",
        summary: area.summary,
      };

      if (area.opportunity) {
        viewModel.opportunity = area.opportunity;
      }
      if (area.watch_out) {
        viewModel.watchOut = area.watch_out;
      }
      if (area.one_action) {
        viewModel.oneAction = area.one_action;
      }

      return viewModel;
    });

  return result;
}

export function adaptAIInterpretation(
  aiInterpretation: AIInterpretationV1,
  level: ExplainabilityLevel = "full"
): PredictionViewModel {
  const visibility = aiInterpretation._visibility;
  
  const backendLevel = visibility?.level as ExplainabilityLevel | undefined;
  const backendShowDominant = backendLevel ? backendLevel !== "minimal" : true;
  const backendShowTiming = backendLevel ? backendLevel !== "minimal" : true;
  const backendShowDeeper = backendLevel ? backendLevel !== "minimal" : true;
  const backendShowAttr = backendLevel ? backendLevel === "full" : true;
  const backendShowSignals = backendLevel ? backendLevel === "full" : true;
  
  const uiShowDominant = level !== "minimal";
  const uiShowTiming = level !== "minimal";
  const uiShowDeeper = level !== "minimal";
  const uiShowAttr = level === "full";
  const uiShowSignals = level === "full";

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

function isValidInterpretationShape(obj: any): boolean {
  if (isV2Interpretation(obj)) {
    return true;
  }
  return (
    obj?.engine_version === "ai-interpretation-v1.0" &&
    obj?.window_summary != null &&
    obj?.life_areas != null
  );
}

export function hasValidAIInterpretation(details: any): boolean {
  const llmInterp = details?.interpretation?.llm_interpretation;
  const aiInterp = details?.interpretation?.ai_interpretation;
  return isValidInterpretationShape(llmInterp) || isValidInterpretationShape(aiInterp);
}

export function extractAIInterpretation(details: any): AIInterpretationV1 | AIInterpretationV2 | null {
  if (!hasValidAIInterpretation(details)) {
    return null;
  }
  
  const llmInterp = details.interpretation.llm_interpretation;
  const aiInterp = details.interpretation.ai_interpretation;
  
  if (isValidInterpretationShape(llmInterp)) {
    return llmInterp;
  }
  
  return aiInterp;
}

// Unified adapter that handles both v1 and v2
export function adaptInterpretation(
  interpretation: AIInterpretationV1 | AIInterpretationV2,
  level: ExplainabilityLevel = "full"
): PredictionViewModel {
  if (isV2Interpretation(interpretation)) {
    return adaptAIInterpretationV2(interpretation, level);
  }
  return adaptAIInterpretation(interpretation as AIInterpretationV1, level);
}
