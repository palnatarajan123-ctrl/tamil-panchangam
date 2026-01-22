import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function LifeAreaCard({
  title,
  score,
  confidence,
}: {
  title: string;
  score: number;
  confidence: number;
}) {
  const tone =
    score >= 70 ? "text-green-600"
    : score >= 40 ? "text-muted-foreground"
    : "text-orange-600";

  return (
    <Card>
      <CardContent className="p-4 space-y-2">
        <div className="font-medium">{title}</div>
        <div className={cn("text-2xl font-bold", tone)}>
          {score}
        </div>
        <div className="text-xs text-muted-foreground">
          Confidence: {Math.round(confidence * 100)}%
        </div>
      </CardContent>
    </Card>
  );
}
