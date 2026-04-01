import { useState } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ChatPanel } from "@/components/ChatPanel";
import {
  Loader2, RefreshCw, MessageCircle, ArrowLeft,
  Star, Heart,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ChildrenWindow {
  period: string;
  strength: "strong" | "moderate" | "mild";
  basis: string;
  plain_english: string;
  cautions: string | null;
}

interface ChildrenTimingData {
  cached: boolean;
  group_id: string;
  year_from: number;
  year_to: number;
  has_children_already: boolean;
  overall_outlook: string;
  combined_windows: ChildrenWindow[];
  jupiter_transits: unknown[];
  jupiter_insight: string;
  remedies: string[];
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(method: string, path: string, body?: unknown) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Badge ──────────────────────────────────────────────────────────────────────

const STRENGTH_CLASSES: Record<string, string> = {
  strong: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
  moderate: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  mild: "border border-border text-muted-foreground",
};

function StrengthBadge({ strength }: { strength: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        STRENGTH_CLASSES[strength] ?? STRENGTH_CLASSES.mild
      }`}
    >
      {strength}
    </span>
  );
}

// ── Regenerate dialog ──────────────────────────────────────────────────────────

function RegenerateDialog({
  onConfirm,
  onCancel,
  isPending,
}: {
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-80 shadow-2xl">
        <CardHeader>
          <CardTitle className="text-base">Regenerate analysis?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This will use your LLM budget to generate a fresh children timing analysis.
            The cached version will be replaced.
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={isPending}
              className="flex-1"
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Regenerate"}
            </Button>
            <Button size="sm" variant="outline" onClick={onCancel} className="flex-1">
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main Screen ────────────────────────────────────────────────────────────────

export default function ChildrenTimingScreen() {
  const { groupId } = useParams<{ groupId: string }>();
  const [, navigate] = useLocation();
  const qc = useQueryClient();
  const { user } = useAuth();

  const currentYear = new Date().getFullYear();
  const [yearFrom] = useState(currentYear);
  const [yearTo] = useState(currentYear + 3);
  const [chatOpen, setChatOpen] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const { data: groupData } = useQuery({
    queryKey: ["/api/family/groups", groupId],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}`),
    enabled: !!groupId,
  });

  const { data, isLoading, error } = useQuery<ChildrenTimingData>({
    queryKey: ["/api/family/groups", groupId, "children-timing", yearFrom, yearTo],
    queryFn: () =>
      apiFetch(
        "GET",
        `/api/family/groups/${groupId}/children-timing?year_from=${yearFrom}&year_to=${yearTo}`
      ),
    enabled: !!groupId,
    staleTime: 1000 * 60 * 5,
  });

  const regenerateMutation = useMutation({
    mutationFn: () =>
      apiFetch(
        "DELETE",
        `/api/family/groups/${groupId}/children-timing?year_from=${yearFrom}&year_to=${yearTo}`
      ),
    onSuccess: () => {
      setShowConfirm(false);
      qc.invalidateQueries({
        queryKey: ["/api/family/groups", groupId, "children-timing", yearFrom, yearTo],
      });
    },
  });

  const groupName = groupData?.name ?? "Family";
  const primaryChartId = groupData?.primary_chart_id ?? null;
  const primaryChartName = groupData?.primary_chart_name ?? groupName;

  if (!groupId) return <div>Missing group ID</div>;

  return (
    <div className={chatOpen ? "mr-80 transition-all duration-300" : "transition-all duration-300"}>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <button
              onClick={() => navigate(`/family`)}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2"
            >
              <ArrowLeft className="h-4 w-4" /> Back to Family
            </button>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-semibold">{groupName}</h1>
              <span className="text-sm px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-medium">
                Children Timing
              </span>
              <span className="text-sm px-2 py-0.5 rounded-full bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300 font-medium">
                {yearFrom} – {yearTo}
              </span>
              {data?.cached && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                  cached
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setChatOpen((v) => !v)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 transition-colors text-sm font-medium"
            >
              <MessageCircle className="h-4 w-4" />
              {chatOpen ? "Close Chat" : "Ask Jyotishi"}
            </button>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-muted-foreground"
              onClick={() => setShowConfirm(true)}
              disabled={isLoading}
            >
              <RefreshCw className="h-4 w-4" /> Regenerate
            </Button>
          </div>
        </div>

        <p className="text-xs text-gray-500 italic mt-1 mb-4">
          These are favorable astrological windows based on Vedic principles.
          All timings are indicative — consult a qualified Jyotishi for personal guidance.
        </p>

        <Separator />

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground">
            <Loader2 className="h-10 w-10 animate-spin text-pink-500" />
            <p className="text-base font-medium">Analyzing Santana Bhagya...</p>
            <p className="text-sm">This takes about 30 seconds on first run</p>
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <Card className="border-destructive">
            <CardContent className="py-8 text-center text-destructive">
              <p>{(error as Error).message}</p>
            </CardContent>
          </Card>
        )}

        {/* Content */}
        {data && !isLoading && (
          <div className="space-y-6">

            {/* Has children already notice */}
            {data.has_children_already && (
              <Card className="border-blue-500/30 bg-blue-500/5">
                <CardContent className="pt-4 pb-4">
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    This group already has child members. The analysis below reflects auspicious
                    windows in case of additional children or for context.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Overall Outlook */}
            {data.overall_outlook && (
              <Card className="border-pink-500/30 bg-pink-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Heart className="h-4 w-4 text-pink-500" />
                    Overall Outlook
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed">{data.overall_outlook}</p>
                </CardContent>
              </Card>
            )}

            {/* Jupiter Insight */}
            {data.jupiter_insight && (
              <Card className="border-amber-500/30 bg-amber-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Star className="h-4 w-4 text-amber-500" />
                    Jupiter's Role
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed">{data.jupiter_insight}</p>
                </CardContent>
              </Card>
            )}

            {/* Favorable Windows */}
            {data.combined_windows?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Favorable Windows</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.combined_windows.map((w, i) => (
                    <div
                      key={i}
                      className="space-y-1.5 pb-3 border-b border-border last:border-0 last:pb-0"
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">{w.period}</span>
                        <StrengthBadge strength={w.strength} />
                      </div>
                      <p className="text-sm text-foreground">{w.plain_english}</p>
                      {w.basis && (
                        <p className="text-xs text-muted-foreground italic">{w.basis}</p>
                      )}
                      {w.cautions && (
                        <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 rounded px-2 py-1">
                          Note: {w.cautions}
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Remedies */}
            {data.remedies?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Supportive Practices</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1.5">
                    {data.remedies.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-amber-500 mt-0.5">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

          </div>
        )}
      </div>

      {/* ChatPanel */}
      {chatOpen && primaryChartId && (
        <div className="fixed top-0 right-0 h-full w-80 z-40 shadow-xl border-l border-border">
          <ChatPanel
            baseChartId={primaryChartId}
            chartName={primaryChartName}
            mahadasha=""
            antardasha=""
            periodLabel={`${groupName} · Children Timing`}
            onClose={() => setChatOpen(false)}
            chatEndpoint={`/api/family/groups/${groupId}/chat/stream`}
            readingAsName={primaryChartName}
          />
        </div>
      )}

      {/* Regenerate confirm dialog */}
      {showConfirm && (
        <RegenerateDialog
          onConfirm={() => regenerateMutation.mutate()}
          onCancel={() => setShowConfirm(false)}
          isPending={regenerateMutation.isPending}
        />
      )}
    </div>
  );
}
