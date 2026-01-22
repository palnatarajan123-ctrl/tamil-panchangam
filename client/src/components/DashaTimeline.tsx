interface Dasha {
  mahadasha?: string; // preferred
  lord?: string; // fallback
  start: string;
  end: string;
  is_partial?: boolean;
}

type ActiveDasha = {
  maha?: {
    lord?: string;
    start?: string;
    end?: string;
    is_partial?: boolean;
  };
  antar?: {
    lord?: string;
    start?: string;
    end?: string;
    confidence_weight?: number;
  } | null;
};

export function DashaTimeline({
  timeline,
  current,
}: {
  timeline?: Dasha[] | null;
  current?: ActiveDasha;
}) {
  if (!timeline || timeline.length === 0) return null;

  const activeMahaLord =
    (current as any)?.maha?.lord ??
    (current as any)?.lord ??
    null;

  const activeAntarLord =
    (current as any)?.antar?.lord ?? null;

  return (
    <div className="space-y-4">
      <h4 className="font-semibold">
        Lifetime Vimshottari Mahadasha periods (reference context)
      </h4>

      <div className="flex gap-3 overflow-x-auto pb-2">
        {timeline.map((dasha, i) => {
          const lord = dasha.mahadasha || dasha.lord || "—";
          const isActive = lord === activeMahaLord;

          return (
            <div
              key={i}
              className={`min-w-[200px] rounded-lg border p-3 text-center ${
                isActive
                  ? "bg-indigo-900/20 border-indigo-500"
                  : "bg-muted"
              }`}
            >
              <div className="font-medium">{lord} Mahadasha</div>

              <div className="text-xs text-muted-foreground mt-1">
                {dasha.start.slice(0, 4)} – {dasha.end.slice(0, 4)}
              </div>

              {/* Antar (only for active Maha) */}
              {isActive && activeAntarLord && (
                <div className="mt-2 text-xs text-indigo-300">
                  Antar: <strong>{activeAntarLord}</strong>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-muted-foreground">
        Predictions above interpret shorter time windows within this lifetime context.
      </p>
    </div>
  );
}
