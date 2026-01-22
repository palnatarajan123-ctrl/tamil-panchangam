// client/src/components/prediction/AntarExplanationCard.tsx

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

interface AntarExplanationCardProps {
  antar: {
    lord: string;
    start: string;
    end: string;
    confidence_weight?: number;
  };
  explanation?: {
    summary: string;
    themes?: string[];
    caution?: string[];
  } | null;
}

export function AntarExplanationCard({
  antar,
  explanation,
}: AntarExplanationCardProps) {
  return (
    <Card className="bg-muted/30 border">
      <CardHeader>
        <CardTitle className="text-base">
          Active Antar Dasha · What This Means
        </CardTitle>
        <CardDescription>
          Sub-period influence operating within the current Mahadasha.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <div>
          <span className="font-medium">Antar Lord:</span>{" "}
          <span className="font-semibold">{antar.lord}</span>
        </div>

        <div>
          <span className="font-medium">Duration:</span>{" "}
          {antar.start} → {antar.end}
        </div>

        {antar.confidence_weight !== undefined && (
          <div>
            <span className="font-medium">Influence Strength:</span>{" "}
            {Math.round(antar.confidence_weight * 100)}%
          </div>
        )}

        {/* Narrative (EPIC-6.3) */}
        {explanation?.summary && (
          <div className="pt-2 text-muted-foreground leading-relaxed">
            {explanation.summary}
          </div>
        )}

        {explanation?.themes?.length ? (
          <ul className="list-disc pl-5">
            {explanation.themes.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        ) : null}

        {explanation?.caution?.length ? (
          <>
            <div className="pt-2 font-medium">Be mindful of:</div>
            <ul className="list-disc pl-5 text-red-500/80">
              {explanation.caution.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
