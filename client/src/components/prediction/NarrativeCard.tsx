import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";

interface NarrativeCardProps {
  narrative: {
    overview: string;
    emotional_tone: string;
    what_to_expect: string[];
    how_to_work_with_this_period: string[];
    closing_reflection: string;
  };
}

export function NarrativeCard({ narrative }: NarrativeCardProps) {
  return (
    <Card className="bg-muted/30 border">
      <CardHeader>
        <CardTitle className="text-base">
          This Period in Plain Language
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 text-sm leading-relaxed">
        <p>{narrative.overview}</p>
        <p>{narrative.emotional_tone}</p>

        {narrative.what_to_expect.length > 0 && (
          <ul className="list-disc pl-5 space-y-1">
            {narrative.what_to_expect.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        )}

        {narrative.how_to_work_with_this_period.length > 0 && (
          <ul className="list-disc pl-5 space-y-1">
            {narrative.how_to_work_with_this_period.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        )}

        <p className="italic text-muted-foreground">
          {narrative.closing_reflection}
        </p>
      </CardContent>
    </Card>
  );
}
