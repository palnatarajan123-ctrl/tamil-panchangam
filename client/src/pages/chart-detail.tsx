// client/src/pages/chart-detail.tsx

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, Link } from "wouter";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

import { StatusBadge } from "@/components/status-badge";
import { DashaTimeline } from "@/components/DashaTimeline";
import { ChartPair } from "@/components/ChartPair";
import { 
  BirthAstroContextTable, 
  adaptBirthChartToAstroContext,
  type RealtimeContextData,
} from "@/components/BirthAstroContextTable";

import {
  ArrowLeft,
  Calendar,
  Clock,
  MapPin,
  User,
  Sparkles,
  Download,
  Loader2,
  TrendingUp,
  Activity,
  Eye,
} from "lucide-react";

import { apiRequest } from "@/lib/queryClient";
import { adaptBirthChart } from "@/adapters/birthChartAdapter";
import { 
  adaptAIInterpretation, 
  type PredictionViewModel,
  type ExplainabilityLevel,
} from "@/adapters/aiInterpretationAdapter";

const OUTLOOK_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  positive: "default",
  favorable: "default",
  neutral: "secondary",
  challenging: "destructive",
};

function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-600 dark:text-green-400";
  if (score >= 50) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

export default function ChartDetail() {
  const { id: chartId } = useParams<{ id: string }>();
  const [explainabilityLevel, setExplainabilityLevel] = useState<ExplainabilityLevel>("standard");
  const [rawInterpretation, setRawInterpretation] = useState<any>(null);

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  const {
    data: rawView,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["/api/ui/birth-chart", chartId],
    enabled: !!chartId,
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/ui/birth-chart?base_chart_id=${chartId}`
      );
      const json = await res.json();
      if (!res.ok) throw new Error("Birth chart not found");
      if (json?.data?.view) return json.data.view;
      if (json?.view) return json.view;
      if (json?.identity) return json;
      throw new Error("Invalid birth chart response shape");
    },
  });

  const { data: realtimeContextData } = useQuery({
    queryKey: ["/api/realtime/context", chartId],
    enabled: !!chartId,
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/realtime/context/${chartId}`
      );
      if (!res.ok) return null;
      const json = await res.json();
      return json?.context as RealtimeContextData | null;
    },
    staleTime: 60000,
  });

  const generatePrediction = useMutation({
    mutationFn: async () => {
      // Always request "full" from backend to get complete data
      // Frontend adapter will filter based on user's explainabilityLevel selection
      const res = await apiRequest("POST", "/api/prediction/monthly", {
        base_chart_id: chartId,
        year: currentYear,
        month: currentMonth,
        explainability_level: "full",
      });
      if (!res.ok) throw new Error("Failed to generate prediction");
      return res.json();
    },
    onSuccess: (data) => {
      const aiInterpretation = data?.details?.interpretation?.ai_interpretation;
      if (aiInterpretation) {
        setRawInterpretation(aiInterpretation);
      }
    },
  });

  const prediction = rawInterpretation
    ? adaptAIInterpretation(rawInterpretation, explainabilityLevel)
    : null;

  if (isLoading) {
    return (
      <div className="container max-w-7xl mx-auto px-4 py-8">
        <Skeleton className="h-8 w-64 mb-8" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (error || !rawView) {
    return (
      <div className="container max-w-7xl mx-auto px-4 py-8">
        <Card className="border-muted">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">Chart not found</p>
            <Link href="/">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const ui = adaptBirthChart({ view: rawView });
  if (!ui || !ui.identity || !ui.southIndianChart) return null;

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>

        <div className="flex-1">
          <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight flex items-center gap-3">
            <Sparkles className="h-7 w-7 text-primary" />
            {ui.identity.name || "Birth Chart"}
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Immutable Birth Chart · Sidereal (Lahiri)
          </p>
        </div>

        <StatusBadge status="ok" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Charts */}
        <div className="lg:col-span-2 space-y-6">
          <ChartPair
            d1={{
              lagna: ui.southIndianChart.lagna,
              planets: ui.southIndianChart.planets,
            }}
            d9={{
              lagna: ui.navamsaChart.lagna,
              planets: ui.navamsaChart.planets,
              dignity: ui.navamsaChart.dignity,
            }}
          />

          <BirthAstroContextTable 
            data={adaptBirthChartToAstroContext(ui, undefined, realtimeContextData ?? undefined)} 
          />

          <DashaTimeline
            timeline={ui.vimshottari.timeline}
            current={
              ui.vimshottari.current
                ? {
                    maha: {
                      lord: ui.vimshottari.current.lord,
                      start: ui.vimshottari.current.start,
                      end: ui.vimshottari.current.end,
                      is_partial: ui.vimshottari.current.is_partial,
                    },
                    antar: ui.vimshottari.current.antar ?? null,
                  }
                : undefined
            }
          />

          {/* AI Interpretation Section */}
          <Card className="border-muted" data-testid="card-ai-interpretation">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-primary" />
                    AI Interpretation
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {prediction 
                      ? `${new Date(currentYear, currentMonth - 1).toLocaleString('default', { month: 'long', year: 'numeric' })} outlook`
                      : "Generate a prediction to see personalized insights"
                    }
                  </CardDescription>
                </div>

                {prediction && (
                  <ToggleGroup
                    type="single"
                    value={explainabilityLevel}
                    onValueChange={(val) => {
                      if (val) {
                        setExplainabilityLevel(val as ExplainabilityLevel);
                      }
                    }}
                    className="border rounded-md"
                    data-testid="toggle-explainability"
                  >
                    <ToggleGroupItem value="minimal" size="sm" data-testid="toggle-minimal">
                      <Eye className="h-3 w-3 mr-1" />
                      Minimal
                    </ToggleGroupItem>
                    <ToggleGroupItem value="standard" size="sm" data-testid="toggle-standard">
                      Standard
                    </ToggleGroupItem>
                    <ToggleGroupItem value="full" size="sm" data-testid="toggle-full">
                      Full
                    </ToggleGroupItem>
                  </ToggleGroup>
                )}
              </div>
            </CardHeader>

            <CardContent>
              {!prediction ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground mb-4">
                    Generate a prediction for this month to see AI-powered insights
                  </p>
                  <Button
                    onClick={() => generatePrediction.mutate()}
                    disabled={generatePrediction.isPending}
                    data-testid="button-generate-interpretation"
                  >
                    {generatePrediction.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        Generate This Month's Prediction
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Window Summary */}
                  {prediction.windowSummary && (
                    <div className="bg-muted/30 rounded-lg p-4 space-y-3" data-testid="card-window-summary">
                      <div className="flex items-center gap-2">
                        {prediction.windowSummary.momentum === "growth" ? (
                          <TrendingUp className="h-5 w-5 text-green-500" />
                        ) : (
                          <Activity className="h-5 w-5 text-amber-500" />
                        )}
                        <Badge variant="outline">
                          {prediction.windowSummary.momentum}
                        </Badge>
                        {prediction.windowSummary.outcomeMode && (
                          <Badge variant="secondary">
                            {prediction.windowSummary.outcomeMode}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm" data-testid="text-overview">
                        {prediction.windowSummary.overview}
                      </p>
                      {prediction.windowSummary.timingGuidance && (
                        <p className="text-xs text-muted-foreground" data-testid="text-timing">
                          {prediction.windowSummary.timingGuidance}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Life Areas */}
                  {prediction.lifeAreas && prediction.lifeAreas.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        Life Areas
                      </h4>
                      <Accordion type="single" collapsible className="space-y-2">
                        {prediction.lifeAreas.map((area) => (
                          <AccordionItem 
                            key={area.key} 
                            value={area.key}
                            className="border rounded-lg px-4"
                            data-testid={`accordion-item-${area.key}`}
                          >
                            <AccordionTrigger data-testid={`accordion-trigger-${area.key}`}>
                              <div className="flex items-center gap-3 flex-wrap">
                                <span className="font-medium">{area.label}</span>
                                <Badge 
                                  variant={OUTLOOK_COLORS[area.outlook] ?? "secondary"}
                                  data-testid={`badge-outlook-${area.key}`}
                                >
                                  {area.outlook}
                                </Badge>
                                <span 
                                  className={`text-sm font-mono ${getScoreColor(area.score)}`}
                                  data-testid={`text-score-${area.key}`}
                                >
                                  {area.score}
                                </span>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-3 text-sm pb-4">
                              <p data-testid={`text-summary-${area.key}`}>
                                {area.summary}
                              </p>
                              {explainabilityLevel !== "minimal" && area.deeperExplanation && (
                                <div 
                                  className="bg-muted/50 p-3 rounded-md"
                                  data-testid={`text-explanation-${area.key}`}
                                >
                                  <p className="text-muted-foreground">
                                    {area.deeperExplanation}
                                  </p>
                                </div>
                              )}
                              {/* Attribution - shown in standard and full modes */}
                              {explainabilityLevel !== "minimal" && area.attribution && (
                                <div 
                                  className="border-t pt-3 mt-2"
                                  data-testid={`attribution-${area.key}`}
                                >
                                  <div className="text-xs text-muted-foreground space-y-1">
                                    {area.attribution.planets && area.attribution.planets.length > 0 && (
                                      <div className="flex gap-2 flex-wrap items-center">
                                        <span className="font-medium">Planets:</span>
                                        {area.attribution.planets.map((p) => (
                                          <Badge key={p} variant="outline" className="text-xs">{p}</Badge>
                                        ))}
                                      </div>
                                    )}
                                    {area.attribution.dasha && (
                                      <div>
                                        <span className="font-medium">Dasha:</span>{" "}
                                        <span className="font-mono">{area.attribution.dasha}</span>
                                      </div>
                                    )}
                                    {area.attribution.engines && area.attribution.engines.length > 0 && (
                                      <div className="flex gap-2 flex-wrap items-center">
                                        <span className="font-medium">Engines:</span>
                                        {area.attribution.engines.map((e) => (
                                          <Badge key={e} variant="secondary" className="text-xs">{e}</Badge>
                                        ))}
                                      </div>
                                    )}
                                    {/* Signals - only shown in full mode */}
                                    {explainabilityLevel === "full" && area.attribution.signalsUsed && area.attribution.signalsUsed.length > 0 && (
                                      <div className="border-t pt-2 mt-2">
                                        <span className="font-medium">Signals:</span>
                                        <div className="grid grid-cols-2 gap-1 mt-1">
                                          {area.attribution.signalsUsed.map((sig, i) => (
                                            <div 
                                              key={i} 
                                              className="flex justify-between bg-muted/30 px-2 py-0.5 rounded text-xs"
                                            >
                                              <span>{sig.engine}</span>
                                              <span className={sig.valence === "positive" ? "text-green-600" : sig.valence === "negative" ? "text-red-600" : "text-muted-foreground"}>
                                                {sig.weight > 0 ? "+" : ""}{sig.weight}
                                              </span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </AccordionContent>
                          </AccordionItem>
                        ))}
                      </Accordion>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6 lg:sticky lg:top-24">
          <Card className="border-muted">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Birth Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Date</div>
                  <div className="text-muted-foreground">{ui.birth.date}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Time</div>
                  <div className="text-muted-foreground">{ui.birth.time}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Place</div>
                  <div className="text-muted-foreground">
                    {ui.identity.place}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={() =>
              window.open(
                `/api/reports/charts/${chartId}/pdf`,
                "_blank"
              )
            }
          >
            <Download className="h-4 w-4" />
            Download Birth Chart PDF
          </Button>

          <Link href={`/chart/${chartId}/predictions`}>
            <Button className="w-full gap-2 mt-2">
              <Calendar className="h-4 w-4" />
              Generate Predictions
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
