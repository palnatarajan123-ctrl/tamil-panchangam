import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";

interface AntarRemediesCardProps {
  remedies: {
    recommended: string[];
    supportive: string[];
    avoid: string[];
  };
  cautionLevel?: "low" | "medium" | "high";
}

export function AntarRemediesCard({
  remedies,
  cautionLevel = "low",
}: AntarRemediesCardProps) {
  const cautionColor =
    cautionLevel === "high"
      ? "destructive"
      : cautionLevel === "medium"
      ? "secondary"
      : "outline";

  return (
    <Card className="border bg-muted/20">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          Remedies & Guidance
          <Badge variant={cautionColor} className="capitalize">
            {cautionLevel} caution
          </Badge>
        </CardTitle>
        <CardDescription>
          Practical actions to align with the current Antar Dasha.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6 text-sm">
        {/* Recommended */}
        {remedies.recommended?.length > 0 && (
          <div>
            <div className="font-medium mb-1">Recommended</div>
            <ul className="list-disc pl-5 space-y-1">
              {remedies.recommended.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Supportive */}
        {remedies.supportive?.length > 0 && (
          <div>
            <div className="font-medium mb-1">Supportive Practices</div>
            <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
              {remedies.supportive.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Avoid */}
        {remedies.avoid?.length > 0 && (
          <div>
            <div className="font-medium mb-1 text-destructive">
              Use Caution / Avoid
            </div>
            <ul className="list-disc pl-5 space-y-1">
              {remedies.avoid.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
