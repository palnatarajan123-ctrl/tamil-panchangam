export function ToneBadge({ score }: { score: number }) {
  let color = "bg-gray-400";
  let label = "Neutral";

  if (score >= 30) {
    color = "bg-green-500";
    label = "Supportive";
  } else if (score <= -30) {
    color = "bg-red-500";
    label = "Caution";
  }

  return (
    <span className={`text-xs px-2 py-1 rounded-full text-white ${color}`}>
      {label}
    </span>
  );
}
