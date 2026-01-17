import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { Info } from "lucide-react";

interface ExplainabilityDrawerProps {
  explainability?: {
    summary?: string;
    dominant_dasha?: string;
    transit_highlights?: string[];
  };
}

export function ExplainabilityDrawer({
  explainability,
}: ExplainabilityDrawerProps) {
  // 🔒 HARD GUARD — do not mount unless there is real content
  if (
    !explainability ||
    (!explainability.summary &&
      !explainability.dominant_dasha &&
      (!explainability.transit_highlights ||
        explainability.transit_highlights.length === 0))
  ) {
    return null;
  }

  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button variant="outline" className="w-full mt-4 gap-2">
          <Info className="h-4 w-4" />
          Why this prediction?
        </Button>
      </DrawerTrigger>

      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Prediction Explainability</DrawerTitle>
        </DrawerHeader>

        <div className="p-6 space-y-4 text-sm">
          {explainability.summary && (
            <div>
              <div className="font-medium mb-1">Overview</div>
              <p className="text-muted-foreground">
                {explainability.summary}
              </p>
            </div>
          )}

          {explainability.dominant_dasha && (
            <div>
              <div className="font-medium mb-1">Dominant Dasha</div>
              <p className="text-muted-foreground">
                {explainability.dominant_dasha}
              </p>
            </div>
          )}

          {explainability.transit_highlights &&
            explainability.transit_highlights.length > 0 && (
              <div>
                <div className="font-medium mb-1">Key Transits</div>
                <ul className="list-disc pl-5 text-muted-foreground space-y-1">
                  {explainability.transit_highlights.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}
