import { useState } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { authHeaders } from "@/lib/auth";
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
  Loader2, RefreshCw, MessageCircle, ArrowLeft, Download,
  BookOpen, Briefcase, Heart, Home, AlertTriangle, Star,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface EducationEntry {
  period: string;
  type: "peak" | "supportive" | "caution";
  subject_strength: string;
  plain_english: string;
}

interface CareerAptitude {
  strong_houses: string[];
  favorable_fields: string[];
  peak_period: string;
  plain_english: string;
}

interface MarriageWindow {
  earliest_favorable: string;
  peak_window: string;
  plain_english: string;
}

interface LeavingHome {
  window: string;
  context: string;
  plain_english: string;
}

interface HealthCaution {
  period: string;
  area: string;
  plain_english: string;
}

interface ChildPrediction {
  cached: boolean;
  member_id: string;
  year: number;
  overall_narrative: string;
  education: EducationEntry[];
  career_aptitude: CareerAptitude;
  marriage_window: MarriageWindow;
  leaving_home: LeavingHome;
  health_cautions: HealthCaution[];
  key_takeaways: string[];
}

// ── Helpers ────────────────────────────────────────────────────────────────────


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

// ── Education type badge ───────────────────────────────────────────────────────

const EDU_TYPE_CLASSES: Record<string, string> = {
  peak: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
  supportive: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  caution: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
};

const SUBJECT_CLASSES: Record<string, string> = {
  mathematics: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
  languages: "bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200",
  arts: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200",
  sciences: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  sports: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  general: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {label}
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
          <CardTitle className="text-base">Regenerate prediction?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This will use your LLM budget to generate a fresh child prediction.
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

export default function ChildPredictionScreen() {
  const { groupId, memberId } = useParams<{ groupId: string; memberId: string }>();
  const [, navigate] = useLocation();
  const qc = useQueryClient();
  const { user } = useAuth();

  const currentYear = new Date().getFullYear();
  const [year] = useState(currentYear);
  const [chatOpen, setChatOpen] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const { data: groupData } = useQuery({
    queryKey: ["/api/family/groups", groupId],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}`),
    enabled: !!groupId,
  });

  const { data, isLoading, error } = useQuery<ChildPrediction>({
    queryKey: ["/api/family/groups", groupId, "members", memberId, "predictions", year],
    queryFn: () =>
      apiFetch(
        "GET",
        `/api/family/groups/${groupId}/members/${memberId}/predictions?year=${year}`
      ),
    enabled: !!groupId && !!memberId,
    staleTime: 1000 * 60 * 5,
  });

  const regenerateMutation = useMutation({
    mutationFn: () =>
      apiFetch(
        "DELETE",
        `/api/family/groups/${groupId}/members/${memberId}/predictions?year=${year}`
      ),
    onSuccess: () => {
      setShowConfirm(false);
      qc.invalidateQueries({
        queryKey: ["/api/family/groups", groupId, "members", memberId, "predictions", year],
      });
    },
  });

  const groupName = groupData?.name ?? "Family";
  const primaryChartId = groupData?.primary_chart_id ?? null;
  const primaryChartName = groupData?.primary_chart_name ?? groupName;

  // Try to find child's display name from group members
  const members: Array<{ id: string; display_name?: string; chart_name?: string; role: string }> =
    groupData?.members ?? [];
  const childMember = members.find((m) => m.id === memberId);
  const childName =
    childMember?.display_name || childMember?.chart_name || "Child";

  if (!groupId || !memberId) return <div>Missing parameters</div>;

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
              <h1 className="text-xl font-semibold">{childName}</h1>
              <span className="text-sm px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-medium">
                {year}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
                Child Reading
              </span>
              {data?.cached && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                  cached
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1">{groupName}</p>
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

        <Separator />

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground">
            <Loader2 className="h-10 w-10 animate-spin text-purple-500" />
            <p className="text-base font-medium">Reading {childName}'s chart...</p>
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

            {/* Overall Narrative */}
            {data.overall_narrative && (
              <Card className="border-purple-500/30 bg-purple-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Astrological Profile</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed whitespace-pre-line">
                    {data.overall_narrative}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Key Takeaways */}
            {data.key_takeaways?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Star className="h-4 w-4 text-amber-400" />
                    Key Takeaways for {year}
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

            {/* Education Timeline */}
            {data.education?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-blue-500" />
                    Education Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.education.map((e, i) => (
                    <div
                      key={i}
                      className="space-y-1.5 pb-3 border-b border-border last:border-0 last:pb-0"
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">{e.period}</span>
                        <Badge
                          label={e.type}
                          className={EDU_TYPE_CLASSES[e.type] ?? EDU_TYPE_CLASSES.supportive}
                        />
                        <Badge
                          label={e.subject_strength.replace(/_/g, " ")}
                          className={SUBJECT_CLASSES[e.subject_strength] ?? SUBJECT_CLASSES.general}
                        />
                      </div>
                      <p className="text-sm text-foreground">{e.plain_english}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Career Aptitude */}
            {data.career_aptitude && Object.keys(data.career_aptitude).length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-emerald-500" />
                    Career Aptitude
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.career_aptitude.favorable_fields?.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
                        Favorable Fields
                      </p>
                      <div className="flex gap-1.5 flex-wrap">
                        {data.career_aptitude.favorable_fields.map((f) => (
                          <span
                            key={f}
                            className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                          >
                            {f}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {data.career_aptitude.plain_english && (
                    <p className="text-sm leading-relaxed">{data.career_aptitude.plain_english}</p>
                  )}
                  {data.career_aptitude.peak_period && (
                    <p className="text-xs text-muted-foreground">
                      Peak foundation period: <span className="font-medium">{data.career_aptitude.peak_period}</span>
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Life Milestones: Marriage Window + Leaving Home */}
            {(data.marriage_window || data.leaving_home) && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Home className="h-4 w-4 text-pink-500" />
                    Life Milestones
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.marriage_window && Object.keys(data.marriage_window).length > 0 && (
                    <div className="space-y-1">
                      <p className="text-sm font-medium flex items-center gap-1.5">
                        <Heart className="h-3.5 w-3.5 text-rose-400" />
                        Marriage Window
                        <span className="text-xs font-normal text-muted-foreground">(distant future, indicative)</span>
                      </p>
                      <p className="text-sm text-foreground pl-5">{data.marriage_window.plain_english}</p>
                      {data.marriage_window.peak_window && (
                        <p className="text-xs text-muted-foreground pl-5">
                          Favorable window: {data.marriage_window.peak_window}
                        </p>
                      )}
                    </div>
                  )}
                  {data.leaving_home && Object.keys(data.leaving_home).length > 0 && (
                    <div className="space-y-1 border-t border-border pt-3">
                      <p className="text-sm font-medium">
                        Leaving Home
                        {data.leaving_home.context && (
                          <span className="text-xs font-normal text-muted-foreground ml-1.5">
                            ({data.leaving_home.context})
                          </span>
                        )}
                      </p>
                      <p className="text-sm text-foreground">{data.leaving_home.plain_english}</p>
                      {data.leaving_home.window && (
                        <p className="text-xs text-muted-foreground">
                          Window: {data.leaving_home.window}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Health Cautions */}
            {data.health_cautions?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    Health Awareness
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.health_cautions.map((h, i) => (
                    <div
                      key={i}
                      className="space-y-0.5 pb-2 border-b border-border last:border-0 last:pb-0"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">{h.period}</span>
                        <span className="text-xs text-muted-foreground">—</span>
                        <span className="text-xs text-foreground">{h.area}</span>
                      </div>
                      <p className="text-xs text-muted-foreground italic">{h.plain_english}</p>
                    </div>
                  ))}
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
            chartName={childName}
            mahadasha=""
            antardasha=""
            periodLabel={`${childName} · ${year}`}
            onClose={() => setChatOpen(false)}
            chatEndpoint={`/api/family/groups/${groupId}/chat/stream`}
            readingAsName={childName}
            contextType={`child:${memberId}`}
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
