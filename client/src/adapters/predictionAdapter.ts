// client/src/adapters/predictionAdapter.ts

import { PredictionUIModel } from "@/models/prediction";
import { PredictionResponse } from "@/types/prediction";

/* =====================================================
   FUTURE / GENERIC PREDICTION ADAPTER (NOT WIRED YET)
===================================================== */
export function adaptPrediction(raw: any): PredictionUIModel {
  throw new Error(
    "adaptPrediction is not wired to the current backend schema. " +
    "Use adaptMonthlyPrediction(details) instead."
  );
}

/* =====================================================
   PASS-THROUGH (LEGACY SAFE)
===================================================== */
export function adaptPredictionResponse(
  data: any
): PredictionResponse {
  return data;
}

/* =====================================================
   MONTHLY PREDICTION → UI READ MODEL (EPIC-10 FINAL)
===================================================== */
export function adaptMonthlyPrediction(details: any) {
  if (!details) {
    throw new Error("Missing prediction details");
  }

  /* ---------- 🔍 DEBUG START ---------- */
  console.log("🧠 PREDICTION DETAILS:", details);
  console.log("🧠 DETAILS.INTERPRETATION:", details?.interpretation);
  console.log(
    "🧠 DETAILS.INTERPRETATION.INTERPRETATION:",
    details?.interpretation?.interpretation
  );
  /* ---------- 🔍 DEBUG END ---------- */

  /* ---------- LIFE AREAS ---------- */

  /* ---------- LIFE AREAS ---------- */

  const synthesis = details?.synthesis?.life_areas ?? {};
  const interpretation =
    details?.interpretation?.interpretation ?? {};

  const life_areas = Object.keys(synthesis).map((key) => {
    const synth = synthesis[key];
    const interp = interpretation[key];

    return {
      key,
      label: key
        .replace("_", " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),

      score: synth.score,
      confidence: synth.confidence,

      sentiment:
        synth.score >= 65 ? "Positive" :
        synth.score >= 45 ? "Mixed" :
        "Challenging",

      // ✅ FIXED: aligned with backend schema (summary, confidence_explanation)
      summary: interp?.summary ?? "No summary available.",
  
      detail:
        interp?.confidence_explanation ??
        interp?.summary ??
        "Detailed interpretation not available.",
      };
  });

  /* ---------- MONTHLY PANCHA PAKSHI (EXPLANATORY ONLY) ---------- */

  return {
    meta: {
      generated_at: details.generated_at,
      engine_version: details.synthesis?.engine_version,
      period_label: "Monthly Prediction",
    },

    overview: {
      headline: "Overall monthly influence summary",
      overall_score:
        life_areas.length > 0
          ? Math.round(
              life_areas.reduce((a, b) => a + b.score, 0) /
                life_areas.length
            )
          : undefined,

      confidence: details.synthesis?.confidence?.overall,
      tone: "Balanced",
    },

    life_areas,

    timing: {
      dominant_pakshi: undefined, // ✅ intentionally absent for monthly
      recommended: [],
      avoid: [],
      note:
        "Pancha Pakshi influence is calculated on a daily basis. " +
        "Monthly predictions describe overall rhythm rather than a single Pakshi. " +
        "Please refer to Daily or Weekly predictions for favorable days and precise timing.",
    },

    disclaimers: [
      details.interpretation?.note,
      "Astrological guidance is indicative, not deterministic.",
    ].filter(Boolean),
  };
}
