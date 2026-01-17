// client/src/hooks/usePrediction.ts

import { useQuery } from "@tanstack/react-query";
import { adaptPrediction } from "@/adapters/predictionAdapter";

async function postPrediction(payload: any) {
  const res = await fetch("/api/ui/predictions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Prediction request failed");
  }

  return res.json();
}

export function usePrediction(
  baseChartId: string,
  timeframePayload: any,
) {
  return useQuery({
    queryKey: ["prediction", baseChartId, timeframePayload],
    queryFn: async () => {
      const raw = await postPrediction({
        base_chart_id: baseChartId,
        timeframe: timeframePayload,
      });
      return adaptPrediction(raw);
    },
    enabled: !!baseChartId,
  });
}
