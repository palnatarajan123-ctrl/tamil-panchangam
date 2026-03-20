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
  Shield,
  Flame,
} from "lucide-react";

import type { PredictionViewModel, LifeAreaViewModel } from "@/adapters/aiInterpretationAdapter";

function splitIntoParagraphs(text: string): string[] {
  if (!text) return [];
  const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
  const paragraphs: string[] = [];
  for (let i = 0; i < sentences.length; i += 3) {
    paragraphs.push(sentences.slice(i, i + 3).join(" ").trim());
  }
  return paragraphs;
}

function Paragraphs({ text, className }: { text: string; className?: string }) {
  const paras = splitIntoParagraphs(text);
  return (
    <>
      {paras.map((para, i) => (
        <p key={i} className={`mb-3 leading-relaxed last:mb-0 ${className ?? ""}`}>{para}</p>
      ))}
    </>
  );
}

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
  isV2: boolean;
}

function LifeAreaCard({ area, isV2 }: LifeAreaCardProps) {
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
        <div data-testid={`text-summary-${area.key}`}>
          <Paragraphs text={area.summary} />
        </div>

        {!isV2 && area.deeperExplanation && (
          <div className="bg-muted/50 p-3 rounded-md" data-testid={`text-explanation-${area.key}`}>
            <Paragraphs text={area.deeperExplanation} className="text-muted-foreground" />
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

  const { lifeAreas } = prediction;
  const isV3 = prediction.engineVersion === "ai-interpretation-v3.0";
  const isV2 = prediction.engineVersion === "ai-interpretation-v2.0";

  const periodLabel =
    period === "weekly"
      ? "Weekly Prediction"
      : period === "yearly"
      ? "Yearly Prediction"
      : "Monthly Prediction";

  return (
    <div className="space-y-6" data-testid="section-prediction-view">

      {/* ================= V3: YEARLY MANTRA ================= */}
      {isV3 && prediction.yearlyMantra && (
        <Card data-testid="card-yearly-mantra" className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Guiding Theme
            </CardTitle>
            <CardDescription>
              Your spiritual and practical compass for this period
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div data-testid="text-yearly-mantra" className="text-base">
              <Paragraphs text={prediction.yearlyMantra} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================= V3: DASHA-TRANSIT SYNTHESIS ================= */}
      {isV3 && prediction.dashaTransitSynthesis && (
        <Card data-testid="card-dasha-synthesis">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Dasha-Transit Synthesis
            </CardTitle>
            <CardDescription>
              How your planetary periods and current transits interact
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div data-testid="text-dasha-synthesis" className="text-base">
              <Paragraphs text={prediction.dashaTransitSynthesis} />
            </div>
          </CardContent>
        </Card>
      )}

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
            <div data-testid="text-theme-narrative" className="text-base">
              <Paragraphs text={prediction.monthlyTheme.narrative} />
            </div>
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
            <div data-testid="text-energy-pattern" className="text-base">
              <Paragraphs text={prediction.overview.energyPattern} />
            </div>

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

            {prediction.overview.attributionSummary && (
              <>
                <Separator />
                <div className="space-y-2" data-testid="section-attribution-summary">
                  <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <Star className="h-4 w-4" />
                    Astrological Influences
                  </p>
                  <div className="flex flex-wrap gap-2 text-sm">
                    {prediction.overview.attributionSummary.activeDasha && (
                      <Badge variant="outline" className="flex items-center gap-1" data-testid="badge-dasha">
                        <Zap className="h-3 w-3" />
                        {prediction.overview.attributionSummary.activeDasha}
                      </Badge>
                    )}
                    {prediction.overview.attributionSummary.activePlanets.map((planet, idx) => (
                      <Badge key={idx} variant="secondary" data-testid={`badge-planet-${idx}`}>
                        {planet}
                      </Badge>
                    ))}
                  </div>
                  {prediction.overview.attributionSummary.activeEngines.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Sources: {prediction.overview.attributionSummary.activeEngines.join(", ")}
                    </p>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= V1: WINDOW SUMMARY (legacy) ================= */}
      {!isV2 && !isV3 && prediction.windowSummary && (
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
            <div data-testid="text-overview" className="text-base">
              <Paragraphs text={prediction.windowSummary.overview} />
            </div>

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

            {prediction.windowSummary.attributionSummary && (
              <>
                <Separator />
                <div className="space-y-2" data-testid="section-attribution-summary-v1">
                  <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <Star className="h-4 w-4" />
                    Astrological Influences
                  </p>
                  <div className="flex flex-wrap gap-2 text-sm">
                    {prediction.windowSummary.attributionSummary.activeDasha && (
                      <Badge variant="outline" className="flex items-center gap-1" data-testid="badge-dasha-v1">
                        <Zap className="h-3 w-3" />
                        {prediction.windowSummary.attributionSummary.activeDasha}
                      </Badge>
                    )}
                    {prediction.windowSummary.attributionSummary.activePlanets.map((planet, idx) => (
                      <Badge key={idx} variant="secondary" data-testid={`badge-planet-v1-${idx}`}>
                        {planet}
                      </Badge>
                    ))}
                  </div>
                  {prediction.windowSummary.attributionSummary.activeEngines.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Sources: {prediction.windowSummary.attributionSummary.activeEngines.join(", ")}
                    </p>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= V3: DANGER WINDOWS ================= */}
      {isV3 && prediction.dangerWindows && prediction.dangerWindows.length > 0 && (
        <Card data-testid="card-danger-windows" className="border-amber-500/30 dark:border-amber-400/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              Mindfulness Windows
            </CardTitle>
            <CardDescription>
              Periods requiring extra awareness and care
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" data-testid="list-danger-windows">
              {prediction.dangerWindows.map((window, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm" data-testid={`text-danger-window-${idx}`}>
                  <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                  <span>{window}</span>
                </li>
              ))}
            </ul>
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
            {isV3 ? "Detailed astrological insights by life domain" : isV2 ? "Detailed insights with opportunities and actions" : "Area-wise influence and interpretation"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Accordion type="single" collapsible className="w-full" data-testid="accordion-life-areas">
            {lifeAreas.map(area => (
              <LifeAreaCard key={area.key} area={area} isV2={isV2 || isV3} />
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* ================= V3: VEDA REMEDY (PARIHARAM) ================= */}
      {isV3 && prediction.vedaRemedy && (
        <Card data-testid="card-veda-remedy" className="border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flame className="h-5 w-5 text-primary" />
              Veda Pariharam (Remedies)
            </CardTitle>
            <CardDescription>
              Deity-specific traditional remedies for this period
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {prediction.vedaRemedy.primaryRemedy && (
              <div className="flex items-start gap-3" data-testid="section-primary-remedy">
                <Star className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Primary Remedy</p>
                  <Paragraphs text={prediction.vedaRemedy.primaryRemedy} className="text-sm" />
                </div>
              </div>
            )}

            {prediction.vedaRemedy.supportingPractice && (
              <div className="flex items-start gap-3" data-testid="section-supporting-practice">
                <Calendar className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Supporting Practice</p>
                  <Paragraphs text={prediction.vedaRemedy.supportingPractice} className="text-sm" />
                </div>
              </div>
            )}

            {prediction.vedaRemedy.specificRemedies && prediction.vedaRemedy.specificRemedies.length > 0 && (
              <div className="flex items-start gap-3 bg-muted/50 p-4 rounded-md" data-testid="section-specific-remedies">
                <BookOpen className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Additional Remedies</p>
                  <ul className="space-y-1 text-sm">
                    {prediction.vedaRemedy.specificRemedies.map((remedy, idx) => (
                      <li key={idx} data-testid={`text-specific-remedy-${idx}`}>
                        {remedy}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
              <div className="flex items-start gap-3 bg-muted/50 p-4 rounded-md" data-testid="section-reflection">
                <MessageCircle className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Reflection & Guidance</p>
                  <Paragraphs
                    text={prediction.practicesAndReflection.reflectionGuidance || prediction.practicesAndReflection.reflectionQuestion || ""}
                    className="text-sm"
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= V2/V3: CLOSING ================= */}
      {(isV2 || isV3) && prediction.closing && (
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
                <div data-testid="text-encouragement" className="text-base text-muted-foreground italic">
                  <Paragraphs text={prediction.closing.encouragement} />
                </div>
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
