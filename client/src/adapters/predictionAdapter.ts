// client/src/adapters/predictionAdapter.ts

import { PredictionUIModel } from "@/models/prediction";

export function adaptPrediction(raw: any): PredictionUIModel {
  if (!raw) {
    throw new Error("Invalid prediction response");
  }

  return {
    baseChartId: raw.base_chart_id,
    asOf: raw.as_of,

    period: {
      type: raw.period.type,
      startDate: raw.period.start_date,
      endDate: raw.period.end_date,
      label: raw.period.label,
    },

    dashaContext: {
      system: raw.dasha_context.system,
      active: {
        maha: raw.dasha_context.active.maha,
        antara: raw.dasha_context.active.antara,
        pratyantara: raw.dasha_context.active.pratyantara ?? undefined,
      },
      overlap: {
        coverageRatio: raw.dasha_context.overlap.coverage_ratio,
        dominantSegment: raw.dasha_context.overlap.dominant_segment,
      },
    },

    gates: {
      eligible: raw.prediction.gates.eligible,
      reasons: raw.prediction.gates.reasons ?? [],
    },

    confidence: {
      score: raw.prediction.confidence.score,
      band: raw.prediction.confidence.band,
      signals: raw.prediction.confidence.signals ?? [],
      notes: raw.prediction.confidence.notes ?? [],
    },

    timeline: (raw.prediction.timeline ?? []).map((t: any) => ({
      start: t.start,
      end: t.end,
      strength: t.strength,
      tags: t.tags ?? [],
    })),
  };
}
