import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, BookOpen, ChevronDown, ChevronUp, Download, Loader2 } from "lucide-react";
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
import { apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { getAccessToken } from "@/lib/auth";

// ── Types ───────────────────────────────────────────────────────────────────

interface DashaEntry {
  mahadasha: string;
  approximate_age: string;
  theme: string;
}

interface NatalInterpretation {
  engine_version: string;
  life_theme: { title: string; narrative: string };
  chart_highlights: {
    lagna_interpretation: string;
    moon_interpretation: string;
    strongest_influence: string;
    key_yoga_impact: string;
  };
  life_areas: {
    career: string;
    wealth: string;
    relationships: string;
    health: string;
    spirituality: string;
  };
  dasha_life_map: DashaEntry[];
  closing_wisdom: string;
  llm_disabled?: boolean;
}

const LIFE_AREA_LABELS: Record<string, string> = {
  career:        "Career & Purpose",
  wealth:        "Wealth & Resources",
  relationships: "Relationships",
  health:        "Health & Vitality",
  spirituality:  "Spirituality & Moksha",
};

const HIGHLIGHT_LABELS: Record<string, string> = {
  lagna_interpretation: "Ascendant (Lagna)",
  moon_interpretation:  "Moon & Nakshatra",
  strongest_influence:  "Strongest Planet",
  key_yoga_impact:      "Key Yoga",
};

// ── Sub-components ──────────────────────────────────────────────────────────

function HighlightGrid({ highlights }: { highlights: NatalInterpretation["chart_highlights"] }) {
  const entries = Object.entries(highlights).filter(([, v]) => v);
  if (!entries.length) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {entries.map(([key, text]) => (
        <div key={key} className="rounded-lg border border-border/50 bg-muted/20 p-3 space-y-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {HIGHLIGHT_LABELS[key] ?? key}
          </p>
          <p className="text-sm leading-relaxed">{text}</p>
        </div>
      ))}
    </div>
  );
}

function DashaLifeMap({ entries }: { entries: DashaEntry[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!entries.length) return null;
  const visible = expanded ? entries : entries.slice(0, 4);

  return (
    <div>
      <p className="text-sm font-semibold mb-3">Dasha Life Map</p>
      <div className="space-y-2">
        {visible.map((d, i) => (
          <div key={i} className="flex gap-3 items-start">
            <div className="flex-shrink-0 w-24 text-right">
              <span className="text-xs font-mono text-muted-foreground">{d.approximate_age}</span>
            </div>
            <div className="flex-shrink-0 w-20">
              <span className="text-xs font-medium text-primary">{d.mahadasha}</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed flex-1">{d.theme}</p>
          </div>
        ))}
      </div>
      {entries.length > 4 && (
        <button
          className="mt-2 text-xs text-primary flex items-center gap-1"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded
            ? <><ChevronUp className="h-3 w-3" /> Show less</>
            : <><ChevronDown className="h-3 w-3" /> Show all {entries.length} Dashas</>
          }
        </button>
      )}
    </div>
  );
}

// ── Loading skeleton ────────────────────────────────────────────────────────

function NatalSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Sparkles className="h-4 w-4 animate-pulse text-primary" />
        Consulting the stars…
      </div>
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-16 w-full" />
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <Skeleton className="h-32 w-full" />
    </div>
  );
}

// ── Panel ───────────────────────────────────────────────────────────────────

export function NatalInterpretationPanel({ chartId }: { chartId: string }) {
  const [downloading, setDownloading] = useState(false);

  async function downloadPdf() {
    setDownloading(true);
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/reports/birth-chart-pdf?base_chart_id=${chartId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `natal_chart_${chartId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ["/api/chart/natal-interpretation", chartId],
    queryFn: async () => {
      const res = await apiRequest("POST", "/api/chart/natal-interpretation", {
        base_chart_id: chartId,
      });
      return res.json();
    },
    staleTime: Infinity, // never re-fetch once loaded
    retry: false,
  });

  const interp: NatalInterpretation | null = data?.interpretation ?? null;

  return (
    <Card className="border-muted" data-testid="card-natal-interpretation">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-primary" />
              Natal Chart Reading
            </CardTitle>
            <CardDescription>Your lifelong astrological blueprint</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-2 shrink-0"
            onClick={downloadPdf}
            disabled={downloading}
            title="Download natal chart as PDF"
          >
            {downloading
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Download className="h-4 w-4" />
            }
            <span className="hidden sm:inline">PDF</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading && <NatalSkeleton />}

        {error && (
          <p className="text-sm text-muted-foreground">
            Unable to load natal reading. Please try again.
          </p>
        )}

        {!isLoading && !error && interp?.llm_disabled && (
          <p className="text-sm text-muted-foreground italic">
            Enable AI interpretation in admin settings to see your natal chart reading.
          </p>
        )}

        {!isLoading && !error && interp && !interp.llm_disabled && (
          <div className="space-y-6">
            {/* Life Theme */}
            {interp.life_theme?.title && (
              <div className="space-y-2">
                <h3 className="text-lg font-serif font-semibold text-amber-400">
                  {interp.life_theme.title}
                </h3>
                {interp.life_theme.narrative && (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {interp.life_theme.narrative}
                  </p>
                )}
              </div>
            )}

            {/* Chart Highlights */}
            {interp.chart_highlights && (
              <HighlightGrid highlights={interp.chart_highlights} />
            )}

            {/* Life Areas */}
            {interp.life_areas && Object.values(interp.life_areas).some(Boolean) && (
              <div>
                <p className="text-sm font-semibold mb-2">Life Area Blueprint</p>
                <Accordion type="single" collapsible className="space-y-1">
                  {Object.entries(interp.life_areas)
                    .filter(([, v]) => v)
                    .map(([key, text]) => (
                      <AccordionItem
                        key={key}
                        value={key}
                        className="border rounded-lg px-4"
                      >
                        <AccordionTrigger className="text-sm py-3">
                          {LIFE_AREA_LABELS[key] ?? key}
                        </AccordionTrigger>
                        <AccordionContent className="text-sm text-muted-foreground pb-3">
                          {text}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                </Accordion>
              </div>
            )}

            {/* Dasha Life Map */}
            {interp.dasha_life_map?.length > 0 && (
              <DashaLifeMap entries={interp.dasha_life_map} />
            )}

            {/* Closing Wisdom */}
            {interp.closing_wisdom && (
              <p className="text-sm italic text-muted-foreground text-center border-t border-border/40 pt-4">
                {interp.closing_wisdom}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
