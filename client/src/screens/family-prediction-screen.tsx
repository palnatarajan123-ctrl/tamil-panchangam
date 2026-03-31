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
  Loader2, Download, MessageCircle, RefreshCw, ArrowLeft,
  TrendingUp, TrendingDown, AlertTriangle, Star, CheckCircle2,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface FinancialPeak {
  period: string;
  type: "peak" | "trough";
  strength: "strong" | "moderate" | "mild";
  driven_by: string;
  plain_english: string;
  members_involved: string[];
}

interface CautionWindow {
  period: string;
  theme: "health" | "relationship" | "finance" | "travel" | "general";
  intensity: "high" | "moderate" | "mild";
  members_affected: string[];
  plain_english: string;
  remedy_hint?: string;
}

interface ChildMilestone {
  child_name: string;
  milestone_type: string;
  period: string;
  plain_english: string;
  favorable: boolean;
}

interface FamilyPrediction {
  cached: boolean;
  group_id: string;
  year: number;
  executive_summary: string;
  financial_peaks: FinancialPeak[];
  caution_windows: CautionWindow[];
  child_milestones: ChildMilestone[];
  key_takeaways: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

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

// ── Badge components ──────────────────────────────────────────────────────────

const STRENGTH_CLASSES: Record<string, string> = {
  strong: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
  moderate: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  mild: "border border-border text-muted-foreground",
};

const THEME_CLASSES: Record<string, string> = {
  health: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  relationship: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200",
  finance: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
  travel: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  general: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

const INTENSITY_CLASSES: Record<string, string> = {
  high: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  moderate: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  mild: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}

function RolePill({ role }: { role: string }) {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-muted text-muted-foreground text-xs">
      {role}
    </span>
  );
}

// ── Section cards ─────────────────────────────────────────────────────────────

function FinancialPeaksCard({ peaks }: { peaks: FinancialPeak[] }) {
  if (!peaks.length) return null;
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-emerald-500" />
          Financial Peaks &amp; Troughs
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {peaks.map((p, i) => (
          <div key={i} className="space-y-1.5 pb-3 border-b border-border last:border-0 last:pb-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">{p.period}</span>
              {p.type === "peak" ? (
                <Badge label="▲ Peak" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200" />
              ) : (
                <Badge label="▼ Trough" className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" />
              )}
              <Badge label={p.strength} className={STRENGTH_CLASSES[p.strength] ?? STRENGTH_CLASSES.mild} />
            </div>
            <p className="text-sm text-foreground">{p.plain_english}</p>
            {p.driven_by && (
              <p className="text-xs text-muted-foreground italic">{p.driven_by}</p>
            )}
            {p.members_involved?.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {p.members_involved.map((m) => <RolePill key={m} role={m} />)}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CautionWindowsCard({ windows }: { windows: CautionWindow[] }) {
  if (!windows.length) return null;
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Shared Caution Windows
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {windows.map((w, i) => (
          <div key={i} className="space-y-1.5 pb-3 border-b border-border last:border-0 last:pb-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">{w.period}</span>
              <Badge label={w.theme} className={THEME_CLASSES[w.theme] ?? THEME_CLASSES.general} />
              <Badge label={w.intensity} className={INTENSITY_CLASSES[w.intensity] ?? INTENSITY_CLASSES.mild} />
            </div>
            <p className="text-sm text-foreground">{w.plain_english}</p>
            {w.remedy_hint && (
              <p className="text-xs text-muted-foreground italic">{w.remedy_hint}</p>
            )}
            {w.members_affected?.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {w.members_affected.map((m) => <RolePill key={m} role={m} />)}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ChildMilestonesCard({ milestones }: { milestones: ChildMilestone[] }) {
  if (!milestones.length) return null;

  // Group by child_name
  const byChild: Record<string, ChildMilestone[]> = {};
  for (const m of milestones) {
    const key = m.child_name || "Child";
    if (!byChild[key]) byChild[key] = [];
    byChild[key].push(m);
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Star className="h-4 w-4 text-amber-400" />
          Child Milestones
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(byChild).map(([childName, items]) => (
          <div key={childName}>
            <p className="text-sm font-semibold mb-2">{childName}</p>
            <div className="space-y-2 pl-2">
              {items.map((m, i) => (
                <div key={i} className="space-y-1 pb-2 border-b border-border last:border-0 last:pb-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium">{m.period}</span>
                    <Badge
                      label={m.milestone_type.replace(/_/g, " ")}
                      className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"
                    />
                    {m.favorable ? (
                      <span className="text-emerald-500 text-xs flex items-center gap-0.5">
                        <CheckCircle2 className="h-3 w-3" /> Favorable
                      </span>
                    ) : (
                      <span className="text-amber-500 text-xs flex items-center gap-0.5">
                        <AlertTriangle className="h-3 w-3" /> Be mindful
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-foreground">{m.plain_english}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Confirm dialog ────────────────────────────────────────────────────────────

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
          <CardTitle className="text-base">Regenerate prediction?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This will use your LLM budget to generate a fresh family prediction.
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

// ── Main Screen ───────────────────────────────────────────────────────────────

export default function FamilyPredictionScreen() {
  const { groupId } = useParams<{ groupId: string }>();
  const [, navigate] = useLocation();
  const qc = useQueryClient();
  const { user } = useAuth();
  const year = new Date().getFullYear();

  const [chatOpen, setChatOpen] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Fetch group info (for name + primary chart)
  const { data: groupData } = useQuery({
    queryKey: ["/api/family/groups", groupId],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}`),
    enabled: !!groupId,
  });

  // Fetch prediction
  const { data, isLoading, error } = useQuery<FamilyPrediction>({
    queryKey: ["/api/family/groups", groupId, "predictions", year],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}/predictions?year=${year}`),
    enabled: !!groupId,
    staleTime: 1000 * 60 * 5,
  });

  // Regenerate: clear cache then refetch
  const regenerateMutation = useMutation({
    mutationFn: () =>
      apiFetch("DELETE", `/api/family/groups/${groupId}/predictions?year=${year}`),
    onSuccess: () => {
      setShowConfirm(false);
      qc.invalidateQueries({ queryKey: ["/api/family/groups", groupId, "predictions", year] });
    },
  });

  const groupName = groupData?.name ?? "Family";
  const primaryChartId = groupData?.primary_chart_id ?? null;
  const primaryChartName = groupData?.primary_chart_name ?? groupName;

  const members: { display_name?: string; chart_name?: string; role: string }[] =
    groupData?.members ?? [];
  const memberPills = members.map(
    (m) => m.display_name || m.chart_name || m.role
  );

  if (!groupId) return <div>Missing group ID</div>;

  return (
    <div className={chatOpen ? "mr-80 transition-all duration-300" : "transition-all duration-300"}>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* ── Header ──────────────────────────────────────────────────────── */}
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
                {year}
              </span>
              {data?.cached && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                  cached
                </span>
              )}
            </div>
            {memberPills.length > 0 && (
              <div className="flex gap-1.5 flex-wrap mt-2">
                {memberPills.map((name) => (
                  <span key={name} className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                    {name}
                  </span>
                ))}
              </div>
            )}
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
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() =>
                window.open(
                  `/api/family/groups/${groupId}/predictions/pdf?year=${year}`,
                  "_blank"
                )
              }
            >
              <Download className="h-4 w-4" /> PDF
            </Button>
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

        <Separator />

        {/* ── Loading state ────────────────────────────────────────────────── */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground">
            <Loader2 className="h-10 w-10 animate-spin text-amber-500" />
            <p className="text-base font-medium">Consulting the stars for your family…</p>
            <p className="text-sm">This takes about 30 seconds on first run</p>
          </div>
        )}

        {/* ── Error state ──────────────────────────────────────────────────── */}
        {error && !isLoading && (
          <Card className="border-destructive">
            <CardContent className="py-8 text-center text-destructive">
              <p>{(error as Error).message}</p>
            </CardContent>
          </Card>
        )}

        {/* ── Prediction content ────────────────────────────────────────────── */}
        {data && !isLoading && (
          <div className="space-y-6">

            {/* Executive Summary */}
            {data.executive_summary && (
              <Card className="border-amber-500/30 bg-amber-500/5">
                <CardContent className="pt-5 pb-5">
                  <p className="text-sm leading-relaxed">{data.executive_summary}</p>
                </CardContent>
              </Card>
            )}

            {/* Key Takeaways */}
            {data.key_takeaways?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Star className="h-4 w-4 text-amber-400" />
                    Key Takeaways
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1.5">
                    {data.key_takeaways.map((t, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-amber-500 mt-0.5">•</span>
                        <span>{t}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Three content cards */}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <FinancialPeaksCard peaks={data.financial_peaks ?? []} />
              <CautionWindowsCard windows={data.caution_windows ?? []} />
              <ChildMilestonesCard milestones={data.child_milestones ?? []} />
            </div>

          </div>
        )}
      </div>

      {/* ── ChatPanel ──────────────────────────────────────────────────────── */}
      {chatOpen && primaryChartId && (
        <div className="fixed top-0 right-0 h-full w-80 z-40 shadow-xl border-l border-border">
          <ChatPanel
            baseChartId={primaryChartId}
            chartName={primaryChartName}
            mahadasha=""
            antardasha=""
            periodLabel={`${groupName} · ${year}`}
            onClose={() => setChatOpen(false)}
            chatEndpoint={`/api/family/groups/${groupId}/chat/stream`}
            readingAsName={primaryChartName}
          />
        </div>
      )}

      {/* ── Regenerate confirm dialog ───────────────────────────────────────── */}
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
