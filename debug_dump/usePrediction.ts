import { useQuery } from "@tanstack/react-query";
import { adaptPredictionResponse } from "@/adapters/predictionAdapter";
import { PeriodType } from "@/types/prediction";

/* -------------------------------------------------
   Prediction Query Hook (LOCKED CONTRACT)
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

  return useQuery({
    queryKey: [
      "prediction",
      baseChartId,
      period,
      year,
      month,
      week,
    ],

    enabled: Boolean(baseChartId),

    staleTime: 1000 * 60 * 10, // 10 minutes

    queryFn: async () => {
      const res = await fetch(`/api/prediction/${period}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_chart_id: baseChartId,
          year,
          month,
          week,
        }),
      });

      if (!res.ok) {
        throw new Error("Prediction request failed");
      }

      return adaptPredictionResponse(await res.json());
    },
  });
}
