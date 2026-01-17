// src/lib/api.ts

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

  const res = await fetch(`/api/ui/monthly-report?${params.toString()}`);

  if (!res.ok) {
    throw new Error("Failed to load monthly UI report");
  }

  return res.json();
}
