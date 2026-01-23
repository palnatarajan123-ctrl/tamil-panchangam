import { useParams } from "wouter";
import { useState, useEffect } from "react";
import { usePrediction } from "@/hooks/usePrediction";

import { MonthlyPredictionView } from "@/components/prediction/MonthlyPredictionView";
import { ExplainabilityDrawer } from "@/components/prediction/ExplainabilityDrawer";
import { AntarExplanationCard } from "@/components/prediction/AntarExplanationCard";
import { AntarRemediesCard } from "@/components/prediction/AntarRemediesCard";
import { NarrativeCard } from "@/components/prediction/NarrativeCard";
import { DashaTimeline } from "@/components/DashaTimeline";

import { PredictionTimelineControl } from "@/components/prediction/PredictionTimelineControl";

import {
  adaptAIInterpretation,
  extractAIInterpretation,
  hasValidAIInterpretation,
  type PredictionViewModel,
} from "@/adapters/aiInterpretationAdapter";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Download } from "lucide-react";

/* -------------------------------------------------
   Helpers
-------------------------------------------------- */

// ISO week number (UTC-safe, deterministic)
function getCurrentISOWeek(): number {
  const d = new Date();
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(
    (((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7
  );
}

/* -------------------------------------------------
   Screen
-------------------------------------------------- */

export default function PredictionScreen() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <div>Missing base chart id</div>;

  const now = new Date();
  const baseYear = now.getFullYear();

  const [period, setPeriod] = useState<"monthly" | "weekly" | "yearly">("monthly");
  const [year, setYear] = useState(baseYear);

  /**
   * Unified cursor:
   * - monthly → month (1–12)
   * - weekly  → ISO week (1–53)
   * - yearly  → always 1
   */
  const [index, setIndex] = useState<number>(now.getMonth() + 1);

  /* -------------------------------------------------
     Keep cursor aligned when period changes
  -------------------------------------------------- */
  useEffect(() => {
    if (period === "monthly") {
      setIndex(now.getMonth() + 1);
    } else if (period === "weekly") {
      setIndex(getCurrentISOWeek());
    } else {
      setIndex(1);
    }
    setYear(baseYear);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  const { data, isLoading, error } = usePrediction({
    baseChartId: id,
    period,
    year,
    month: period === "monthly" ? index : undefined,
    week: period === "weekly" ? index : undefined,
  });

  const dashaContext = data?.details?.envelope?.dasha_context;

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------
          Header
      -------------------------------------------------- */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold capitalize">
          {period} Predictions
        </h1>

        <div className="flex gap-2">
          {(["monthly", "weekly", "yearly"] as const).map((p) => (
            <Button
              key={p}
              variant={period === p ? "default" : "ghost"}
              onClick={() => setPeriod(p)}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {/* -------------------------------------------------
          Unified Timeline Control
      -------------------------------------------------- */}
      <PredictionTimelineControl
        period={period}
        year={year}
        index={index}
        onChange={({ year, index }) => {
          setYear(year);
          setIndex(index);
        }}
      />

      {isLoading && <div>Computing prediction…</div>}
      {error && <div className="text-red-600">{error.message}</div>}

      {data && (
        <>
          {/* -------------------------------------------------
              Download
          -------------------------------------------------- */}
          <Button
            variant="outline"
            className="gap-2"
            onClick={() =>
              window.open(
                `/api/reports/prediction/${id}/${year}/full-report/pdf`,
                "_blank"
              )
            }
          >
            <Download className="h-4 w-4" />
            Download Full Report (PDF)
          </Button>

          <Separator className="my-4" />

          {/* -------------------------------------------------
              Prediction Body
          -------------------------------------------------- */}
          {hasValidAIInterpretation(data) && (
            <MonthlyPredictionView
              prediction={adaptAIInterpretation(extractAIInterpretation(data)!)}
              period={period}
            />
          )}

          {dashaContext?.active?.antar && (
            <>
              <Separator className="my-6" />
              <AntarExplanationCard antar={dashaContext.active.antar} />
            </>
          )}

          {data?.details?.envelope?.narrative && (
            <>
              <Separator className="my-6" />
              <NarrativeCard narrative={data.details.envelope.narrative} />
            </>
          )}

          {dashaContext?.antar_explanation?.remedies && (
            <>
              <Separator className="my-6" />
              <AntarRemediesCard
                remedies={dashaContext.antar_explanation.remedies}
                cautionLevel={dashaContext.antar_explanation.caution_level}
              />
            </>
          )}

          <ExplainabilityDrawer explainability={data.explainability} />

          {dashaContext?.timeline && (
            <>
              <Separator className="my-10" />
              <Card className="border-dashed bg-muted/40">
                <CardHeader>
                  <CardTitle className="text-base">
                    Lifetime Context · Vimshottari Dasha
                  </CardTitle>
                  <CardDescription>
                    Long-term planetary periods derived from your birth chart.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DashaTimeline
                    timeline={dashaContext.timeline}
                    current={dashaContext.active}
                  />
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
}
