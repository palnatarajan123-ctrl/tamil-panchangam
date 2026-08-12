import { useQuery } from "@tanstack/react-query";
import { Layers, Sparkles } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { getAccessToken } from "@/lib/auth";

// ── Types ───────────────────────────────────────────────────────────────────

interface KpLifeArea {
  summary: string;
  practical_note: string;
}

interface KpInterpretation {
  engine_version: string;
  overall_summary: string;
  life_areas: {
    wealth?: KpLifeArea;
    health?: KpLifeArea;
    relationships?: KpLifeArea;
    longevity_and_transformation?: KpLifeArea;
    career?: KpLifeArea;
    gains_and_goals?: KpLifeArea;
  };
  llm_disabled?: boolean;
  llm_error?: string;
}

const AREA_LABELS: Record<string, string> = {
  career:                    "Career & Calling",
  wealth:                    "Wealth & Money",
  health:                    "Health & Vitality",
  relationships:             "Relationships & Partnership",
  longevity_and_transformation: "Longevity & Transformation",
  gains_and_goals:           "Gains & Long-term Goals",
};

// ── Loading skeleton ────────────────────────────────────────────────────────

function KpSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Sparkles className="h-4 w-4 animate-pulse text-primary" />
        Computing KP natal insights…
      </div>
      <Skeleton className="h-16 w-full" />
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </div>
  );
}

// ── Card ────────────────────────────────────────────────────────────────────

export function KpInsightCard({ chartId }: { chartId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["/api/chart/kp-interpretation", chartId],
    queryFn: async () => {
      const token = getAccessToken();
      const res = await fetch(`/api/chart/${chartId}/kp-interpretation`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("KP interpretation request failed");
      return res.json() as Promise<{
        kp_available: boolean;
        interpretation: KpInterpretation | null;
        cached: boolean;
        llm_disabled?: boolean;
      }>;
    },
    staleTime: Infinity,
    retry: false,
  });

  // Server said no KP data for this chart — render nothing
  if (!isLoading && data && !data.kp_available) return null;

  const interp = data?.interpretation ?? null;

  return (
    <Card className="border-muted" data-testid="card-kp-insight">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-primary" />
          KP Natal Insights
        </CardTitle>
        <CardDescription>
          Krishnamurti Paddhati — life-area blueprint from house significators
        </CardDescription>
      </CardHeader>

      <CardContent>
        {isLoading && <KpSkeleton />}

        {error && (
          <p className="text-sm text-muted-foreground">
            Unable to load KP insights. Please try again.
          </p>
        )}

        {!isLoading && !error && (data?.llm_disabled || interp?.llm_disabled) && (
          <p className="text-sm text-muted-foreground italic">
            Enable AI interpretation in admin settings to see KP natal insights.
          </p>
        )}

        {!isLoading && !error && interp && !interp.llm_disabled && (
          <div className="space-y-5">
            {/* Overall summary */}
            {interp.overall_summary && (
              <p className="text-sm leading-relaxed text-muted-foreground border-l-2 border-primary/40 pl-3">
                {interp.overall_summary}
              </p>
            )}

            {/* Life areas */}
            {interp.life_areas && Object.keys(interp.life_areas).length > 0 && (
              <Accordion type="single" collapsible className="space-y-1">
                {Object.entries(interp.life_areas)
                  .filter(([, area]) => area && (area.summary || area.practical_note))
                  .map(([key, area]) => (
                    <AccordionItem
                      key={key}
                      value={key}
                      className="border rounded-lg px-4"
                    >
                      <AccordionTrigger className="text-sm py-3">
                        {AREA_LABELS[key] ?? key}
                      </AccordionTrigger>
                      <AccordionContent className="pb-3 space-y-3">
                        {area!.summary && (
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {area!.summary}
                          </p>
                        )}
                        {area!.practical_note && (
                          <div className="bg-primary/10 rounded px-3 py-2 border-l-2 border-primary">
                            <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-0.5">
                              Key takeaway
                            </p>
                            <p className="text-sm">{area!.practical_note}</p>
                          </div>
                        )}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
              </Accordion>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
