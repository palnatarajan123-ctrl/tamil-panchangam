import { useQuery } from "@tanstack/react-query";
import { adaptPredictionResponse } from "@/adapters/predictionAdapter";
import { PeriodType } from "@/types/prediction";

/* -------------------------------------------------
   Prediction Query Hook (LOCKED CONTRACT)
   PURPOSE:
   - Reads predictions via ENGINE endpoints
   - NEVER calls /api/ui/*
-------------------------------------------------- */

interface UsePredictionParams {
  baseChartId: string;
  period: PeriodType; // "monthly" | "weekly" | "yearly"
  year: number;
  month?: number;
  week?: number;
}

export function usePrediction(params: UsePredictionParams) {
  const { baseChartId, period, year, month, week } = params;

  // -----------------------------
  // Endpoint selection
  // -----------------------------
  const endpoint =
    period === "monthly"
      ? "/api/prediction/monthly"
      : period === "weekly"
      ? "/api/prediction/weekly"
      : "/api/prediction/yearly";

  // -----------------------------
  // Payload construction
  // -----------------------------
  const payload: any = {
    base_chart_id: baseChartId,
    year,
  };

  if (period === "monthly") {
    payload.month = month;
  }

  if (period === "weekly") {
    payload.week = week;
  }

  // -----------------------------
  // Query
  // -----------------------------
  return useQuery({
    queryKey: ["prediction", baseChartId, period, year, month, week],
    enabled: Boolean(baseChartId && period),

    queryFn: async () => {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Prediction request failed");
      }

      const json = await res.json();
      return adaptPredictionResponse(json);
    },
  });
}
