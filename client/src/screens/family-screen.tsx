import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChatPanel } from "@/components/ChatPanel";
import {
  Users, Plus, Trash2, ArrowLeft, ChevronRight,
  Heart, Star, AlertCircle, CheckCircle2, XCircle,
  MessageCircle, ChevronDown,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

interface UserChart {
  chart_id: string;
  name: string;
  date_of_birth: string;
  nakshatra: string;
  rasi: string;
}

interface FamilyMember {
  id: string;
  group_id: string;
  chart_id: string;
  role: string;
  display_name: string | null;
  birth_order: number;
  created_at: string;
  chart_name?: string;
  date_of_birth?: string;
  nakshatra?: string;
  rasi?: string;
}

interface FamilyGroup {
  id: string;
  name: string;
  primary_chart_id: string | null;
  primary_chart_name?: string;
  created_at: string;
  updated_at: string;
  member_count: number;
  members?: FamilyMember[];
}

interface PoruthPoint {
  name: string;
  score: number;
  max: number;
  pass: boolean;
  mandatory?: boolean;
}

interface PoruthResult {
  total_score: number;
  max_score: number;
  percent: number;
  grade: string;
  mandatory_fail: boolean;
  points: PoruthPoint[];
  error?: string;
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

const ROLE_LABELS: Record<string, string> = {
  husband: "Husband",
  wife: "Wife",
  child: "Child",
  other: "Other",
};

const ROLE_COLORS: Record<string, string> = {
  husband: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  wife: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200",
  child: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  other: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
};

function GradeTag({ grade, mandatoryFail }: { grade: string; mandatoryFail: boolean }) {
  const colors: Record<string, string> = {
    Excellent: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
    Good: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    Average: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    Poor: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    Unknown: "bg-gray-100 text-gray-600",
  };
  const label = mandatoryFail ? `${grade} (dosha)` : grade;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-sm font-medium ${colors[grade] ?? colors.Unknown}`}>
      {mandatoryFail && <AlertCircle className="h-3 w-3" />}
      {label}
    </span>
  );
}

// ── Sub-views ─────────────────────────────────────────────────────────────────

function GroupList({
  onSelect, onCreate,
}: {
  onSelect: (g: FamilyGroup) => void;
  onCreate: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/family/groups"],
    queryFn: () => apiFetch("GET", "/api/family/groups"),
  });

  if (isLoading) {
    return <div className="text-muted-foreground text-sm py-8 text-center">Loading groups…</div>;
  }

  const groups: FamilyGroup[] = data?.groups ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Family Groups</h2>
        <Button size="sm" onClick={onCreate} className="gap-2">
          <Plus className="h-4 w-4" /> New Group
        </Button>
      </div>

      {groups.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Users className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No family groups yet</p>
            <p className="text-sm mt-1">Create a group and add family charts to check compatibility.</p>
            <Button className="mt-4" onClick={onCreate}>
              <Plus className="h-4 w-4 mr-2" /> Create Family Group
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {groups.map((g) => (
            <Card
              key={g.id}
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => onSelect(g)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{g.name}</p>
                    <p className="text-xs text-muted-foreground">{g.member_count} member{g.member_count !== 1 ? "s" : ""}</p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}


function AddMemberForm({
  groupId,
  onDone,
}: {
  groupId: string;
  onDone: () => void;
}) {
  const qc = useQueryClient();
  const [chartId, setChartId] = useState("");
  const [role, setRole] = useState("husband");
  const [displayName, setDisplayName] = useState("");

  const { data: chartsData } = useQuery({
    queryKey: ["/api/family/user-charts"],
    queryFn: () => apiFetch("GET", "/api/family/user-charts"),
  });

  const addMutation = useMutation({
    mutationFn: (body: unknown) =>
      apiFetch("POST", `/api/family/groups/${groupId}/members`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/family/groups", groupId] });
      qc.invalidateQueries({ queryKey: ["/api/family/groups"] });
      onDone();
    },
  });

  const charts: UserChart[] = chartsData?.charts ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Add Member</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1 block">Chart</label>
          <select
            value={chartId}
            onChange={(e) => {
              setChartId(e.target.value);
              const c = charts.find((x) => x.chart_id === e.target.value);
              if (c) setDisplayName(c.name);
            }}
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
          >
            <option value="">Select a chart…</option>
            {charts.map((c) => (
              <option key={c.chart_id} value={c.chart_id}>
                {c.name} {c.nakshatra ? `· ${c.nakshatra}` : ""}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1 block">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
          >
            {Object.entries(ROLE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1 block">Display Name (optional)</label>
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Override chart name"
          />
        </div>

        {addMutation.error && (
          <p className="text-sm text-destructive">{(addMutation.error as Error).message}</p>
        )}

        <div className="flex gap-2 pt-1">
          <Button
            size="sm"
            disabled={!chartId || addMutation.isPending}
            onClick={() =>
              addMutation.mutate({ chart_id: chartId, role, display_name: displayName || null, birth_order: 0 })
            }
          >
            {addMutation.isPending ? "Adding…" : "Add Member"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onDone}>Cancel</Button>
        </div>
      </CardContent>
    </Card>
  );
}


function PoruthTab({ groupId }: { groupId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["/api/family/groups", groupId, "porutham"],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}/porutham`),
    retry: false,
  });

  if (isLoading) return <div className="text-muted-foreground text-sm py-6 text-center">Computing…</div>;

  if (error) {
    return (
      <div className="text-muted-foreground text-sm py-6 text-center">
        <AlertCircle className="h-6 w-6 mx-auto mb-2 text-amber-500" />
        <p>{(error as Error).message}</p>
        <p className="mt-1 text-xs">Add a husband and wife to this group to see compatibility.</p>
      </div>
    );
  }

  const result: PoruthResult = data?.porutham;
  if (!result) return null;

  const husband = data?.husband;
  const wife = data?.wife;

  return (
    <div className="space-y-4">
      {/* Header pair */}
      <div className="flex items-center gap-3 justify-center py-2">
        <div className="text-center">
          <p className="font-medium">{husband?.name || "Husband"}</p>
          <p className="text-xs text-muted-foreground">{husband?.nakshatra} · {husband?.rasi}</p>
        </div>
        <Heart className="h-5 w-5 text-rose-400" />
        <div className="text-center">
          <p className="font-medium">{wife?.name || "Wife"}</p>
          <p className="text-xs text-muted-foreground">{wife?.nakshatra} · {wife?.rasi}</p>
        </div>
      </div>

      {/* Score card */}
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="text-3xl font-bold">{result.total_score}</span>
              <span className="text-muted-foreground text-sm"> / {result.max_score}</span>
            </div>
            <GradeTag grade={result.grade} mandatoryFail={result.mandatory_fail} />
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${result.percent}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground mt-1">{result.percent}%</p>
        </CardContent>
      </Card>

      {/* Points breakdown */}
      <div className="space-y-1">
        {result.points.map((pt) => (
          <div key={pt.name} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
            <div className="flex items-center gap-2">
              {pt.mandatory && !pt.pass ? (
                <XCircle className="h-4 w-4 text-destructive flex-shrink-0" />
              ) : pt.pass ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              )}
              <span className="text-sm">{pt.name}</span>
              {pt.mandatory && (
                <span className="text-xs text-muted-foreground">(mandatory)</span>
              )}
            </div>
            <span className="text-sm font-medium tabular-nums">
              {pt.max > 0 ? `${pt.score}/${pt.max}` : (pt.pass ? "✓" : "✗")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}


function GroupDetail({
  groupId,
  onBack,
}: {
  groupId: string;
  onBack: () => void;
}) {
  const qc = useQueryClient();
  const [, navigate] = useLocation();
  const [activeTab, setActiveTab] = useState<"overview" | "compatibility">("overview");
  const [showAddMember, setShowAddMember] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["/api/family/groups", groupId],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}`),
  });

  const { data: overviewData } = useQuery({
    queryKey: ["/api/family/groups", groupId, "overview"],
    queryFn: () => apiFetch("GET", `/api/family/groups/${groupId}/overview`),
    enabled: !!groupId,
  });

  const deleteMember = useMutation({
    mutationFn: (memberId: string) =>
      apiFetch("DELETE", `/api/family/groups/${groupId}/members/${memberId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/family/groups", groupId] });
      qc.invalidateQueries({ queryKey: ["/api/family/groups"] });
      qc.invalidateQueries({ queryKey: ["/api/family/groups", groupId, "porutham"] });
    },
  });

  const deleteGroup = useMutation({
    mutationFn: () => apiFetch("DELETE", `/api/family/groups/${groupId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/family/groups"] });
      onBack();
    },
  });

  const patchPrimary = useMutation({
    mutationFn: (chartId: string | null) =>
      apiFetch("PATCH", `/api/family/groups/${groupId}`, { primary_chart_id: chartId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/family/groups", groupId] });
    },
  });

  if (isLoading) {
    return <div className="text-muted-foreground text-sm py-8 text-center">Loading…</div>;
  }

  const group: FamilyGroup = data;
  if (!group) return null;
  const members: FamilyMember[] = group.members ?? [];

  // Build a lookup from member_id → overview entry for O(1) access in render
  const overviewByMemberId: Record<string, { dasha: { mahadasha: string | null; antardasha: string | null; end_date: string | null }; sade_sati: { is_active: boolean; phase: string | null } }> = {};
  for (const entry of (overviewData?.members ?? [])) {
    overviewByMemberId[entry.member_id] = entry;
  }
  const primaryChartId = group.primary_chart_id ?? null;
  const primaryChartName = group.primary_chart_name ?? "";

  return (
    <div className={chatOpen ? "mr-80 transition-all duration-300" : "transition-all duration-300"}>
    <div className="space-y-4">
      {/* Back header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Groups
        </button>
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-sm"
            onClick={() => navigate(`/family/${groupId}/predictions`)}
          >
            View Predictions
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-sm"
            onClick={() => navigate(`/family/${groupId}/timeline`)}
          >
            Timeline
          </Button>
          {members.some((m) => m.role === "husband") && members.some((m) => m.role === "wife") && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-sm"
              onClick={() => navigate(`/family/${groupId}/children-timing`)}
            >
              Children Timing
            </Button>
          )}
          {members.filter((m) => m.role === "child").map((child) => (
            <Button
              key={child.id}
              size="sm"
              variant="outline"
              className="gap-1.5 text-sm"
              onClick={() => navigate(`/family/${groupId}/members/${child.id}/predictions`)}
            >
              {child.display_name || "Child"}'s Predictions
            </Button>
          ))}
          {primaryChartId && (
            <Button
              size="sm"
              variant="ghost"
              className="gap-1.5 text-sm"
              onClick={() => setChatOpen((o) => !o)}
            >
              <MessageCircle className="h-4 w-4" />
              Ask Jyotishi
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={() => deleteGroup.mutate()}
            disabled={deleteGroup.isPending}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xl font-semibold">{group.name}</h2>

        {/* Primary chart selector */}
        {members.length > 0 && (
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-xs text-muted-foreground">Reading from:</span>
            <div className="relative">
              <select
                value={primaryChartId ?? ""}
                onChange={(e) => patchPrimary.mutate(e.target.value || null)}
                className="appearance-none pl-2 pr-6 py-1 text-sm font-medium bg-muted rounded-md border-0 cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">— auto —</option>
                {members.map((m) => (
                  <option key={m.chart_id} value={m.chart_id}>
                    {m.display_name || m.chart_name || m.chart_id}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-border">
        {(["overview", "compatibility"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
              activeTab === tab
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab === "compatibility" ? (
              <span className="flex items-center gap-1.5"><Heart className="h-3.5 w-3.5" />Compatibility</span>
            ) : (
              <span className="flex items-center gap-1.5"><Users className="h-3.5 w-3.5" />Overview</span>
            )}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-3">
          {members.length === 0 && !showAddMember && (
            <p className="text-muted-foreground text-sm text-center py-4">No members yet.</p>
          )}
          {members.map((m) => {
            const ov = overviewByMemberId[m.id];
            const dasha = ov?.dasha;
            const ss = ov?.sade_sati;
            const dashaLabel = dasha?.mahadasha
              ? `${dasha.mahadasha} › ${dasha.antardasha ?? "—"}${dasha.end_date ? `  until ${dasha.end_date.slice(0, 10)}` : ""}`
              : "—";
            return (
              <Card key={m.id}>
                <CardContent className="flex items-start justify-between p-3 gap-2">
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{m.display_name || m.chart_name}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${ROLE_COLORS[m.role]}`}>
                        {ROLE_LABELS[m.role] ?? m.role}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-xs text-muted-foreground shrink-0">Current Dasha</span>
                      <span className="text-xs font-medium truncate">{dashaLabel}</span>
                    </div>
                    {ss ? (
                      ss.is_active ? (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                          ⚠ Sade Sati active — {ss.phase ?? "unknown"} phase
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
                          ✓ No Sade Sati
                        </span>
                      )
                    ) : null}
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
                    onClick={() => deleteMember.mutate(m.id)}
                    disabled={deleteMember.isPending}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}

          {showAddMember ? (
            <AddMemberForm groupId={groupId} onDone={() => setShowAddMember(false)} />
          ) : (
            <Button size="sm" variant="outline" className="w-full gap-2" onClick={() => setShowAddMember(true)}>
              <Plus className="h-4 w-4" /> Add Member
            </Button>
          )}
        </div>
      )}

      {activeTab === "compatibility" && <PoruthTab groupId={groupId} />}
    </div>

    {chatOpen && primaryChartId && (
      <div className="fixed top-0 right-0 h-full w-80 z-40">
        <ChatPanel
          baseChartId={primaryChartId}
          chartName={primaryChartName}
          mahadasha=""
          antardasha=""
          periodLabel={group.name}
          onClose={() => setChatOpen(false)}
          readingAsName={primaryChartName}
        />
      </div>
    )}
    </div>
  );
}


// ── Create Group Modal ────────────────────────────────────────────────────────

function CreateGroupForm({ onDone }: { onDone: (group: FamilyGroup) => void; onCancel: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");

  const createMutation = useMutation({
    mutationFn: (body: unknown) => apiFetch("POST", "/api/family/groups", body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["/api/family/groups"] });
      onDone(data);
    },
  });

  return (
    <Card className="max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Create Family Group</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Input
          placeholder="e.g. Our Family"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && name.trim() && createMutation.mutate({ name: name.trim() })}
          autoFocus
        />
        {createMutation.error && (
          <p className="text-sm text-destructive">{(createMutation.error as Error).message}</p>
        )}
        <div className="flex gap-2">
          <Button
            disabled={!name.trim() || createMutation.isPending}
            onClick={() => createMutation.mutate({ name: name.trim() })}
          >
            {createMutation.isPending ? "Creating…" : "Create"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}


// ── Main Screen ───────────────────────────────────────────────────────────────

export default function FamilyScreen() {
  const { user, isLoading: authLoading } = useAuth();
  const [, navigate] = useLocation();
  const [view, setView] = useState<"list" | "create" | "detail">("list");
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      navigate("/login");
    }
  }, [authLoading, user, navigate]);

  if (authLoading) return null;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {view === "list" && (
          <GroupList
            onSelect={(g) => { setSelectedGroupId(g.id); setView("detail"); }}
            onCreate={() => setView("create")}
          />
        )}

        {view === "create" && (
          <CreateGroupForm
            onDone={(g) => { setSelectedGroupId(g.id); setView("detail"); }}
            onCancel={() => setView("list")}
          />
        )}

        {view === "detail" && selectedGroupId && (
          <GroupDetail
            groupId={selectedGroupId}
            onBack={() => { setSelectedGroupId(null); setView("list"); }}
          />
        )}
      </div>
    </div>
  );
}
