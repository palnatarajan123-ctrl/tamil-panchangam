// client/src/adapters/aiInterpretationAdapter.ts
// AI Interpretation Engine v1.0/v2.0/v3.0 → Prediction UI View Model Adapter
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

export interface MonthlyThemeViewModel {
  title: string;
  narrative: string;
}

export interface OverviewViewModel {
  energyPattern: string;
  keyFocus?: string[];
  avoidOrBeMindful?: string[];
  attributionSummary?: AttributionSummaryViewModel;
}

export interface AttributionSummaryViewModel {
  activePlanets: string[];
  activeDasha?: string;
  activeEngines: string[];
}

export interface PracticesViewModel {
  dailyPractice?: string;
  weeklyPractice?: string;
  reflectionQuestion?: string;
  reflectionGuidance?: string;
}

export interface ClosingViewModel {
  keyTakeaways?: string[];
  encouragement?: string;
}

export interface WindowSummaryViewModel {
  momentum: string;
  overview: string;
  outcomeMode: string;
  dominantForces?: DominantForce[];
  timingGuidance?: string;
  attributionSummary?: AttributionSummaryViewModel;
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
  opportunity?: string;
  watchOut?: string;
  oneAction?: string;
  attribution?: LifeAreaAttribution;
}

export interface VedaRemedyViewModel {
  primaryRemedy: string;
  supportingPractice?: string;
  specificRemedies?: string[];
}

export interface PredictionViewModel {
  engineVersion: string;
  generatedAt: string;
  monthlyTheme?: MonthlyThemeViewModel;
  overview?: OverviewViewModel;
  practicesAndReflection?: PracticesViewModel;
  closing?: ClosingViewModel;
  windowSummary?: WindowSummaryViewModel;
  yearlyMantra?: string;
  dashaTransitSynthesis?: string;
  dangerWindows?: string[];
  vedaRemedy?: VedaRemedyViewModel;
  lifeAreas: LifeAreaViewModel[];
  explainabilityLevel: ExplainabilityLevel;
}

export interface AIInterpretationV3 {
  engine_version: "ai-interpretation-v3.0";
  generated_at: string;
  yearly_mantra: string;
  dasha_transit_synthesis: string;
  life_areas: {
    [key: string]: {
      score: number;
      outlook: string;
      summary: string;
    };
  };
  danger_windows?: string[];
  veda_remedy: {
    primary_remedy: string;
    supporting_practice?: string;
    specific_remedies?: string[];
  };
  closing: {
    key_takeaways?: string[];
    encouragement?: string;
  };
  _visibility?: {
    level?: string;
    show_yearly_mantra?: boolean;
    show_dasha_synthesis?: boolean;
    show_danger_windows?: boolean;
    show_veda_remedy?: boolean;
    show_closing?: boolean;
  };
}

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
    reflection_guidance?: string;
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

function isV3Interpretation(obj: any): obj is AIInterpretationV3 {
  return obj?.engine_version === "ai-interpretation-v3.0";
}

function isV2Interpretation(obj: any): obj is AIInterpretationV2 {
  return obj?.engine_version === "ai-interpretation-v2.0";
}

function isV1Interpretation(obj: any): obj is AIInterpretationV1 {
  return (
    obj?.engine_version === "ai-interpretation-v1.0" ||
    (obj?.window_summary != null && obj?.life_areas != null)
  );
}

export function adaptAIInterpretationV3(
  aiInterpretation: AIInterpretationV3,
  level: ExplainabilityLevel = "full"
): PredictionViewModel {
  const visibility = aiInterpretation._visibility;
  const showMantra = level !== "minimal" && (visibility?.show_yearly_mantra !== false);
  const showSynthesis = level !== "minimal" && (visibility?.show_dasha_synthesis !== false);
  const showDangerWindows = level !== "minimal" && (visibility?.show_danger_windows !== false);
  const showRemedy = level !== "minimal" && (visibility?.show_veda_remedy !== false);
  const showClosing = level !== "minimal" && (visibility?.show_closing !== false);

  const result: PredictionViewModel = {
    engineVersion: aiInterpretation.engine_version,
    generatedAt: aiInterpretation.generated_at,
    lifeAreas: [],
    explainabilityLevel: level,
  };

  if (showMantra && aiInterpretation.yearly_mantra) {
    result.yearlyMantra = aiInterpretation.yearly_mantra;
  }

  if (showSynthesis && aiInterpretation.dasha_transit_synthesis) {
    result.dashaTransitSynthesis = aiInterpretation.dasha_transit_synthesis;
  }

  if (showDangerWindows && aiInterpretation.danger_windows?.length) {
    result.dangerWindows = aiInterpretation.danger_windows;
  }

  if (showRemedy && aiInterpretation.veda_remedy) {
    const remedy: VedaRemedyViewModel = {
      primaryRemedy: aiInterpretation.veda_remedy.primary_remedy,
    };
    if (aiInterpretation.veda_remedy.supporting_practice) {
      remedy.supportingPractice = aiInterpretation.veda_remedy.supporting_practice;
    }
    if (aiInterpretation.veda_remedy.specific_remedies?.length) {
      remedy.specificRemedies = aiInterpretation.veda_remedy.specific_remedies;
    }
    result.vedaRemedy = remedy;
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
      return {
        key,
        label: LIFE_AREA_LABELS[key] ?? key,
        score: area.score,
        outlook: area.outlook ?? "neutral",
        summary: area.summary,
      };
    });

  return result;
}

export function adaptAIInterpretationV2(
  aiInterpretation: AIInterpretationV2,
  level: ExplainabilityLevel = "full",
  deterministicInterpretation?: AIInterpretationV1
): PredictionViewModel {
  const visibility = aiInterpretation._visibility;
  const showTheme = level !== "minimal" && (visibility?.show_monthly_theme !== false);
  const showOverview = level !== "minimal" && (visibility?.show_overview !== false);
  const showPractices = level !== "minimal" && (visibility?.show_practices !== false);
  const showClosing = level !== "minimal" && (visibility?.show_closing !== false);
  const showAttribution = level === "full";

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
    
    if (showAttribution && deterministicInterpretation?.life_areas) {
      const allPlanets = new Set<string>();
      const allEngines = new Set<string>();
      let dasha: string | undefined;
      
      Object.values(deterministicInterpretation.life_areas).forEach((area: any) => {
        if (area.attribution) {
          area.attribution.planets?.forEach((p: string) => allPlanets.add(p));
          area.attribution.engines?.forEach((e: string) => allEngines.add(e));
          if (area.attribution.dasha && area.attribution.dasha !== "X") {
            dasha = area.attribution.dasha;
          }
        }
      });
      
      if (allPlanets.size > 0 || allEngines.size > 0 || dasha) {
        result.overview.attributionSummary = {
          activePlanets: Array.from(allPlanets),
          activeEngines: Array.from(allEngines),
        };
        if (dasha) {
          result.overview.attributionSummary.activeDasha = dasha;
        }
      }
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
    if (aiInterpretation.practices_and_reflection.reflection_guidance) {
      practices.reflectionGuidance = aiInterpretation.practices_and_reflection.reflection_guidance;
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

  if (showAttribution) {
    const allPlanets = new Set<string>();
    const allEngines = new Set<string>();
    let dasha: string | undefined;
    
    Object.values(aiInterpretation.life_areas).forEach((area: any) => {
      if (area.attribution) {
        area.attribution.planets?.forEach((p: string) => allPlanets.add(p));
        area.attribution.engines?.forEach((e: string) => allEngines.add(e));
        if (area.attribution.dasha && area.attribution.dasha !== "X") {
          dasha = area.attribution.dasha;
        }
      }
    });
    
    if (allPlanets.size > 0 || allEngines.size > 0 || dasha) {
      windowSummary.attributionSummary = {
        activePlanets: Array.from(allPlanets),
        activeEngines: Array.from(allEngines),
      };
      if (dasha) {
        windowSummary.attributionSummary.activeDasha = dasha;
      }
    }
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
  if (isV3Interpretation(obj)) {
    return true;
  }
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

export interface ExtractedInterpretation {
  primary: AIInterpretationV1 | AIInterpretationV2 | AIInterpretationV3;
  deterministic?: AIInterpretationV1;
}

export function extractAIInterpretation(details: any): AIInterpretationV1 | AIInterpretationV2 | AIInterpretationV3 | null {
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

export function extractInterpretationWithDeterministic(details: any): ExtractedInterpretation | null {
  if (!hasValidAIInterpretation(details)) {
    return null;
  }
  
  const llmInterp = details.interpretation.llm_interpretation;
  const aiInterp = details.interpretation.ai_interpretation;
  
  if (isValidInterpretationShape(llmInterp)) {
    return {
      primary: llmInterp,
      deterministic: isV1Interpretation(aiInterp) ? aiInterp : undefined,
    };
  }
  
  return {
    primary: aiInterp,
  };
}

export function adaptInterpretation(
  interpretation: AIInterpretationV1 | AIInterpretationV2 | AIInterpretationV3,
  level: ExplainabilityLevel = "full",
  deterministicInterpretation?: AIInterpretationV1
): PredictionViewModel {
  if (isV3Interpretation(interpretation)) {
    return adaptAIInterpretationV3(interpretation, level);
  }
  if (isV2Interpretation(interpretation)) {
    return adaptAIInterpretationV2(interpretation, level, deterministicInterpretation);
  }
  return adaptAIInterpretation(interpretation as AIInterpretationV1, level);
}
