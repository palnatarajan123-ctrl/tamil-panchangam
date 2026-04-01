import { useState, useRef } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChatPanel } from "@/components/ChatPanel";
import { Loader2, RefreshCw, MessageCircle, ArrowLeft, X, Users } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashaBar {
  from: string;
  to: string;
  mahadasha: string;
  antardasha: string;
  color: string;
  label: string;
}

interface SadeSatiBar {
  from: string;
  to: string;
  phase: string | number | null;
  active: boolean;
}

interface Milestone {
  date: string;
  type: string;
  label: string;
  significance: string;
  plain_english: string;
}

interface MemberTracks {
  dasha: DashaBar[];
  sade_sati: SadeSatiBar[];
  milestones: Milestone[];
}

interface TimelineMember {
  member_id: string;
  role: string;
  display_name: string;
  color: string;
  tracks: MemberTracks;
}

interface SharedEvent {
  period: string;
  type: string;
  members_involved: string[];
  label: string;
  significance: string;
  plain_english: string;
  remedy_hint?: string;
}

interface TimelineData {
  group_id: string;
  group_name: string;
  from_year: number;
  to_year: number;
  generated_at: string;
  members: TimelineMember[];
  shared_events: SharedEvent[];
  cached: boolean;
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

// ── SVG Timeline constants ─────────────────────────────────────────────────────

const MONTH_WIDTH = 60;
const MEMBER_HEIGHT = 120;
const LEFT_MARGIN = 140;
const TOP_MARGIN = 40;
const DASHA_ROW_H = 28;
const SS_ROW_H = 14;
const MILESTONE_ROW_H = 20;
const ROW_PADDING = 8;

function dateToX(dateStr: string, fromYear: number): number {
  const d = new Date(dateStr);
  const monthsFromStart = (d.getFullYear() - fromYear) * 12 + d.getMonth();
  return LEFT_MARGIN + monthsFromStart * MONTH_WIDTH;
}

function yearToX(year: number, fromYear: number): number {
  return LEFT_MARGIN + (year - fromYear) * 12 * MONTH_WIDTH;
}

function todayX(fromYear: number): number {
  const now = new Date();
  const monthsFromStart = (now.getFullYear() - fromYear) * 12 + now.getMonth();
  return LEFT_MARGIN + monthsFromStart * MONTH_WIDTH;
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
          <CardTitle className="text-base">Refresh timeline?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This will rebuild the family timeline from current chart data.
            The cached version will be replaced.
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={isPending}
              className="flex-1"
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
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

// ── SVG Timeline Renderer ──────────────────────────────────────────────────────

function TimelineSVG({
  data,
  fromYear,
  toYear,
  onMilestoneClick,
}: {
  data: TimelineData;
  fromYear: number;
  toYear: number;
  onMilestoneClick: (m: Milestone) => void;
}) {
  const totalYears = toYear - fromYear + 1;
  const totalMonths = totalYears * 12;
  const svgWidth = LEFT_MARGIN + totalMonths * MONTH_WIDTH + 40;
  const svgHeight = TOP_MARGIN + data.members.length * MEMBER_HEIGHT + 40;
  const txDay = todayX(fromYear);

  return (
    <svg
      width={svgWidth}
      height={svgHeight}
      style={{ fontFamily: "sans-serif", fontSize: 11 }}
    >
      {/* Year labels */}
      {Array.from({ length: totalYears }, (_, i) => {
        const yr = fromYear + i;
        const x = yearToX(yr, fromYear);
        return (
          <g key={yr}>
            <line x1={x} y1={TOP_MARGIN - 10} x2={x} y2={svgHeight - 20}
              stroke="#e5e7eb" strokeWidth={1} />
            <text x={x + 4} y={TOP_MARGIN - 14} fill="#6b7280" fontSize={10}>
              {yr}
            </text>
          </g>
        );
      })}

      {/* Today marker */}
      {txDay >= LEFT_MARGIN && txDay <= svgWidth - 20 && (
        <g>
          <line
            x1={txDay} y1={TOP_MARGIN - 10}
            x2={txDay} y2={svgHeight - 20}
            stroke="#f97316" strokeWidth={1.5} strokeDasharray="4,3"
          />
          <text x={txDay + 3} y={TOP_MARGIN - 2} fill="#f97316" fontSize={9}>
            Today
          </text>
        </g>
      )}

      {/* Members */}
      {data.members.map((member, mi) => {
        const baseY = TOP_MARGIN + mi * MEMBER_HEIGHT;
        const dashaY = baseY + ROW_PADDING;
        const ssY = dashaY + DASHA_ROW_H + 4;
        const msY = ssY + SS_ROW_H + 4;

        return (
          <g key={member.member_id}>
            {/* Member label */}
            <text
              x={LEFT_MARGIN - 8}
              y={baseY + MEMBER_HEIGHT / 2}
              textAnchor="end"
              fill={member.color}
              fontWeight="600"
              fontSize={11}
            >
              {member.display_name}
            </text>
            <text
              x={LEFT_MARGIN - 8}
              y={baseY + MEMBER_HEIGHT / 2 + 14}
              textAnchor="end"
              fill="#9ca3af"
              fontSize={9}
            >
              {member.role}
            </text>

            {/* Row separator */}
            <line
              x1={LEFT_MARGIN - 4} y1={baseY + MEMBER_HEIGHT - 2}
              x2={svgWidth - 10} y2={baseY + MEMBER_HEIGHT - 2}
              stroke="#f3f4f6" strokeWidth={1}
            />

            {/* Sub-row labels */}
            <text x={LEFT_MARGIN - 8} y={dashaY + 18} textAnchor="end" fill="#9ca3af" fontSize={8}>Dasha</text>
            <text x={LEFT_MARGIN - 8} y={ssY + 10} textAnchor="end" fill="#9ca3af" fontSize={8}>SS</text>

            {/* Dasha bars */}
            {member.tracks.dasha.map((bar, bi) => {
              const x1 = dateToX(bar.from, fromYear);
              const x2 = dateToX(bar.to, fromYear);
              const w = Math.max(x2 - x1, 2);
              return (
                <g key={bi}>
                  <rect
                    x={x1} y={dashaY}
                    width={w} height={DASHA_ROW_H}
                    fill={bar.color}
                    opacity={0.85}
                    rx={3}
                  />
                  {w > 40 && (
                    <text
                      x={x1 + 4} y={dashaY + 17}
                      fill="white" fontSize={8}
                      style={{ pointerEvents: "none" }}
                    >
                      {bar.label.length > Math.floor(w / 6) ? bar.label.slice(0, Math.floor(w / 6)) + "…" : bar.label}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Sade Sati overlay */}
            {member.tracks.sade_sati.map((ss, si) => {
              const x1 = dateToX(ss.from, fromYear);
              const x2 = dateToX(ss.to, fromYear);
              const w = Math.max(x2 - x1, 2);
              return (
                <rect
                  key={si}
                  x={x1} y={ssY}
                  width={w} height={SS_ROW_H}
                  fill="#f59e0b"
                  opacity={0.5}
                  rx={2}
                />
              );
            })}

            {/* Milestones */}
            {member.tracks.milestones.map((ms, msi) => {
              const mx = dateToX(ms.date, fromYear);
              return (
                <g
                  key={msi}
                  style={{ cursor: "pointer" }}
                  onClick={() => onMilestoneClick(ms)}
                >
                  <circle
                    cx={mx} cy={msY + MILESTONE_ROW_H / 2}
                    r={ms.significance === "high" ? 6 : 4}
                    fill={ms.significance === "high" ? "#f97316" : "#6b7280"}
                    opacity={0.9}
                  />
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

// ── Main Screen ────────────────────────────────────────────────────────────────

export default function FamilyTimelineScreen() {
  const { groupId } = useParams<{ groupId: string }>();
  const [, navigate] = useLocation();
  const qc = useQueryClient();
  const { user } = useAuth();

  const currentYear = new Date().getFullYear();
  const [fromYear, setFromYear] = useState(currentYear);
  const [toYear, setToYear] = useState(currentYear + 5);
  const [chatOpen, setChatOpen] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [selectedMilestone, setSelectedMilestone] = useState<{
    milestone: Milestone;
    x: number;
    y: number;
  } | null>(null);

  const { data: groupData } = useQuery({
    queryKey: ["/api/family/groups", groupId],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}`),
    enabled: !!groupId,
  });

  const { data, isLoading, error } = useQuery<TimelineData>({
    queryKey: ["/api/family/groups", groupId, "timeline", fromYear, toYear],
    queryFn: () =>
      apiFetch("GET", `/api/family/groups/${groupId}/timeline?from_year=${fromYear}&to_year=${toYear}`),
    enabled: !!groupId,
    staleTime: 1000 * 60 * 5,
  });

  const refreshMutation = useMutation({
    mutationFn: () =>
      apiFetch("DELETE", `/api/family/groups/${groupId}/timeline?from_year=${fromYear}&to_year=${toYear}`),
    onSuccess: () => {
      setShowConfirm(false);
      qc.invalidateQueries({
        queryKey: ["/api/family/groups", groupId, "timeline", fromYear, toYear],
      });
    },
  });

  const groupName = groupData?.name ?? "Family";
  const primaryChartId = groupData?.primary_chart_id ?? null;
  const primaryChartName = groupData?.primary_chart_name ?? groupName;

  if (!groupId) return <div>Missing group ID</div>;

  return (
    <div
      className={chatOpen ? "mr-80 transition-all duration-300" : "transition-all duration-300"}
      onClick={() => selectedMilestone && setSelectedMilestone(null)}
    >
      <div className="max-w-full px-4 py-8 space-y-6">

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
                Timeline
              </span>
              {data?.cached && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                  cached
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Year range inputs */}
            <div className="flex items-center gap-1 text-sm">
              <label className="text-muted-foreground">From</label>
              <input
                type="number"
                value={fromYear}
                onChange={(e) => setFromYear(Number(e.target.value))}
                className="w-20 border border-border rounded px-2 py-1 text-sm bg-background"
                min={2000}
                max={2100}
              />
              <label className="text-muted-foreground">to</label>
              <input
                type="number"
                value={toYear}
                onChange={(e) => setToYear(Number(e.target.value))}
                className="w-20 border border-border rounded px-2 py-1 text-sm bg-background"
                min={2000}
                max={2100}
              />
            </div>

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
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground">
            <Loader2 className="h-10 w-10 animate-spin text-amber-500" />
            <p className="text-base font-medium">Building your family timeline...</p>
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

        {/* Empty state */}
        {data && !isLoading && data.members.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-gray-700 rounded-2xl">
            <Users size={40} className="mb-4 text-gray-600" />
            <p className="text-gray-500">Add members to this family group to see the timeline.</p>
          </div>
        )}

        {/* Timeline SVG */}
        {data && !isLoading && data.members.length > 0 && (
          <div className="space-y-4">
            {/* Legend */}
            <div className="flex gap-4 flex-wrap text-xs text-muted-foreground">
              {data.members.map((m) => (
                <span key={m.member_id} className="flex items-center gap-1.5">
                  <span
                    className="inline-block w-3 h-3 rounded-sm"
                    style={{ backgroundColor: m.color }}
                  />
                  {m.display_name} ({m.role})
                </span>
              ))}
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-amber-400 opacity-60" />
                Sade Sati
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-full bg-orange-400" />
                Milestone
              </span>
            </div>

            {/* Scrollable SVG container */}
            <div
              className="overflow-x-auto border border-border rounded-lg bg-background relative"
              style={{ maxHeight: "70vh", overflowY: "auto" }}
            >
              <TimelineSVG
                data={data}
                fromYear={fromYear}
                toYear={toYear}
                onMilestoneClick={(ms) =>
                  setSelectedMilestone({ milestone: ms, x: 0, y: 0 })
                }
              />
            </div>

            {/* Shared events */}
            {data.shared_events.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Shared Events</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.shared_events.map((ev, i) => (
                    <div key={i} className="space-y-1 pb-2 border-b border-border last:border-0 last:pb-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">{ev.period}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                          {ev.label}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {ev.members_involved.join(", ")}
                        </span>
                      </div>
                      {ev.plain_english && (
                        <p className="text-sm text-foreground">{ev.plain_english}</p>
                      )}
                      {ev.remedy_hint && (
                        <p className="text-xs text-muted-foreground italic">{ev.remedy_hint}</p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Milestone popover */}
      {selectedMilestone && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setSelectedMilestone(null)}
        >
          <Card
            className="w-80 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader className="pb-2 flex flex-row items-start justify-between">
              <CardTitle className="text-sm">{selectedMilestone.milestone.label}</CardTitle>
              <button onClick={() => setSelectedMilestone(null)}>
                <X className="h-4 w-4 text-muted-foreground" />
              </button>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <p className="text-muted-foreground text-xs">{selectedMilestone.milestone.date}</p>
              <p>{selectedMilestone.milestone.plain_english}</p>
              <span className="inline-block text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {selectedMilestone.milestone.type.replace(/_/g, " ")}
              </span>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ChatPanel */}
      {chatOpen && primaryChartId && (
        <div className="fixed top-0 right-0 h-full w-80 z-40 shadow-xl border-l border-border">
          <ChatPanel
            baseChartId={primaryChartId}
            chartName={primaryChartName}
            mahadasha=""
            antardasha=""
            periodLabel={`${groupName} · Timeline`}
            onClose={() => setChatOpen(false)}
            chatEndpoint={`/api/family/groups/${groupId}/chat/stream`}
            readingAsName={primaryChartName}
          />
        </div>
      )}

      {/* Regenerate confirm dialog */}
      {showConfirm && (
        <RegenerateDialog
          onConfirm={() => refreshMutation.mutate()}
          onCancel={() => setShowConfirm(false)}
          isPending={refreshMutation.isPending}
        />
      )}
    </div>
  );
}
