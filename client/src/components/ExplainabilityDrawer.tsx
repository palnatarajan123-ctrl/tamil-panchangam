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
    active_lords?: string[];
    maha_lord?: string;
    antar_lord?: string | null;
    confidence?: {
      overall?: number;
      variance?: number;
    };
  };
}

function confidenceLabel(v?: number) {
  if (v === undefined) return "moderate";
  if (v >= 0.75) return "high";
  if (v >= 0.55) return "moderate";
  return "low";
}

export function ExplainabilityDrawer({
  explainability,
}: ExplainabilityDrawerProps) {
  if (!explainability) return null;

  const {
    maha_lord,
    antar_lord,
    active_lords,
    confidence,
  } = explainability;

  const confidenceText = confidenceLabel(confidence?.overall);

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
          <DrawerTitle>Why this prediction</DrawerTitle>
        </DrawerHeader>

        <div className="p-6 space-y-4 text-sm text-muted-foreground">
          {/* Dasha explanation */}
          {maha_lord && (
            <p>
              This period is primarily influenced by{" "}
              <span className="font-medium text-foreground">
                {maha_lord}
              </span>
              {antar_lord && (
                <>
                  , with a secondary influence from{" "}
                  <span className="font-medium text-foreground">
                    {antar_lord}
                  </span>
                </>
              )}
              .
            </p>
          )}

          {/* Active lords */}
          {active_lords && active_lords.length > 0 && (
            <p>
              Active planetary influences this period include{" "}
              <span className="font-medium text-foreground">
                {active_lords.join(", ")}
              </span>
              .
            </p>
          )}

          {/* Confidence */}
          <p>
            Overall confidence in this prediction is{" "}
            <span className="font-medium text-foreground">
              {confidenceText}
            </span>
            , based on the stability and consistency of signals across life
            areas.
          </p>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
