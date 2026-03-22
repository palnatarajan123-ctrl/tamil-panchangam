export function aggregateInterpretation(areas: Record<string, any>) {
  const positives: string[] = [];
  const cautions: string[] = [];

  Object.entries(areas).forEach(([area, data]) => {
    if (data.tone === "positive") positives.push(area);
    if (data.tone === "caution") cautions.push(area);
  });

  let summary = "";

  if (positives.length) {
    summary += `This month supports progress in ${positives.join(", ")}. `;
  }

  if (cautions.length) {
    summary += `Extra care is advised in ${cautions.join(", ")}.`;
  }

  if (!summary) {
    summary =
      "This month remains largely stable, with no strong accelerators or obstacles.";
  }

  return summary;
}
