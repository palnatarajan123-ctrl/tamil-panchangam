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
import { Loader2, Download, Sparkles, MessageCircle } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getAccessToken } from "@/lib/auth";
import { ChatPanel } from "@/components/ChatPanel";

/* -------------------------------------------------
   Screen
-------------------------------------------------- */

export default function PredictionScreen() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <div>Missing base chart id</div>;
  const [chatOpen, setChatOpen] = useState(false);

  const now = new Date();
  const baseYear = now.getFullYear();

  const [period, setPeriod] = useState<"monthly" | "yearly">("monthly");
  const [year, setYear] = useState(baseYear);
  const [enhancing, setEnhancing] = useState(false);
  const [llmDisabledMessage, setLlmDisabledMessage] = useState<string | null>(null);

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
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!llmPending) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const statusUrl = period === "monthly"
          ? `/api/prediction/monthly/llm-status?${new URLSearchParams({ base_chart_id: id, year: year.toString(), month: index.toString() })}`
          : `/api/prediction/yearly/llm-status?${new URLSearchParams({ base_chart_id: id, year: year.toString() })}`;
        const res = await fetch(statusUrl);
        if (!res.ok) return;
        const json = await res.json();
        if (json.status === "ready") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
          queryClient.invalidateQueries({
            queryKey: period === "monthly"
              ? ["prediction", id, "monthly", year, index, undefined]
              : ["prediction", id, "yearly", year],
          });
        }
      } catch (_) { /* ignore */ }
    }, 3000);
    pollTimeoutRef.current = setTimeout(() => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      queryClient.invalidateQueries({
        queryKey: period === "monthly"
          ? ["prediction", id, "monthly", year, index, undefined]
          : ["prediction", id, "yearly", year],
      });
    }, 120000); // 2 minutes max
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmPending]);

  const dashaContext = data?.details?.envelope?.dasha_context;

  const fallbackReason = data?.details?.interpretation?.llm_metadata?.fallback_reason;
  const llmProvider = data?.details?.interpretation?.llm_metadata?.provider;
  const showEnhanceButton =
    (fallbackReason === "llm_disabled" || fallbackReason === "anthropic_key_missing") &&
    llmProvider !== "anthropic" &&
    llmProvider !== "cache";

  async function handleEnhanceWithAI() {
    setEnhancing(true);
    setLlmDisabledMessage(null);
    try {
      const token = getAccessToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const statusRes = await fetch("/api/admin/llm/status", { headers });
      const statusJson = await statusRes.json();

      if (!statusJson.llm_enabled) {
        setLlmDisabledMessage("AI enhancement is currently disabled by admin");
        return;
      }

      await fetch("/api/admin/llm/clear-cache", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ base_chart_id: id }),
      });

      queryClient.invalidateQueries({
        queryKey: ["prediction", id, period, year, index, undefined],
      });
    } finally {
      setEnhancing(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------
          Header
      -------------------------------------------------- */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold capitalize">
          {period} Predictions
        </h1>
        {data && (
          <p className="text-sm text-muted-foreground mt-1">
            {data?.details?.envelope?.birth_details?.name || ""}
            {data?.details?.envelope?.ephemeris?.moon?.rasi ? ` · ${data.details.envelope.ephemeris.moon.rasi}` : ""}
            {data?.details?.envelope?.ephemeris?.moon?.nakshatra?.name ? ` · ${data.details.envelope.ephemeris.moon.nakshatra.name}` : ""}
          </p>
        )}

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
        <div className={chatOpen ? "mr-80 transition-all duration-300" : "transition-all duration-300"}>
          {/* -------------------------------------------------
              Download (only for monthly/yearly)
          -------------------------------------------------- */}
          {(period === "monthly" || period === "yearly") && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setChatOpen((v) => !v)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 transition-colors text-sm font-medium"
              >
                <MessageCircle className="w-4 h-4" />
                {chatOpen ? "Close Chat" : "Ask Jyotishi"}
              </button>
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

              {showEnhanceButton && (
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={handleEnhanceWithAI}
                  disabled={enhancing || !!llmDisabledMessage}
                  title={llmDisabledMessage ?? undefined}
                >
                  {enhancing
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : <Sparkles className="h-4 w-4" />
                  }
                  Enhance with AI
                </Button>
              )}
            </div>
          )}

          <Separator className="my-4" />
          {chatOpen && (
            <div className="fixed top-0 right-0 h-full w-80 z-40 shadow-xl border-l border-border">
              <ChatPanel
                baseChartId={id}
                chartName={data?.details?.envelope?.birth_details?.name || data?.details?.birth_details?.name || id}
                mahadasha={dashaContext?.active?.lord || "—"}
                antardasha={dashaContext?.active?.antar?.lord || "—"}
                periodLabel={period === "monthly" ? `${new Date(year, (index ?? 1) - 1).toLocaleString("default", { month: "long" })} ${year}` : String(year)}
                onClose={() => setChatOpen(false)}
              />
            </div>
          )}

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
                envelope={data.details?.envelope}
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
        </div>
        </>
      )}
    </div>
  );
}
