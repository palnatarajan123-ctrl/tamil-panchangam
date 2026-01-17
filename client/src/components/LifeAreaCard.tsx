import { ToneBadge } from "./ToneBadge";
import { ScoreBar } from "./ScoreBar";

interface Props {
  area: string;
  score: number;
  confidence: number;
  sentiment: string;
  summary: string;
  onExplain?: () => void;
}

export function LifeAreaCard({
  area,
  score,
  confidence,
  sentiment,
  summary,
  onExplain,
}: Props) {
  return (
    <div
      className="rounded-xl border p-4 transition hover:shadow-md cursor-pointer"
      style={{ opacity: 0.5 + confidence * 0.5 }}
      onClick={onExplain}
    >
      <div className="flex justify-between items-center mb-2">
        <h3 className="capitalize font-semibold">{area}</h3>
        <ToneBadge score={score} />
      </div>

      <ScoreBar score={score} />

      <p className="text-sm mt-3 text-gray-700 line-clamp-2">
        {summary}
      </p>

      <div className="mt-2 text-xs text-gray-500">
        Sentiment: {sentiment}
      </div>
    </div>
  );
}
