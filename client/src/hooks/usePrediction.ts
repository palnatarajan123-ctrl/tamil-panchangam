import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
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
      // Monthly/weekly/yearly prediction endpoints now require auth
      // (security fix, 2026-09-08) -- use the shared apiRequest helper so
      // the bearer token is attached, instead of a bare fetch() that would
      // 401. Same bug class as DailyView.tsx and getQueryFn, a third
      // instance found in production post-deploy testing.
      const res = await apiRequest("POST", endpoint, payload);

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Prediction request failed");
      }

      const json = await res.json();
      return adaptPredictionResponse(json);
    },
  });
}
