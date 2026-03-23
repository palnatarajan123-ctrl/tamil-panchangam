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
  who_you_are?: {
    core_identity: string;
    in_one_line: string;
    core_strengths: string[];
    growth_edges: string[];
    central_tension: string;
  };
  where_you_shine?: {
    natural_domains: string[];
    why: string;
    working_style: string;
  };
  relationships_and_family?: {
    partnership_nature: string;
    marriage_windows: string;
    children_indication: string;
    family_dynamics: string;
  };
  current_chapter?: {
    dasha_now: string;
    what_this_means: string;
    focus_for_now: string;
  };
  life_by_decade?: Array<{
    age_range: string;
    theme: string;
    key_focus: string;
    dasha_context: string;
  }>;
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
            {(() => { const isV2 = interp.engine_version === "natal-v2.0"; return (
            <>
          {/* V2: WHO YOU ARE */}
          {isV2 && interp.who_you_are && (
            <div className="space-y-3">
              <h3 className="text-base font-semibold">Who You Are</h3>
              {interp.who_you_are.in_one_line && (
                <p className="text-sm italic text-muted-foreground border-l-2 border-primary/40 pl-3">
                  {interp.who_you_are.in_one_line}
                </p>
              )}
              {interp.who_you_are.core_identity && (
                <p className="text-sm leading-relaxed">
                  {interp.who_you_are.core_identity}
                </p>
              )}
              {(interp.who_you_are.core_strengths?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Core Strengths
                  </p>
                  <ul className="space-y-1">
                    {interp.who_you_are.core_strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm bg-green-50 dark:bg-green-950/30 rounded px-3 py-2">
                        <span className="text-green-600 dark:text-green-400 font-bold mt-0.5 shrink-0">+</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(interp.who_you_are.growth_edges?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Growth Edges
                  </p>
                  <ul className="space-y-1">
                    {interp.who_you_are.growth_edges.map((g, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm bg-purple-50 dark:bg-purple-950/30 rounded px-3 py-2">
                        <span className="text-purple-600 dark:text-purple-400 font-bold mt-0.5 shrink-0">→</span>
                        {g}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {interp.who_you_are.central_tension && (
                <div className="bg-amber-50 dark:bg-amber-950/30 rounded px-3 py-2 border-l-2 border-amber-400">
                  <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide mb-1">
                    Central Life Tension
                  </p>
                  <p className="text-sm">{interp.who_you_are.central_tension}</p>
                </div>
              )}
            </div>
          )}

          {/* V2: WHERE YOU SHINE */}
          {isV2 && interp.where_you_shine && (
            <div className="space-y-2">
              <h3 className="text-base font-semibold">Where You Shine</h3>
              {(interp.where_you_shine.natural_domains?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-2">
                  {interp.where_you_shine.natural_domains.map((d, i) => (
                    <span key={i} className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 text-xs font-medium px-2.5 py-1 rounded-full">
                      {d}
                    </span>
                  ))}
                </div>
              )}
              {interp.where_you_shine.why && (
                <p className="text-sm text-muted-foreground">{interp.where_you_shine.why}</p>
              )}
              {interp.where_you_shine.working_style && (
                <p className="text-sm italic text-muted-foreground">{interp.where_you_shine.working_style}</p>
              )}
            </div>
          )}

          {/* V2: RELATIONSHIPS AND FAMILY */}
          {isV2 && interp.relationships_and_family && (
            <div className="space-y-2">
              <h3 className="text-base font-semibold">Relationships &amp; Family</h3>
              {interp.relationships_and_family.partnership_nature && (
                <div className="rounded px-3 py-2 bg-purple-50 dark:bg-purple-950/20">
                  <p className="text-xs font-semibold text-purple-700 dark:text-purple-400 uppercase tracking-wide mb-1">Partnership Nature</p>
                  <p className="text-sm">{interp.relationships_and_family.partnership_nature}</p>
                </div>
              )}
              {interp.relationships_and_family.marriage_windows && (
                <div className="rounded px-3 py-2 bg-green-50 dark:bg-green-950/20">
                  <p className="text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wide mb-1">Marriage Windows</p>
                  <p className="text-sm">{interp.relationships_and_family.marriage_windows}</p>
                </div>
              )}
              {interp.relationships_and_family.children_indication && (
                <div className="rounded px-3 py-2 bg-blue-50 dark:bg-blue-950/20">
                  <p className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide mb-1">Children</p>
                  <p className="text-sm">{interp.relationships_and_family.children_indication}</p>
                </div>
              )}
              {interp.relationships_and_family.family_dynamics && (
                <div className="rounded px-3 py-2 bg-muted/40">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Family Dynamics</p>
                  <p className="text-sm">{interp.relationships_and_family.family_dynamics}</p>
                </div>
              )}
            </div>
          )}

          {/* V2: CURRENT CHAPTER */}
          {isV2 && interp.current_chapter && (
            <div className="space-y-2 bg-muted/30 rounded-lg p-4">
              <h3 className="text-base font-semibold">Your Current Chapter</h3>
              {interp.current_chapter.dasha_now && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Active period:</span>{" "}
                  {interp.current_chapter.dasha_now}
                </p>
              )}
              {interp.current_chapter.what_this_means && (
                <p className="text-sm leading-relaxed">{interp.current_chapter.what_this_means}</p>
              )}
              {interp.current_chapter.focus_for_now && (
                <div className="bg-primary/10 rounded px-3 py-2 border-l-2 border-primary">
                  <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-0.5">Focus Now</p>
                  <p className="text-sm">{interp.current_chapter.focus_for_now}</p>
                </div>
              )}
            </div>
          )}

          {/* V2: LIFE BY DECADE */}
          {isV2 && (interp.life_by_decade?.length ?? 0) > 0 && (
            <div className="space-y-2">
              <h3 className="text-base font-semibold">Life by Decade</h3>
              <div className="space-y-2">
                {interp.life_by_decade!.map((d, i) => (
                  <div key={i} className="flex gap-3 items-start border-b border-border/30 pb-2 last:border-0">
                    <div className="flex-shrink-0 w-14 text-right">
                      <span className="text-xs font-mono font-semibold text-primary">{d.age_range}</span>
                    </div>
                    <div className="flex-1 space-y-0.5">
                      <p className="text-sm font-medium">{d.theme}</p>
                      <p className="text-xs text-muted-foreground">{d.key_focus}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

            {/* V1 only: Life Theme */}
            {!isV2 && interp.life_theme?.title && (
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
            </>
            ); })()}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
