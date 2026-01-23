import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

import {
  TrendingUp,
  Activity,
  Sparkles,
  ChevronRight,
  Zap,
  Star,
} from "lucide-react";

import type { PredictionViewModel, LifeAreaViewModel } from "@/adapters/aiInterpretationAdapter";

type PredictionPeriod = "weekly" | "monthly" | "yearly";

const OUTLOOK_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  positive: "default",
  neutral: "secondary",
  challenging: "destructive",
};

const MOMENTUM_ICONS: Record<string, typeof TrendingUp> = {
  growth: TrendingUp,
  stability: Activity,
  contraction: ChevronRight,
};

function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-600 dark:text-green-400";
  if (score >= 50) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

interface LifeAreaCardProps {
  area: LifeAreaViewModel;
  showAttribution: boolean;
}

function LifeAreaCard({ area, showAttribution }: LifeAreaCardProps) {
  return (
    <AccordionItem value={area.key} data-testid={`accordion-item-${area.key}`}>
      <AccordionTrigger data-testid={`accordion-trigger-${area.key}`}>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-medium">{area.label}</span>
          <Badge 
            variant={OUTLOOK_COLORS[area.outlook] ?? "secondary"}
            data-testid={`badge-outlook-${area.key}`}
          >
            {area.outlook}
          </Badge>
          <span className={`text-sm font-mono ${getScoreColor(area.score)}`} data-testid={`text-score-${area.key}`}>
            {area.score}
          </span>
        </div>
      </AccordionTrigger>

      <AccordionContent className="space-y-4 text-sm">
        <p data-testid={`text-summary-${area.key}`}>{area.summary}</p>

        {area.deeperExplanation && (
          <div className="bg-muted/50 p-3 rounded-md" data-testid={`text-explanation-${area.key}`}>
            <p className="text-muted-foreground">{area.deeperExplanation}</p>
          </div>
        )}

        {showAttribution && area.attribution && (
          <div className="border-t pt-3 space-y-2" data-testid={`section-attribution-${area.key}`}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Astrological Attribution
            </p>

            <div className="flex flex-wrap gap-2 text-xs">
              {area.attribution.planets && area.attribution.planets.length > 0 && (
                <div className="flex items-center gap-1">
                  <Star className="h-3 w-3" />
                  <span>{area.attribution.planets.join(", ")}</span>
                </div>
              )}

              {area.attribution.dasha && (
                <div className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  <span>Dasha: {area.attribution.dasha}</span>
                </div>
              )}
            </div>

            {area.attribution.engines && area.attribution.engines.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Engines: {area.attribution.engines.join(", ")}
              </p>
            )}

            {area.attribution.signalsUsed && area.attribution.signalsUsed.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-muted-foreground mb-1">Signals:</p>
                <div className="flex flex-wrap gap-1">
                  {area.attribution.signalsUsed.map((signal, idx) => (
                    <Badge 
                      key={idx} 
                      variant="outline" 
                      className="text-xs"
                      data-testid={`badge-signal-${area.key}-${idx}`}
                    >
                      {signal.engine} ({signal.valence}, {signal.weight.toFixed(2)})
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </AccordionContent>
    </AccordionItem>
  );
}

export function MonthlyPredictionView({
  prediction,
  period = "monthly",
}: {
  prediction: PredictionViewModel | null;
  period?: PredictionPeriod;
}) {
  if (!prediction) {
    return null;
  }

  const { windowSummary, lifeAreas, explainabilityLevel } = prediction;
  const showAttribution = explainabilityLevel === "full";

  const periodLabel =
    period === "weekly"
      ? "Weekly Prediction"
      : period === "yearly"
      ? "Yearly Prediction"
      : "Monthly Prediction";

  const MomentumIcon = MOMENTUM_ICONS[windowSummary.momentum] ?? TrendingUp;

  return (
    <div className="space-y-6" data-testid="section-prediction-view">

      {/* ================= WINDOW SUMMARY ================= */}
      <Card data-testid="card-window-summary">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {periodLabel}
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            <Badge variant="secondary" data-testid="badge-momentum">
              <MomentumIcon className="h-3 w-3 mr-1" />
              {windowSummary.momentum}
            </Badge>
            <Badge variant="outline" data-testid="badge-outcome-mode">
              {windowSummary.outcomeMode}
            </Badge>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <p className="text-base leading-relaxed" data-testid="text-overview">
            {windowSummary.overview}
          </p>

          {windowSummary.dominantForces && windowSummary.dominantForces.length > 0 && (
            <div className="space-y-2" data-testid="section-dominant-forces">
              <p className="text-sm font-medium text-muted-foreground">
                Dominant Forces
              </p>
              <ul className="space-y-1 text-sm">
                {windowSummary.dominantForces.map((force, idx) => (
                  <li key={idx} className="flex items-start gap-2" data-testid={`text-force-${idx}`}>
                    <Badge variant="outline" className="text-xs shrink-0">
                      {force.type}
                    </Badge>
                    <span>{force.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {windowSummary.timingGuidance && (
            <>
              <Separator />
              <div data-testid="section-timing-guidance">
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Timing Guidance
                </p>
                <p className="text-sm">{windowSummary.timingGuidance}</p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* ================= LIFE AREAS ================= */}
      <Card data-testid="card-life-areas">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Life Areas
          </CardTitle>
          <CardDescription>
            Area-wise influence and interpretation
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Accordion type="single" collapsible className="w-full" data-testid="accordion-life-areas">
            {lifeAreas.map(area => (
              <LifeAreaCard key={area.key} area={area} showAttribution={showAttribution} />
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* ================= ENGINE INFO ================= */}
      <div className="text-xs text-muted-foreground text-center" data-testid="text-engine-info">
        Generated at {new Date(prediction.generatedAt).toLocaleString()} | {prediction.engineVersion}
      </div>
    </div>
  );
}
