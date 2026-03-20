import { useParams } from "wouter";
import { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { usePrediction } from "@/hooks/usePrediction";

import { MonthlyPredictionView } from "@/components/prediction/MonthlyPredictionView";
import { ExplainabilityDrawer } from "@/components/prediction/ExplainabilityDrawer";
import { AntarExplanationCard } from "@/components/prediction/AntarExplanationCard";
import { DashaTimeline } from "@/components/DashaTimeline";

import { PredictionTimelineControl } from "@/components/prediction/PredictionTimelineControl";

import {
  adaptInterpretation,
  extractInterpretationWithDeterministic,
  hasValidAIInterpretation,
} from "@/adapters/aiInterpretationAdapter";

import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
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
   Screen
-------------------------------------------------- */

export default function PredictionScreen() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <div>Missing base chart id</div>;

  const now = new Date();
  const baseYear = now.getFullYear();

  const [period, setPeriod] = useState<"monthly" | "yearly">("monthly");
  const [year, setYear] = useState(baseYear);

  /**
   * Unified cursor:
   * - monthly → month (1–12)
   * - yearly  → always 1
   */
  const [index, setIndex] = useState<number>(now.getMonth() + 1);

  /* -------------------------------------------------
     Keep cursor aligned when period changes
  -------------------------------------------------- */
  useEffect(() => {
    if (period === "monthly") {
      setIndex(now.getMonth() + 1);
    } else {
      setIndex(1);
    }
    setYear(baseYear);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  const queryClient = useQueryClient();
  const { data, isLoading, error } = usePrediction({
    baseChartId: id,
    period,
    year,
    month: period === "monthly" ? index : undefined,
  });

  /* -------------------------------------------------
     LLM status polling — fires only for monthly when
     the backend returns llm_status = "pending".
     MonthlyPredictionView is blocked until ready.
  -------------------------------------------------- */
  const llmPending = period === "monthly" && (data as any)?.llm_status === "pending";
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!llmPending) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const params = new URLSearchParams({
          base_chart_id: id,
          year: year.toString(),
          month: index.toString(),
        });
        const res = await fetch(`/api/prediction/monthly/llm-status?${params}`);
        if (!res.ok) return;
        const json = await res.json();
        if (json.status === "ready") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          queryClient.invalidateQueries({
            queryKey: ["prediction", id, "monthly", year, index, undefined],
          });
        }
      } catch (_) { /* ignore */ }
    }, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmPending]);

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
          {(["monthly", "yearly"] as const).map((p) => (
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

      {/* LLM pending — block prediction view, show centered spinner */}
      {llmPending && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-base font-medium">Generating your interpretation…</p>
          <p className="text-sm">This takes a few seconds</p>
        </div>
      )}

      {data && !llmPending && (
        <>
          {/* -------------------------------------------------
              Download (only for monthly/yearly)
          -------------------------------------------------- */}
          {(period === "monthly" || period === "yearly") && (
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => {
                const params = new URLSearchParams({
                  base_chart_id: id,
                  report_type: period,
                  year: year.toString(),
                });
                if (period === "monthly") {
                  params.append("month", index.toString());
                }
                window.open(`/api/reports/pdf?${params.toString()}`, "_blank");
              }}
              data-testid="button-download-pdf"
            >
              <Download className="h-4 w-4" />
              Download Full Report (PDF)
            </Button>
          )}

          <Separator className="my-4" />

          {/* -------------------------------------------------
              Prediction Body
          -------------------------------------------------- */}
          {hasValidAIInterpretation(data.details) && (() => {
            const extracted = extractInterpretationWithDeterministic(data.details);
            if (!extracted) return null;
            return (
              <MonthlyPredictionView
                prediction={adaptInterpretation(extracted.primary, extracted.deterministic)}
                period={period}
              />
            );
          })()}

          {dashaContext?.active?.antar && (
            <>
              <Separator className="my-6" />
              <AntarExplanationCard antar={dashaContext.active.antar} />
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
