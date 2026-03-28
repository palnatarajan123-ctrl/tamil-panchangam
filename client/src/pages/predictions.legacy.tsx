import { useParams, Link } from "wouter";
import { useState, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { MonthlyPredictionView } from "@/components/prediction/MonthlyPredictionView";
import {
  adaptInterpretation,
  extractInterpretationWithDeterministic,
  hasValidAIInterpretation,
  type PredictionViewModel,
} from "@/adapters/aiInterpretationAdapter";

import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/hooks/use-toast";

import {
  Calendar,
  Loader2,
  Sparkles,
  ArrowLeft,
  AlertCircle,
  FileDown,
  ShieldCheck,
  ShieldAlert,
  Info,
  MessageCircle,
} from "lucide-react";
import { ChatPanel } from "@/components/ChatPanel";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const monthlySchema = z.object({
  year: z.string(),
  month: z.string(),
});

const yearlySchema = z.object({
  year: z.string(),
});

export default function Predictions() {
  const { id } = useParams<{ id: string }>();
  const baseChartId = id;
  const [chatOpen, setChatOpen] = useState(false);

  const { toast } = useToast();

  const [prediction, setPrediction] = useState<PredictionViewModel | null>(null);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [predictionType, setPredictionType] = useState<
    "monthly" | "yearly"
  >("monthly");
  const [llmPending, setLlmPending] = useState(false);
  const llmPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [lastPredictionParams, setLastPredictionParams] = useState<{
    year: number;
    month?: number;
  } | null>(null);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [envelopeData, setEnvelopeData] = useState<any>(null);
  const [calculationConfidence, setCalculationConfidence] = useState<{
    level: string;
    cusp_cases: Array<{ planet: string; position: string }>;
  } | null>(null);

  if (!baseChartId) {
    return (
      <div className="container max-w-4xl mx-auto px-4 py-12 text-muted-foreground" data-testid="text-no-chart">
        Select a birth chart
      </div>
    );
  }

  const { data: chart, isLoading, error } = useQuery({
    queryKey: ["/api/base-chart", baseChartId],
    queryFn: async () => {
      const res = await fetch(`/api/base-chart/${baseChartId}`);
      if (!res.ok) throw new Error("Birth chart not found");
      return res.json();
    },
  });

  const form = useForm<any>({
    resolver: zodResolver(
      predictionType === "monthly" ? monthlySchema : yearlySchema
    ),
    defaultValues: {
      year: new Date().getFullYear().toString(),
      month: (new Date().getMonth() + 1).toString(),
    },
  });

  const mutation = useMutation({
    mutationFn: async (v: any) => {
      const basePayload = {
        base_chart_id: baseChartId,
        year: Number(v.year),
      };

      let endpoint = "/api/prediction/monthly";
      let payload: any = basePayload;

      if (predictionType === "monthly") {
        payload.month = Number(v.month);
      } else {
        endpoint = "/api/prediction/yearly";
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      return res.json();
    },

    onSuccess: (data, variables) => {
      setPredictionError(null);

      // If LLM is still running in background, show spinner and poll
      if (data.llm_status === "pending" && predictionType === "monthly") {
        setLlmPending(true);
        setPrediction(null);
        setLastPredictionParams({
          year: Number(variables.year),
          month: Number(variables.month),
        });
        const pendingYear = Number(variables.year);
        const pendingMonth = Number(variables.month);
        llmPollRef.current = setInterval(async () => {
          try {
            const params = new URLSearchParams({
              base_chart_id: baseChartId!,
              year: pendingYear.toString(),
              month: pendingMonth.toString(),
            });
            const res = await fetch(`/api/prediction/monthly/llm-status?${params}`);
            if (!res.ok) return;
            const json = await res.json();
            if (json.status === "ready") {
              clearInterval(llmPollRef.current!);
              llmPollRef.current = null;
              setLlmPending(false);
              // Re-submit to get the merged prediction with LLM content
              mutation.mutate(variables);
            }
          } catch (_) { /* ignore */ }
        }, 3000);
        return;
      }

      // Clear any previous polling
      if (llmPollRef.current) {
        clearInterval(llmPollRef.current);
        llmPollRef.current = null;
      }
      setLlmPending(false);

      if (!hasValidAIInterpretation(data.details)) {
        setPrediction(null);
        setPredictionError("AI Interpretation data is missing or invalid.");
        setLastPredictionParams(null);
        toast({
          title: "Prediction Error",
          description: "AI Interpretation data is missing from the response.",
          variant: "destructive",
        });
        return;
      }

      const extracted = extractInterpretationWithDeterministic(data.details);
      if (!extracted) {
        setPrediction(null);
        setPredictionError("Failed to extract AI Interpretation.");
        setLastPredictionParams(null);
        return;
      }

      const viewModel = adaptInterpretation(extracted.primary, extracted.deterministic);
      setPrediction(viewModel);

      // Extract calculation confidence and envelope
      const envelope = data.details?.envelope;
      setEnvelopeData(envelope || null);
      if (envelope?.calculation_confidence) {
        setCalculationConfidence(envelope.calculation_confidence);
      } else {
        setCalculationConfidence(null);
      }

      setLastPredictionParams({
        year: Number(variables.year),
        month: variables.month ? Number(variables.month) : undefined,
      });

      toast({
        title: "Prediction Generated",
        description: `${predictionType} prediction ready`,
      });
    },

    onError: (e: Error) => {
      setPrediction(null);
      setPredictionError(e.message);
      setLastPredictionParams(null);
      toast({
        title: "Prediction failed",
        description: e.message,
        variant: "destructive",
      });
    },
  });

  const handleDownloadPdf = async () => {
    if (!baseChartId || !lastPredictionParams) return;
    
    setIsDownloadingPdf(true);
    
    try {
      const params = new URLSearchParams({
        base_chart_id: baseChartId,
        report_type: predictionType,
        year: lastPredictionParams.year.toString(),
      });
      
      if (predictionType === "monthly" && lastPredictionParams.month) {
        params.append("month", lastPredictionParams.month.toString());
      }
      
      const res = await fetch(`/api/reports/pdf?${params.toString()}`);
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "Failed to generate PDF");
      }
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      
      const contentDisposition = res.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
      const filename = filenameMatch?.[1] || `report_${lastPredictionParams.year}.pdf`;
      
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast({
        title: "PDF Downloaded",
        description: "Your astrology report has been downloaded.",
      });
    } catch (e: any) {
      toast({
        title: "PDF Download Failed",
        description: e.message || "Unable to generate the PDF report.",
        variant: "destructive",
      });
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container max-w-6xl mx-auto px-4 py-12">
        <Skeleton className="h-8 w-64 mb-6" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !chart) {
    return (
      <div className="container max-w-4xl mx-auto px-4 py-12" data-testid="text-chart-error">
        Birth chart not found
      </div>
    );
  }

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">

      {/* HEADER */}
      <div className="flex items-center gap-4 mb-6">
        <Link href={`/chart/${baseChartId}`}>
          <Button variant="ghost" size="icon" data-testid="button-back">
            <ArrowLeft />
          </Button>
        </Link>

        <h1 className="text-3xl font-bold flex items-center gap-2" data-testid="heading-predictions">
          <Sparkles /> Predictions
        </h1>

        <StatusBadge status="ok" />
      </div>

      {/* TABS */}
      <div className="flex gap-2 mb-6">
        {(["monthly", "yearly"] as const).map(t => (
          <Button
            key={t}
            variant={predictionType === t ? "default" : "outline"}
            onClick={() => {
              setPredictionType(t);
              setPrediction(null);
              setPredictionError(null);
              setLlmPending(false);
              setEnvelopeData(null);
              if (llmPollRef.current) { clearInterval(llmPollRef.current); llmPollRef.current = null; }
            }}
            data-testid={`button-tab-${t}`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </Button>
        ))}
      </div>

      {/* FORM */}
      <Card className="mb-8" data-testid="card-form">
        <CardContent className="pt-6">
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(v => mutation.mutate(v))}
              className="grid grid-cols-1 md:grid-cols-3 gap-4"
            >
              <FormField
                control={form.control}
                name="year"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Year</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} data-testid="input-year" />
                    </FormControl>
                  </FormItem>
                )}
              />

              {predictionType === "monthly" && (
                <FormField
                  control={form.control}
                  name="month"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Month</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger data-testid="select-month">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {MONTHS.map((m, i) => (
                            <SelectItem key={i} value={(i + 1).toString()} data-testid={`select-item-month-${i + 1}`}>
                              {m}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
              )}

              <Button
                type="submit"
                className="md:col-span-3"
                disabled={mutation.isPending}
                data-testid="button-generate"
              >
                {mutation.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <>
                    <Calendar className="mr-2" />
                    Generate
                  </>
                )}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* ERROR STATE */}
      {predictionError && !prediction && (
        <Card className="mb-8 border-destructive" data-testid="card-error">
          <CardContent className="pt-6 flex items-center gap-3 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <span>{predictionError}</span>
          </CardContent>
        </Card>
      )}

      {/* LLM PENDING SPINNER */}
      {llmPending && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-base font-medium">Generating your interpretation…</p>
          <p className="text-sm">This takes a few seconds</p>
        </div>
      )}

      {/* RESULT */}
      {prediction && !llmPending && (
        <>
          {/* Prediction Confidence - shown once below summary */}
          {calculationConfidence && (
            <Card className="mb-4" data-testid="card-prediction-confidence">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start gap-3">
                  {calculationConfidence.level === "high" ? (
                    <ShieldCheck className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                  ) : calculationConfidence.level === "medium" ? (
                    <Info className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
                  ) : (
                    <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                  )}
                  <div>
                    <span className="font-medium">Prediction Confidence: </span>
                    <span className={
                      calculationConfidence.level === "high" 
                        ? "text-green-600 dark:text-green-400 font-medium" 
                        : calculationConfidence.level === "medium"
                        ? "text-amber-600 dark:text-amber-400 font-medium"
                        : "text-red-600 dark:text-red-400 font-medium"
                    }>
                      {calculationConfidence.level === "high" ? "High" : 
                       calculationConfidence.level === "medium" ? "Medium" : "Sensitive"}
                    </span>
                    <p className="text-sm text-muted-foreground mt-1">
                      {calculationConfidence.level === "high" 
                        ? "All planetary positions are clearly within sign boundaries."
                        : "Some influences fall near transitional boundaries. Interpret trends as ranges rather than absolutes."}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          
          <div className="flex gap-4 items-start">
            <div className={chatOpen ? "flex-1 min-w-0" : "w-full"}>
              <MonthlyPredictionView prediction={prediction} period={predictionType} envelope={envelopeData} />
            </div>
            {chatOpen && (
              <div className="w-80 flex-shrink-0 h-[600px] rounded-xl overflow-hidden border border-border shadow-sm">
                <ChatPanel
                  baseChartId={baseChartId!}
                  chartName={chart?.payload?.birth_details?.name || chart?.name || "Chart"}
                  mahadasha={chart?.payload?.dasha_periods?.current?.mahadasha || "—"}
                  antardasha={chart?.payload?.dasha_periods?.current?.antardasha || "—"}
                  periodLabel={predictionType === "monthly" && lastPredictionParams ? `${MONTHS[(lastPredictionParams.month ?? 1) - 1]} ${lastPredictionParams.year}` : String(lastPredictionParams?.year ?? new Date().getFullYear())}
                  onClose={() => setChatOpen(false)}
                />
              </div>
            )}
          </div>

          {prediction && (
            <div className="mt-6 flex justify-center gap-3 flex-wrap">
              <button
                onClick={() => setChatOpen((v) => !v)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 transition-colors text-sm font-medium"
              >
                <MessageCircle className="w-4 h-4" />
                {chatOpen ? "Close Chat" : "Ask Jyotishi"}
              </button>
              <Button
                onClick={handleDownloadPdf}
                disabled={isDownloadingPdf}
                size="lg"
                className="gap-2"
                data-testid="button-download-pdf"
              >
                {isDownloadingPdf ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating PDF...
                  </>
                ) : (
                  <>
                    <FileDown className="h-4 w-4" />
                    Generate PDF Report
                  </>
                )}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
