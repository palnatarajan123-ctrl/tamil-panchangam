import { useState } from "react";

/* -------------------------------------------------------
   Classical one-line interpretations per Mahadasha lord
------------------------------------------------------- */
const DASHA_MEANINGS: Record<string, string> = {
  Sun:     "Authority, vitality, government, father",
  Moon:    "Mind, emotions, mother, nourishment",
  Mars:    "Energy, courage, property, siblings",
  Mercury: "Intelligence, commerce, communication",
  Jupiter: "Wisdom, expansion, dharma, teachers",
  Venus:   "Relationships, arts, wealth, comfort",
  Saturn:  "Karma, discipline, delay, structure",
  Rahu:    "Ambition, foreign, unconventional paths",
  Ketu:    "Spirituality, detachment, past karma",
};

/* -------------------------------------------------------
   Planet color coding
------------------------------------------------------- */
const PLANET_COLORS: Record<string, string> = {
  Sun:     "border-amber-500 bg-amber-900/20",
  Moon:    "border-slate-400 bg-slate-800/20",
  Mars:    "border-red-500 bg-red-900/20",
  Mercury: "border-green-500 bg-green-900/20",
  Jupiter: "border-yellow-500 bg-yellow-900/20",
  Venus:   "border-pink-500 bg-pink-900/20",
  Saturn:  "border-blue-500 bg-blue-900/20",
  Rahu:    "border-purple-500 bg-purple-900/20",
  Ketu:    "border-orange-500 bg-orange-900/20",
};

const ACTIVE_COLORS: Record<string, string> = {
  Sun:     "border-amber-400 bg-amber-900/40 ring-1 ring-amber-400",
  Moon:    "border-slate-300 bg-slate-700/40 ring-1 ring-slate-300",
  Mars:    "border-red-400 bg-red-900/40 ring-1 ring-red-400",
  Mercury: "border-green-400 bg-green-900/40 ring-1 ring-green-400",
  Jupiter: "border-yellow-400 bg-yellow-900/40 ring-1 ring-yellow-400",
  Venus:   "border-pink-400 bg-pink-900/40 ring-1 ring-pink-400",
  Saturn:  "border-blue-400 bg-blue-900/40 ring-1 ring-blue-400",
  Rahu:    "border-purple-400 bg-purple-900/40 ring-1 ring-purple-400",
  Ketu:    "border-orange-400 bg-orange-900/40 ring-1 ring-orange-400",
};

/* -------------------------------------------------------
   Types
------------------------------------------------------- */
interface Dasha {
  mahadasha?: string;
  lord?: string;
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

/* -------------------------------------------------------
   Component
------------------------------------------------------- */
export function DashaTimeline({
  timeline,
  current,
}: {
  timeline?: Dasha[] | null;
  current?: ActiveDasha;
}) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!timeline || timeline.length === 0) return null;

  const activeMahaLord =
    (current as any)?.maha?.lord ?? (current as any)?.lord ?? null;
  const activeAntarLord = (current as any)?.antar?.lord ?? null;

  return (
    <div className="space-y-4">
      <h4 className="font-semibold">
        Lifetime Vimshottari Mahadasha periods (reference context)
      </h4>

      <div className="flex gap-3 overflow-x-auto pb-2">
        {timeline.map((dasha, i) => {
          const lord = dasha.mahadasha || dasha.lord || "—";
          const isActive = lord === activeMahaLord;
          const isExpanded = expanded === i;
          const meaning = DASHA_MEANINGS[lord];
          const colorClass = isActive
            ? ACTIVE_COLORS[lord] ?? "border-indigo-500 bg-indigo-900/40 ring-1 ring-indigo-400"
            : PLANET_COLORS[lord] ?? "border-muted bg-muted";

          return (
            <div
              key={i}
              className={`min-w-[200px] rounded-lg border p-3 text-center cursor-pointer transition-all ${colorClass}`}
              onClick={() => setExpanded(isExpanded ? null : i)}
            >
              <div className="flex items-center justify-center gap-2">
                <span className="font-medium">{lord} Mahadasha</span>
                {isActive && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-white/10 text-white">
                    ACTIVE
                  </span>
                )}
              </div>

              <div className="text-xs text-muted-foreground mt-1">
                {dasha.start.slice(0, 4)} – {dasha.end.slice(0, 4)}
              </div>

              {/* Antar (only for active Maha) */}
              {isActive && activeAntarLord && (
                <div className="mt-2 text-xs text-indigo-300">
                  Antar: <strong>{activeAntarLord}</strong>
                </div>
              )}

              {/* Expanded detail */}
              {isExpanded && (
                <div className="mt-3 text-left border-t border-white/10 pt-2 space-y-1">
                  {meaning && (
                    <p className="text-xs text-muted-foreground italic">{meaning}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {dasha.start.slice(0, 10)} → {dasha.end.slice(0, 10)}
                  </p>
                  {dasha.is_partial && (
                    <p className="text-xs text-amber-400">Partial period</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-muted-foreground">
        Tap a period for details. Predictions above interpret shorter windows within this lifetime context.
      </p>
    </div>
  );
}
