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
  Target,
  AlertTriangle,
  Calendar,
  BookOpen,
  MessageCircle,
  CheckCircle,
  Heart,
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
  isV2: boolean;
}

function LifeAreaCard({ area, showAttribution, isV2 }: LifeAreaCardProps) {
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

        {isV2 && area.opportunity && (
          <div className="flex items-start gap-2 bg-green-50 dark:bg-green-950/30 p-3 rounded-md" data-testid={`text-opportunity-${area.key}`}>
            <Target className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-green-700 dark:text-green-300 mb-1">Opportunity</p>
              <p className="text-green-800 dark:text-green-200">{area.opportunity}</p>
            </div>
          </div>
        )}

        {isV2 && area.watchOut && (
          <div className="flex items-start gap-2 bg-amber-50 dark:bg-amber-950/30 p-3 rounded-md" data-testid={`text-watchout-${area.key}`}>
            <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Watch Out</p>
              <p className="text-amber-800 dark:text-amber-200">{area.watchOut}</p>
            </div>
          </div>
        )}

        {isV2 && area.oneAction && (
          <div className="flex items-start gap-2 bg-blue-50 dark:bg-blue-950/30 p-3 rounded-md" data-testid={`text-action-${area.key}`}>
            <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">One Action</p>
              <p className="text-blue-800 dark:text-blue-200">{area.oneAction}</p>
            </div>
          </div>
        )}

        {!isV2 && area.deeperExplanation && (
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
                      {signal.engine} ({signal.valence}{signal.weight != null ? `, ${signal.weight.toFixed(2)}` : ""})
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

  const { lifeAreas, explainabilityLevel } = prediction;
  const showAttribution = explainabilityLevel === "full";
  const isV2 = prediction.engineVersion === "ai-interpretation-v2.0";

  const periodLabel =
    period === "weekly"
      ? "Weekly Prediction"
      : period === "yearly"
      ? "Yearly Prediction"
      : "Monthly Prediction";

  return (
    <div className="space-y-6" data-testid="section-prediction-view">

      {/* ================= V2: MONTHLY THEME ================= */}
      {isV2 && prediction.monthlyTheme && (
        <Card data-testid="card-monthly-theme" className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              {prediction.monthlyTheme.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-base leading-relaxed" data-testid="text-theme-narrative">
              {prediction.monthlyTheme.narrative}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ================= V2: OVERVIEW ================= */}
      {isV2 && prediction.overview && (
        <Card data-testid="card-overview">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              {periodLabel}
            </CardTitle>
            <CardDescription>
              Energy pattern and focus areas
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-base leading-relaxed" data-testid="text-energy-pattern">
              {prediction.overview.energyPattern}
            </p>

            {prediction.overview.keyFocus && prediction.overview.keyFocus.length > 0 && (
              <div className="space-y-2" data-testid="section-key-focus">
                <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <Target className="h-4 w-4" />
                  Key Focus Areas
                </p>
                <ul className="space-y-1 text-sm pl-5">
                  {prediction.overview.keyFocus.map((item, idx) => (
                    <li key={idx} className="list-disc" data-testid={`text-focus-${idx}`}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {prediction.overview.avoidOrBeMindful && prediction.overview.avoidOrBeMindful.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2" data-testid="section-avoid">
                  <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4" />
                    Be Mindful Of
                  </p>
                  <ul className="space-y-1 text-sm pl-5">
                    {prediction.overview.avoidOrBeMindful.map((item, idx) => (
                      <li key={idx} className="list-disc text-amber-700 dark:text-amber-400" data-testid={`text-avoid-${idx}`}>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= V1: WINDOW SUMMARY (legacy) ================= */}
      {!isV2 && prediction.windowSummary && (
        <Card data-testid="card-window-summary">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              {periodLabel}
            </CardTitle>
            <CardDescription className="flex items-center gap-2">
              <Badge variant="secondary" data-testid="badge-momentum">
                {MOMENTUM_ICONS[prediction.windowSummary.momentum] ? (
                  (() => {
                    const MomentumIcon = MOMENTUM_ICONS[prediction.windowSummary.momentum];
                    return <MomentumIcon className="h-3 w-3 mr-1" />;
                  })()
                ) : null}
                {prediction.windowSummary.momentum}
              </Badge>
              <Badge variant="outline" data-testid="badge-outcome-mode">
                {prediction.windowSummary.outcomeMode}
              </Badge>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-base leading-relaxed" data-testid="text-overview">
              {prediction.windowSummary.overview}
            </p>

            {prediction.windowSummary.dominantForces && prediction.windowSummary.dominantForces.length > 0 && (
              <div className="space-y-2" data-testid="section-dominant-forces">
                <p className="text-sm font-medium text-muted-foreground">
                  Dominant Forces
                </p>
                <ul className="space-y-1 text-sm">
                  {prediction.windowSummary.dominantForces.map((force, idx) => (
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

            {prediction.windowSummary.timingGuidance && (
              <>
                <Separator />
                <div data-testid="section-timing-guidance">
                  <p className="text-sm font-medium text-muted-foreground mb-1">
                    Timing Guidance
                  </p>
                  <p className="text-sm">{prediction.windowSummary.timingGuidance}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= LIFE AREAS ================= */}
      <Card data-testid="card-life-areas">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Life Areas
          </CardTitle>
          <CardDescription>
            {isV2 ? "Detailed insights with opportunities and actions" : "Area-wise influence and interpretation"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Accordion type="single" collapsible className="w-full" data-testid="accordion-life-areas">
            {lifeAreas.map(area => (
              <LifeAreaCard key={area.key} area={area} showAttribution={showAttribution} isV2={isV2} />
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* ================= V2: PRACTICES & REFLECTION ================= */}
      {isV2 && prediction.practicesAndReflection && (
        <Card data-testid="card-practices">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Practices & Reflection
            </CardTitle>
            <CardDescription>
              Suggested activities and questions for this period
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {prediction.practicesAndReflection.dailyPractice && (
              <div className="flex items-start gap-3" data-testid="section-daily-practice">
                <Calendar className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Daily Practice</p>
                  <p className="text-sm">{prediction.practicesAndReflection.dailyPractice}</p>
                </div>
              </div>
            )}

            {prediction.practicesAndReflection.weeklyPractice && (
              <div className="flex items-start gap-3" data-testid="section-weekly-practice">
                <Activity className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Weekly Practice</p>
                  <p className="text-sm">{prediction.practicesAndReflection.weeklyPractice}</p>
                </div>
              </div>
            )}

            {(prediction.practicesAndReflection.reflectionGuidance || prediction.practicesAndReflection.reflectionQuestion) && (
              <div className="flex items-start gap-3 bg-muted/50 p-4 rounded-lg" data-testid="section-reflection">
                <MessageCircle className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Reflection & Guidance</p>
                  <p className="text-sm">
                    {prediction.practicesAndReflection.reflectionGuidance || prediction.practicesAndReflection.reflectionQuestion}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= V2: CLOSING ================= */}
      {isV2 && prediction.closing && (
        <Card data-testid="card-closing" className="border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Heart className="h-5 w-5 text-primary" />
              Key Takeaways
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            {prediction.closing.keyTakeaways && prediction.closing.keyTakeaways.length > 0 && (
              <ul className="space-y-2" data-testid="section-takeaways">
                {prediction.closing.keyTakeaways.map((takeaway, idx) => (
                  <li key={idx} className="flex items-start gap-2" data-testid={`text-takeaway-${idx}`}>
                    <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
                    <span className="text-sm">{takeaway}</span>
                  </li>
                ))}
              </ul>
            )}

            {prediction.closing.encouragement && (
              <>
                <Separator />
                <p className="text-base leading-relaxed text-muted-foreground italic" data-testid="text-encouragement">
                  {prediction.closing.encouragement}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= ENGINE INFO ================= */}
      <div className="text-xs text-muted-foreground text-center" data-testid="text-engine-info">
        Generated at {new Date(prediction.generatedAt).toLocaleString()} | {prediction.engineVersion}
      </div>
    </div>
  );
}
