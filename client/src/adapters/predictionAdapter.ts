// client/src/adapters/predictionAdapter.ts
// 
// DEPRECATED: This adapter is retained for backward compatibility only.
// All new prediction UI code should use aiInterpretationAdapter.ts instead.
// 
// The AI Interpretation Engine v1.0 is now the single source of truth
// for all prediction text content.

import { PredictionUIModel } from "@/models/prediction";
import { PredictionResponse } from "@/types/prediction";

export function adaptPrediction(raw: any): PredictionUIModel {
  throw new Error(
    "DEPRECATED: Use aiInterpretationAdapter.adaptAIInterpretation() instead. " +
    "This legacy adapter has been replaced."
  );
}

export function adaptPredictionResponse(
  data: any
): PredictionResponse {
  return data;
}

export function adaptMonthlyPrediction(details: any) {
  throw new Error(
    "DEPRECATED: Use aiInterpretationAdapter.adaptAIInterpretation() instead. " +
    "The legacy monthly prediction adapter has been replaced."
  );
}
