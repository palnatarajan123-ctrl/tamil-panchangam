interface PakshiProps {
  dominant_pakshi: string;
  recommended: string[];
  avoid: string[];
}

export function PakshiPanel({ pakshi }: { pakshi: PakshiProps }) {
  return (
    <div className="rounded-xl bg-emerald-50 p-5">
      <h4 className="font-semibold mb-2">
        Pancha Pakshi — {pakshi.dominant_pakshi}
      </h4>

      <div className="grid md:grid-cols-2 gap-4 text-sm">
        <div>
          <h5 className="font-medium mb-1">Favorable</h5>
          <ul className="list-disc pl-4">
            {pakshi.recommended.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>

        <div>
          <h5 className="font-medium mb-1">Avoid</h5>
          <ul className="list-disc pl-4">
            {pakshi.avoid.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      </div>

      <p className="text-xs text-gray-600 mt-3">
        Pancha Pakshi guidance is for timing harmony, not deterministic outcomes.
      </p>
    </div>
  );
}
