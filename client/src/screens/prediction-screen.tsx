// client/src/pages/prediction-screen.tsx

import { useParams } from "wouter";
import { useState } from "react";
import { usePrediction } from "@/hooks/usePrediction";

import { MonthlyPredictionView } from "@/components/prediction/MonthlyPredictionView";
import { ExplainabilityDrawer } from "@/components/prediction/ExplainabilityDrawer";
import { AntarExplanationCard } from "@/components/prediction/AntarExplanationCard";
import { AntarRemediesCard } from "@/components/prediction/AntarRemediesCard";
import { DashaTimeline } from "@/components/DashaTimeline";

import { adaptMonthlyPrediction } from "@/adapters/predictionAdapter";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

import { Separator } from "@/components/ui/separator";
import { NarrativeCard } from "@/components/prediction/NarrativeCard";
import { Download } from "lucide-react";

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
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [week, setWeek] = useState(
    (() => {
      const d = new Date();
      const day = d.getUTCDay() || 7;
      d.setUTCDate(d.getUTCDate() + 4 - day);
      const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
      return Math.ceil(
        (((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7
      );
    })()
  );

  const { data, isLoading, error } = usePrediction({
    baseChartId: id,
    period,
    year,
    month: period === "monthly" ? month : undefined,
    week: period === "weekly" ? week : undefined,
  });

  const dashaContext = data?.details?.envelope?.dasha_context;

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Time Controls */}
      <div className="flex gap-2">
        {period === "monthly" && (
          <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Month" />
            </SelectTrigger>
            <SelectContent>
              {Array.from({ length: 12 }).map((_, i) => (
                <SelectItem key={i + 1} value={String(i + 1)}>
                  {new Date(0, i).toLocaleString("default", { month: "short" })}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="w-[90px]">
            <SelectValue placeholder="Year" />
          </SelectTrigger>
          <SelectContent>
            {Array.from({ length: 10 }).map((_, i) => {
              const y = baseYear + i;
              return (
                <SelectItem key={y} value={String(y)}>
                  {y}
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      </div>

      {isLoading && <div>Computing prediction…</div>}
      {error && <div className="text-red-600">{error.message}</div>}

      {data && (
        <>
          {/* Download Full Report */}
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

          <MonthlyPredictionView
            prediction={adaptMonthlyPrediction(data.details)}
          />

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
