export function ScoreBar({ score }: { score: number }) {
  const percentage = Math.min(Math.abs(score), 100);

  return (
    <div className="relative h-2 bg-gray-200 rounded">
      <div
        className={`absolute top-0 h-2 rounded ${
          score >= 0 ? "bg-green-400" : "bg-red-400"
        }`}
        style={{
          width: `${percentage}%`,
          left: score >= 0 ? "50%" : `${50 - percentage}%`,
        }}
      />
      <div className="absolute left-1/2 top-0 h-2 w-px bg-gray-500" />
    </div>
  );
}
