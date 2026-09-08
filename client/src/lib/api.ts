// src/lib/api.ts

import { apiRequest } from "@/lib/queryClient";

export async function fetchMonthlyUIReport(
  baseChartId: string,
  year: number,
  month: number
) {
  const params = new URLSearchParams({
    base_chart_id: baseChartId,
    year: String(year),
    month: String(month),
  });

  // /api/ui/monthly-report now requires auth (security fix, 2026-09-08) --
  // use the shared apiRequest helper. (Currently unreferenced elsewhere in
  // the app, but fixed for consistency per this session's whole-tree audit.)
  const res = await apiRequest("GET", `/api/ui/monthly-report?${params.toString()}`);

  if (!res.ok) {
    throw new Error("Failed to load monthly UI report");
  }

  return res.json();
}
