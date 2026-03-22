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

function binduLabel(n: number): string {
  if (n >= 7) return "Very Strong";
  if (n >= 5) return "Strong";
  if (n >= 3) return "Moderate";
  return "Very Weak";
}

function getDrishtiNote(engine: string, envelope: any): string | null {
  if (!envelope) return null;
  let bonus: number | undefined;
  if (engine.includes("GOCHARA_JUPITER")) {
    bonus = envelope?.gochara?.jupiter?.drishti_aspect_bonus;
  } else if (engine.includes("GOCHARA_SATURN")) {
    bonus = envelope?.gochara?.saturn?.drishti_aspect_bonus;
  }
  if (bonus == null || Math.abs(bonus) < 0.15) return null;
  const pct = Math.round(Math.abs(bonus) * 100);
  return bonus < 0
    ? `Weakened by natal aspects (\u2212${pct}%)`
    : `Strengthened by natal aspects (+${pct}%)`;
}

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
  isV4: boolean;
  envelope?: any;
}

function LifeAreaCard({ area, isV2, isV4, envelope }: LifeAreaCardProps) {
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

        {isV4 && area.realLifePatterns && (
          <div className="bg-muted/50 p-3 rounded-md text-sm text-muted-foreground"
            data-testid={`text-patterns-${area.key}`}>
            <p className="text-xs font-medium uppercase tracking-wide mb-1">
              What You May Notice
            </p>
            <p>{area.realLifePatterns}</p>
          </div>
        )}

        {isV4 && ((area.doList?.length ?? 0) > 0 || (area.avoidList?.length ?? 0) > 0) && (
          <div className="grid grid-cols-2 gap-3 pt-1"
            data-testid={`section-do-avoid-${area.key}`}>
            {(area.doList?.length ?? 0) > 0 && (
              <div>
                <p className="text-xs font-medium text-green-700 dark:text-green-400
                   uppercase tracking-wide mb-2">
                  Do
                </p>
                <ul className="space-y-1">
                  {area.doList!.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm"
                      data-testid={`text-do-${area.key}-${idx}`}>
                      <CheckCircle className="h-3.5 w-3.5 text-green-600
                        dark:text-green-400 mt-0.5 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(area.avoidList?.length ?? 0) > 0 && (
              <div>
                <p className="text-xs font-medium text-amber-700 dark:text-amber-400
                   uppercase tracking-wide mb-2">
                  Avoid
                </p>
                <ul className="space-y-1">
                  {area.avoidList!.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm"
                      data-testid={`text-avoid-${area.key}-${idx}`}>
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-600
                        dark:text-amber-400 mt-0.5 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {isV4 && area.astrologicalBasis && (
          <p className="text-xs text-muted-foreground/70 italic pt-1 border-t border-border/30"
            data-testid={`text-basis-${area.key}`}>
            {area.astrologicalBasis}
          </p>
        )}

        {!isV2 && !isV4 && area.deeperExplanation && (
          <div className="bg-muted/50 p-3 rounded-md" data-testid={`text-explanation-${area.key}`}>
            <Paragraphs text={area.deeperExplanation} className="text-muted-foreground" />
          </div>
        )}

        {!isV2 && area.attribution?.signalsUsed && area.attribution.signalsUsed.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-border/40" data-testid={`section-signals-${area.key}`}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Signals</p>
            {area.attribution.signalsUsed.map((sig, idx) => {
              const sign = sig.weight >= 0 ? "+" : "";
              const drishtiNote = getDrishtiNote(sig.engine, envelope);
              return (
                <div key={idx} className="space-y-0.5">
                  <span className="font-mono text-xs text-muted-foreground">
                    {sig.engine}  {sign}{sig.weight.toFixed(2)}
                  </span>
                  {sig.interpretiveHint && (
                    <p className="text-xs text-muted-foreground italic pl-2">{sig.interpretiveHint}</p>
                  )}
                  {drishtiNote && (
                    <p className="text-xs text-muted-foreground/70 italic pl-2">{drishtiNote}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </AccordionContent>
    </AccordionItem>
  );
}

export function MonthlyPredictionView({
  prediction,
  period = "monthly",
  envelope,
}: {
  prediction: PredictionViewModel | null;
  period?: PredictionPeriod;
  envelope?: any;
}) {
  if (!prediction) {
    return null;
  }

  const { lifeAreas } = prediction;
  const isV4 = prediction.engineVersion === "ai-interpretation-v4.0";
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

      {/* ================= V4: EXECUTIVE SUMMARY ================= */}
      {isV4 && prediction.executiveSummary && (
        <Card data-testid="card-executive-summary"
          className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Your {period === "yearly" ? "Year" : "Month"} at a Glance
            </CardTitle>
            <CardDescription>
              {prediction.executiveSummary.yearInOneLine}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-base leading-relaxed">
              {prediction.executiveSummary.mainTheme}
            </p>
            <div className="grid grid-cols-2 gap-3 pt-2">
              {prediction.executiveSummary.strongestArea && (
                <div className="bg-green-50 dark:bg-green-950/30 rounded-md p-3">
                  <p className="text-xs font-medium text-green-700 dark:text-green-400
                     uppercase tracking-wide mb-1">
                    Strongest Area
                  </p>
                  <p className="text-sm">{prediction.executiveSummary.strongestArea}</p>
                </div>
              )}
              {prediction.executiveSummary.watchArea && (
                <div className="bg-amber-50 dark:bg-amber-950/30 rounded-md p-3">
                  <p className="text-xs font-medium text-amber-700 dark:text-amber-400
                     uppercase tracking-wide mb-1">
                    Watch Area
                  </p>
                  <p className="text-sm">{prediction.executiveSummary.watchArea}</p>
                </div>
              )}
            </div>
            {prediction.executiveSummary.bestUse && (
              <div className="bg-muted/50 rounded-md p-3">
                <p className="text-xs font-medium text-muted-foreground uppercase
                   tracking-wide mb-1">
                  Best Use of This Period
                </p>
                <p className="text-sm">{prediction.executiveSummary.bestUse}</p>
              </div>
            )}
            {prediction.executiveSummary.oneLines &&
             Object.keys(prediction.executiveSummary.oneLines).length > 0 && (
              <div className="space-y-2 pt-1 border-t border-border/40">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Area Snapshot
                </p>
                {Object.entries(prediction.executiveSummary.oneLines).map(([key, line]) => (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="font-medium capitalize min-w-[110px] text-muted-foreground">
                      {key.replace("_", " ")}
                    </span>
                    <span>{line}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================= V4: WHY THIS PERIOD ================= */}
      {isV4 && prediction.whyThisPeriod && (
        <Card data-testid="card-why-this-period">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Why This Period Feels This Way
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-base leading-relaxed">
              {prediction.whyThisPeriod.dashaPlain}
            </p>
            <p className="text-base leading-relaxed text-muted-foreground">
              {prediction.whyThisPeriod.transitPlain}
            </p>
            {prediction.whyThisPeriod.overlapSummary && (
              <div className="bg-muted/50 rounded-md p-3 text-sm italic">
                {prediction.whyThisPeriod.overlapSummary}
              </div>
            )}
            <div className="grid grid-cols-2 gap-3 pt-1">
              {prediction.whyThisPeriod.supportive?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-700 dark:text-green-400
                     uppercase tracking-wide mb-2">
                    Working For You
                  </p>
                  <ul className="space-y-1">
                    {prediction.whyThisPeriod.supportive.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <CheckCircle className="h-3.5 w-3.5 text-green-600
                          dark:text-green-400 mt-0.5 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {prediction.whyThisPeriod.watchouts?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-amber-700 dark:text-amber-400
                     uppercase tracking-wide mb-2">
                    Watch Out For
                  </p>
                  <ul className="space-y-1">
                    {prediction.whyThisPeriod.watchouts.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-600
                          dark:text-amber-400 mt-0.5 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

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
      {!isV2 && !isV3 && !isV4 && prediction.windowSummary && (
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

      {/* ================= V4: CAUTION WINDOWS ================= */}
      {isV4 && prediction.cautionWindows &&
       prediction.cautionWindows.length > 0 && (
        <Card data-testid="card-caution-windows-v4"
          className="border-amber-500/30 dark:border-amber-400/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              Mindfulness Windows
            </CardTitle>
            <CardDescription>
              Dates and patterns that call for extra care
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" data-testid="list-caution-windows-v4">
              {prediction.cautionWindows.map((window, idx) => (
                <li key={idx}
                  className="flex items-start gap-2 text-sm"
                  data-testid={`text-caution-window-${idx}`}>
                  <AlertTriangle className="h-4 w-4 text-amber-600
                    dark:text-amber-400 mt-0.5 shrink-0" />
                  <span>{window}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* ================= TRANSIT STRENGTH (ENHANCEMENT A) ================= */}
      {envelope?.gochara && (
        <Card data-testid="card-transit-strength">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4" />
              Transit Influences
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {(() => {
                const jup = envelope.gochara.jupiter;
                const bindus = envelope.ashtakavarga?.jupiter?.bindus;
                return (
                  <div className="space-y-1" data-testid="transit-jupiter">
                    <span className="font-medium">Jupiter in {jup?.transit_rasi}</span>
                    {bindus != null && (
                      <div>
                        <Badge variant="outline" className="text-xs">
                          {bindus}/8 bindus · {binduLabel(bindus)}
                        </Badge>
                      </div>
                    )}
                  </div>
                );
              })()}
              {(() => {
                const sat = envelope.gochara.saturn;
                const bindus = envelope.ashtakavarga?.saturn?.bindus;
                return (
                  <div className="space-y-1" data-testid="transit-saturn">
                    <span className="font-medium">Saturn in {sat?.transit_rasi}</span>
                    {bindus != null && (
                      <div>
                        <Badge variant="outline" className="text-xs">
                          {bindus}/8 bindus · {binduLabel(bindus)}
                        </Badge>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
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
            {isV4 ? "Plain-English guidance for each life area" : isV3 ? "Detailed astrological insights by life domain" : isV2 ? "Detailed insights with opportunities and actions" : "Area-wise influence and interpretation"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Accordion type="single" collapsible className="w-full" data-testid="accordion-life-areas">
            {lifeAreas.map(area => (
              <LifeAreaCard key={area.key} area={area}
                isV2={isV2 || isV3} isV4={isV4} envelope={envelope} />
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

      {/* ================= V4: REMEDIES ================= */}
      {isV4 && prediction.remediesV4 && (
        <Card data-testid="card-remedies-v4" className="border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flame className="h-5 w-5 text-primary" />
              Remedies & Practices
            </CardTitle>
            <CardDescription>
              Traditional remedies with practical alternatives
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {prediction.remediesV4.primary && (
              <div className="space-y-3" data-testid="section-primary-remedy-v4">
                <div className="flex items-start gap-3">
                  <Star className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <div className="space-y-2 flex-1">
                    <p className="text-sm font-medium text-muted-foreground">
                      Primary Remedy
                    </p>
                    <p className="text-sm">
                      {prediction.remediesV4.primary.traditional}
                    </p>
                    {prediction.remediesV4.primary.simplePractice && (
                      <div className="bg-muted/50 rounded p-2">
                        <p className="text-xs font-medium text-muted-foreground mb-0.5">
                          Simple Alternative
                        </p>
                        <p className="text-sm">
                          {prediction.remediesV4.primary.simplePractice}
                        </p>
                      </div>
                    )}
                    {prediction.remediesV4.primary.purpose && (
                      <p className="text-xs text-muted-foreground italic">
                        Purpose: {prediction.remediesV4.primary.purpose}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
            {prediction.remediesV4.supporting &&
             prediction.remediesV4.supporting.traditional && (
              <>
                <Separator />
                <div className="flex items-start gap-3"
                  data-testid="section-supporting-remedy-v4">
                  <Calendar className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <div className="space-y-2 flex-1">
                    <p className="text-sm font-medium text-muted-foreground">
                      Supporting Practice
                    </p>
                    <p className="text-sm">
                      {prediction.remediesV4.supporting.traditional}
                    </p>
                    {prediction.remediesV4.supporting.simplePractice && (
                      <div className="bg-muted/50 rounded p-2">
                        <p className="text-xs font-medium text-muted-foreground mb-0.5">
                          Simple Alternative
                        </p>
                        <p className="text-sm">
                          {prediction.remediesV4.supporting.simplePractice}
                        </p>
                      </div>
                    )}
                    {prediction.remediesV4.supporting.purpose && (
                      <p className="text-xs text-muted-foreground italic">
                        Purpose: {prediction.remediesV4.supporting.purpose}
                      </p>
                    )}
                  </div>
                </div>
              </>
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

      {/* ================= V4: KEY TAKEAWAYS ================= */}
      {isV4 && prediction.keyTakeawaysV4 &&
       prediction.keyTakeawaysV4.length > 0 && (
        <Card data-testid="card-takeaways-v4" className="border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Heart className="h-5 w-5 text-primary" />
              Key Takeaways
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" data-testid="section-takeaways-v4">
              {prediction.keyTakeawaysV4.map((takeaway, idx) => (
                <li key={idx}
                  className="flex items-start gap-2"
                  data-testid={`text-takeaway-v4-${idx}`}>
                  <CheckCircle className="h-4 w-4 text-green-600
                    dark:text-green-400 mt-0.5 shrink-0" />
                  <span className="text-sm">{takeaway}</span>
                </li>
              ))}
            </ul>
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
