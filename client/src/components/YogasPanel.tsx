import { Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { BirthChartUIModel } from "@/adapters/birthChartAdapter";

type Yoga = NonNullable<BirthChartUIModel["yogas"]>["yogas"][number];

// ─── Grouping ──────────────────────────────────────────────────────────────

const GROUPS: { label: string; match: (y: Yoga) => boolean }[] = [
  {
    label: "Raja & Authority Yogas",
    match: (y) =>
      y.name === "Raja Yoga" ||
      y.name === "Neecha Bhanga Raja Yoga" ||
      y.name === "Harsha Yoga" ||
      y.name === "Sarala Yoga" ||
      y.name === "Vimala Yoga" ||
      (y.category ?? "").includes("Viparita"),
  },
  {
    label: "Pancha Mahapurusha",
    match: (y) =>
      (y.category ?? "") === "Pancha Mahapurusha" ||
      ["Ruchaka", "Bhadra", "Hamsa", "Malavya", "Shasha"].some((n) =>
        y.name.includes(n)
      ),
  },
  {
    label: "Prosperity Yogas",
    match: (y) =>
      y.name === "Dhana Yoga" || y.name === "Chandra-Mangala Yoga",
  },
  {
    label: "Intellect & Character",
    match: (y) =>
      y.name === "Gaja Kesari Yoga" || y.name === "Budhaditya Yoga",
  },
  {
    label: "Challenging Yogas",
    match: (y) =>
      y.name === "Kemadruma Yoga" ||
      (y.category ?? "") === "Challenging Yoga",
  },
];

function groupYogas(yogas: Yoga[]): { label: string; yogas: Yoga[] }[] {
  const result: { label: string; yogas: Yoga[] }[] = [];
  const assigned = new Set<number>();

  for (const group of GROUPS) {
    const matched = yogas.filter((y, i) => {
      if (assigned.has(i)) return false;
      if (group.match(y)) {
        assigned.add(i);
        return true;
      }
      return false;
    });
    if (matched.length > 0) {
      result.push({ label: group.label, yogas: matched });
    }
  }

  // Any unmatched go into a catch-all
  const rest = yogas.filter((_, i) => !assigned.has(i));
  if (rest.length > 0) {
    result.push({ label: "Other Yogas", yogas: rest });
  }

  return result;
}

// ─── Strength Badge ────────────────────────────────────────────────────────

function StrengthBadge({ strength }: { strength: string }) {
  const cls =
    strength === "very strong"
      ? "bg-purple-600/20 text-purple-400 border-purple-500/30"
      : strength === "strong"
      ? "bg-green-600/20 text-green-400 border-green-500/30"
      : "bg-amber-600/20 text-amber-400 border-amber-500/30";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {strength}
    </span>
  );
}

// ─── Single Yoga Card ──────────────────────────────────────────────────────

function YogaCard({ yoga, isChallenging }: { yoga: Yoga; isChallenging: boolean }) {
  return (
    <div
      className={`rounded-lg border p-3 space-y-1.5 ${
        isChallenging
          ? "border-amber-500/20 bg-amber-500/5"
          : "border-border bg-muted/30"
      }`}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`font-semibold text-sm ${isChallenging ? "text-amber-400" : ""}`}>
          {yoga.name}
        </span>
        <StrengthBadge strength={yoga.strength} />
      </div>

      {yoga.effects.slice(0, 3).length > 0 && (
        <ul className="space-y-0.5">
          {yoga.effects.slice(0, 3).map((effect, i) => (
            <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
              <span className="mt-0.5 shrink-0">•</span>
              <span>{effect}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-muted-foreground/70 italic">{yoga.rationale}</p>
    </div>
  );
}

// ─── Panel ─────────────────────────────────────────────────────────────────

export function YogasPanel({ yogas }: { yogas: BirthChartUIModel["yogas"] }) {
  const list = yogas?.yogas?.filter((y) => y.present) ?? [];
  const groups = groupYogas(list);

  return (
    <Card className="border-muted">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          Detected Yogas
        </CardTitle>
      </CardHeader>

      <CardContent>
        {list.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No significant yogas detected in this chart.
          </p>
        ) : (
          <div className="space-y-5">
            {groups.map((group) => {
              const isChallenging = group.label === "Challenging Yogas";
              return (
                <div key={group.label}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    {group.label}
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {group.yogas.map((yoga, i) => (
                      <YogaCard key={i} yoga={yoga} isChallenging={isChallenging} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
