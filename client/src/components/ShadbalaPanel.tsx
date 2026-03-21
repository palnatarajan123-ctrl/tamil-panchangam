import { useState } from "react";
import { Scale, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BirthChartUIModel } from "@/adapters/birthChartAdapter";

type ShadbalaData = NonNullable<BirthChartUIModel["shadbala"]>;
type PlanetData = ShadbalaData["planets"][string];

// ── Constants ──────────────────────────────────────────────────────────────

const PLANET_ORDER = [
  "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
];

const PLANET_SYMBOL: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mars: "♂", Mercury: "☿",
  Jupiter: "♃", Venus: "♀", Saturn: "♄",
};

const STRENGTH_COLOR: Record<string, string> = {
  "Very Strong": "bg-purple-500",
  "Strong":      "bg-green-500",
  "Moderate":    "bg-amber-500",
  "Weak":        "bg-red-500",
};

const STRENGTH_TEXT: Record<string, string> = {
  "Very Strong": "text-purple-400",
  "Strong":      "text-green-400",
  "Moderate":    "text-amber-400",
  "Weak":        "text-red-400",
};

const PLACEMENT_LABELS: Record<string, string> = {
  exaltation:    "Exalt",
  debilitation:  "Debil",
  own_sign:      "Own",
  friendly_sign: "Friendly",
  neutral_sign:  "Neutral",
};

const COMPONENT_LABELS: Array<{ key: string; label: string }> = [
  { key: "sthana_bala",    label: "Sthana" },
  { key: "dig_bala",       label: "Dig" },
  { key: "chesta_bala",    label: "Chesta" },
  { key: "naisargika_bala", label: "Naisargika" },
  { key: "drik_bala",      label: "Drik" },
];

// ── Sub-components ──────────────────────────────────────────────────────────

function PlacementBadge({ placement }: { placement: string }) {
  if (!placement || placement === "neutral_sign") return null;
  const isGood = ["exaltation", "own_sign", "friendly_sign"].includes(placement);
  const label = PLACEMENT_LABELS[placement] ?? placement;
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
      isGood
        ? "border-green-500/40 bg-green-500/10 text-green-400"
        : "border-red-500/40 bg-red-500/10 text-red-400"
    }`}>
      {label}
    </span>
  );
}

function RetrogradeBadge() {
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded border border-amber-500/40 bg-amber-500/10 text-amber-400">
      ℞
    </span>
  );
}

function ComponentBars({ components }: { components: PlanetData["components"] }) {
  return (
    <div className="mt-3 space-y-1.5 pl-2 border-l border-border/40">
      {COMPONENT_LABELS.map(({ key, label }) => {
        const comp = (components as Record<string, { score: number }>)[key];
        const score = comp?.score ?? 0;
        const pct = Math.round((score / 60) * 100);
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="text-[10px] text-muted-foreground w-20 shrink-0">{label}</span>
            <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary/50 rounded-full"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-[10px] text-muted-foreground w-7 text-right">{score.toFixed(0)}</span>
          </div>
        );
      })}
    </div>
  );
}

function PlanetRow({
  planet,
  data,
}: {
  planet: string;
  data: PlanetData;
}) {
  const [expanded, setExpanded] = useState(false);
  const barColor = STRENGTH_COLOR[data.strength_label] ?? "bg-muted";
  const textColor = STRENGTH_TEXT[data.strength_label] ?? "text-muted-foreground";
  const pct = data.percent_strength;
  const placement = data.components.sthana_bala.placement;

  return (
    <div className="space-y-1">
      <div
        className="flex items-center gap-2 cursor-pointer group"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Planet name + badges — fixed left column */}
        <div className="flex items-center gap-1 shrink-0 min-w-[180px]">
          <span className="text-sm opacity-70 shrink-0">{PLANET_SYMBOL[planet]}</span>
          <span className="text-xs font-medium shrink-0">{planet}</span>
          {data.is_retrograde && <RetrogradeBadge />}
          <PlacementBadge placement={placement} />
        </div>

        {/* Bar — flexible middle, min-w-0 prevents overflow */}
        <div className="flex-1 min-w-0 h-2.5 bg-muted/30 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${barColor} transition-all`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Label + value — fixed right column */}
        <div className="flex items-center gap-1.5 w-32 shrink-0 justify-end">
          <span className={`text-[10px] font-medium ${textColor}`}>
            {data.strength_label}
          </span>
          <span className="text-[10px] text-muted-foreground">
            {data.rupas.toFixed(2)}R
          </span>
          {expanded
            ? <ChevronUp className="h-3 w-3 text-muted-foreground" />
            : <ChevronDown className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100" />
          }
        </div>
      </div>

      {expanded && <ComponentBars components={data.components} />}
    </div>
  );
}

// ── Panel ───────────────────────────────────────────────────────────────────

export function ShadbalaPanel({
  shadbala,
}: {
  shadbala: BirthChartUIModel["shadbala"];
}) {
  if (!shadbala || shadbala.error || !shadbala.planets) return null;

  const planets = shadbala.planets;
  const summary = shadbala.summary;

  return (
    <Card className="border-muted">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="h-4 w-4 text-primary" />
          Planetary Strength (Shadbala)
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {PLANET_ORDER.map((planet) => {
          const data = planets[planet];
          if (!data) return null;
          return <PlanetRow key={planet} planet={planet} data={data} />;
        })}

        {/* Summary footer */}
        {(summary.strongest || summary.weakest) && (
          <div className="pt-2 border-t border-border/40 flex items-center gap-4 text-xs text-muted-foreground">
            {summary.strongest && (
              <span>
                Strongest:{" "}
                <span className="font-medium text-purple-400">{summary.strongest}</span>
              </span>
            )}
            {summary.weakest && (
              <span>
                Weakest:{" "}
                <span className="font-medium text-red-400">{summary.weakest}</span>
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
