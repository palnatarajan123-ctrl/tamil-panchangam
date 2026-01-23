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
  Clock,
} from "lucide-react";

/* -----------------------------------------------------
   Types (UI read model)
----------------------------------------------------- */

interface MonthlyPredictionUIModel {
  meta?: {
    generated_at?: string;
    engine_version?: string;
  };

  overview?: {
    confidence?: number;
    overall_score?: number;
    tone?: string;
  };

  life_areas?: {
    key: string;
    label: string;
    score: number;
    confidence: number;
    sentiment: string;
    summary: string;
    detail: string;
  }[];

  timing?: {
    dominant_pakshi?: string;
    recommended?: string[];
    avoid?: string[];
    note?: string;
  };

  disclaimers?: string[];
}

type PredictionPeriod = "weekly" | "monthly" | "yearly";

/* -----------------------------------------------------
   Component
----------------------------------------------------- */

export function MonthlyPredictionView({
  prediction,
  period,
}: {
  prediction: MonthlyPredictionUIModel | null;
  period: PredictionPeriod;
}) {
  const lifeAreas = Array.isArray(prediction?.life_areas)
    ? prediction.life_areas
    : [];

  const timing = {
    dominant_pakshi: prediction?.timing?.dominant_pakshi,
    recommended: Array.isArray(prediction?.timing?.recommended)
      ? prediction.timing.recommended
      : [],
    avoid: Array.isArray(prediction?.timing?.avoid)
      ? prediction.timing.avoid
      : [],
    note: prediction?.timing?.note,
  };

  const disclaimers = Array.isArray(prediction?.disclaimers)
    ? prediction.disclaimers
    : [];

  if (!prediction || lifeAreas.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-12">
        Prediction data not available yet.
      </div>
    );
  }

  /* -----------------------------------------------------
     Period-aware labels (AUTHORITATIVE)
  ----------------------------------------------------- */

  const periodLabel =
    period === "weekly"
      ? "Weekly Prediction"
      : period === "yearly"
      ? "Yearly Prediction"
      : "Monthly Prediction";

  const overviewHeadline =
    period === "weekly"
      ? "Overall weekly influence summary"
      : period === "yearly"
      ? "Overall yearly influence summary"
      : "Overall monthly influence summary";

  /* -----------------------------------------------------
     UI
  ----------------------------------------------------- */

  return (
    <div className="space-y-6">

      {/* ================= OVERVIEW ================= */}
      {prediction.overview && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Prediction Overview
            </CardTitle>

            {/* Single, clean period label */}
            <CardDescription>{periodLabel}</CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <p className="text-lg font-medium">
              {overviewHeadline}
            </p>

            <div className="flex items-center gap-3 text-sm">
              {prediction.overview.tone && (
                <Badge variant="secondary">
                  {prediction.overview.tone}
                </Badge>
              )}

              {prediction.overview.overall_score !== undefined && (
                <span>
                  Overall Score:{" "}
                  <strong>{prediction.overview.overall_score}</strong>
                </span>
              )}

              {prediction.overview.confidence !== undefined && (
                <span className="text-muted-foreground">
                  Confidence{" "}
                  {Math.round(prediction.overview.confidence * 100)}%
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================= LIFE AREAS ================= */}
      <Card>
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
          <Accordion type="single" collapsible className="w-full">
            {lifeAreas.map(area => (
              <AccordionItem key={area.key} value={area.key}>
                <AccordionTrigger>
                  <div className="flex items-center gap-3">
                    <span>{area.label}</span>
                    <Badge variant="outline">
                      {area.sentiment}
                    </Badge>
                    <span className="text-muted-foreground text-sm">
                      {area.score}
                    </span>
                  </div>
                </AccordionTrigger>

                <AccordionContent className="space-y-2 text-sm">
                  <p>{area.summary}</p>
                  {area.detail && (
                    <p className="text-muted-foreground">{area.detail}</p>
                  )}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* ================= TIMING ================= */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Timing & Rhythm
          </CardTitle>
          <CardDescription>
            Pancha Pakshi influence
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 text-sm">
          {timing.dominant_pakshi && (
            <div>
              <strong>Dominant Pakshi:</strong>{" "}
              {timing.dominant_pakshi}
            </div>
          )}

          {!timing.dominant_pakshi && timing.note && (
            <div className="text-muted-foreground leading-relaxed">
              {timing.note}
            </div>
          )}

          {timing.recommended.length > 0 && (
            <>
              <Separator />
              <div>
                <strong>Recommended:</strong>
                <ul className="list-disc ml-5 mt-1">
                  {timing.recommended.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {timing.avoid.length > 0 && (
            <>
              <Separator />
              <div>
                <strong>Avoid:</strong>
                <ul className="list-disc ml-5 mt-1">
                  {timing.avoid.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* ================= DISCLAIMERS ================= */}
      {disclaimers.length > 0 && (
        <Card>
          <CardContent className="text-xs text-muted-foreground space-y-1">
            {disclaimers.map((d, i) => (
              <p key={i}>• {d}</p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
