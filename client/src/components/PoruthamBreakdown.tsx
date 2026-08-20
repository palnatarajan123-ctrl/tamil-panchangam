// client/src/components/PoruthamBreakdown.tsx
// Shared Porutham score card + points breakdown, extracted from
// family-screen.tsx's PoruthTab (Phase F3/F4) so Phase G1's chart-to-chart
// prospect detail view can reuse the exact same presentation without
// duplicating the JSX -- family group Porutham (husband/wife) and prospect
// Porutham (boy/girl) render identically, only the person labels differ.

import { Heart, AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export interface PoruthPoint {
  name: string;
  score: number;
  max: number;
  pass: boolean;
  mandatory?: boolean;
}

export interface PoruthResult {
  total_score: number;
  max_score: number;
  percent: number;
  grade: string;
  mandatory_fail: boolean;
  points: PoruthPoint[];
  error?: string;
}

export interface PoruthamPerson {
  name?: string;
  nakshatra?: string;
  rasi?: string;
}

export function GradeTag({ grade, mandatoryFail }: { grade: string; mandatoryFail: boolean }) {
  const colors: Record<string, string> = {
    Excellent: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
    Good: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    Average: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    Poor: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    Unknown: "bg-gray-100 text-gray-600",
  };
  const label = mandatoryFail ? `${grade} (dosha)` : grade;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-sm font-medium ${colors[grade] ?? colors.Unknown}`}>
      {mandatoryFail && <AlertCircle className="h-3 w-3" />}
      {label}
    </span>
  );
}

export function PoruthamBreakdown({
  personA,
  personB,
  personALabel = "Person A",
  personBLabel = "Person B",
  result,
  commentary,
  context = "prospect",
}: {
  personA: PoruthamPerson;
  personB: PoruthamPerson;
  personALabel?: string;
  personBLabel?: string;
  result: PoruthResult;
  commentary?: string | null;
  context?: "family" | "prospect";
}) {
  return (
    <div className="space-y-4">
      {/* Header pair */}
      <div className="flex items-center gap-3 justify-center py-2">
        <div className="text-center">
          <p className="font-medium">{personA.name || personALabel}</p>
          <p className="text-xs text-muted-foreground">{personA.nakshatra} · {personA.rasi}</p>
        </div>
        <Heart className="h-5 w-5 text-rose-400" />
        <div className="text-center">
          <p className="font-medium">{personB.name || personBLabel}</p>
          <p className="text-xs text-muted-foreground">{personB.nakshatra} · {personB.rasi}</p>
        </div>
      </div>

      {/* Score card */}
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="text-3xl font-bold">{result.total_score}</span>
              <span className="text-muted-foreground text-sm"> / {result.max_score}</span>
            </div>
            <GradeTag grade={result.grade} mandatoryFail={result.mandatory_fail} />
          </div>
          {/* Family-context-only softening (2026-08-20): the "(dosha)"
              badge alone can read as an alarming verdict for a couple
              already married, sometimes decades. Doesn't touch the badge
              itself (color/score/wording) -- just adds adjacent context
              pointing at the commentary below. Prospect context is
              unchanged; this is deliberately not shown there. */}
          {context === "family" && result.mandatory_fail && (
            <p className="text-xs text-muted-foreground mb-2">
              Traditional screening flag — see note below
            </p>
          )}
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${result.percent}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground mt-1">{result.percent}%</p>
        </CardContent>
      </Card>

      {/* Commentary (Phase H2) -- LLM-generated explanation of the
          mechanism behind the grade, cached at compute time alongside
          the score. Older cached rows predating this field simply won't
          have it -- render nothing rather than backfilling on read. */}
      {commentary && (
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-primary">✦</span>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              About This Result
            </p>
          </div>
          <p className="text-sm text-foreground leading-relaxed">
            {commentary}
          </p>
        </div>
      )}

      {/* Points breakdown */}
      <div className="space-y-1">
        {result.points.map((pt) => (
          <div key={pt.name} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
            <div className="flex items-center gap-2">
              {pt.mandatory && !pt.pass ? (
                <XCircle className="h-4 w-4 text-destructive flex-shrink-0" />
              ) : pt.pass ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              )}
              <span className="text-sm">{pt.name}</span>
              {pt.mandatory && (
                <span className="text-xs text-muted-foreground">(mandatory)</span>
              )}
            </div>
            <span className="text-sm font-medium tabular-nums">
              {pt.max > 0 ? `${pt.score}/${pt.max}` : (pt.pass ? "✓" : "✗")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
