import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiRequest } from "@/lib/queryClient";
import { useLocation } from "wouter";
import { useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, BarChart2, FileText, ScrollText } from "lucide-react";

// ── Stats tab ────────────────────────────────────────────────────────────────

function StatsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/admin/stats"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/stats");
      return res.json();
    },
  });

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="Total Users" value={data?.users?.total ?? 0} />
      <StatCard label="Active Users" value={data?.users?.active ?? 0} />
      <StatCard label="New (7d)" value={data?.users?.new_7d ?? 0} />
      <StatCard label="Total Charts" value={data?.charts?.total ?? 0} />
      <StatCard label="Saved Charts" value={data?.charts?.saved ?? 0} />
      <StatCard label="Predictions" value={data?.predictions?.total ?? 0} />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="py-4 text-center">
        <p className="text-3xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground mt-1">{label}</p>
      </CardContent>
    </Card>
  );
}

// ── Users tab ─────────────────────────────────────────────────────────────────

function UsersTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["/api/admin/users"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/users");
      return res.json();
    },
  });

  const updateUser = useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Record<string, unknown> }) => {
      await apiRequest("PUT", `/api/admin/users/${id}`, updates);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/admin/users"] }),
  });

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  const users = data?.users ?? [];

  return (
    <div className="space-y-2">
      {users.map((u: {
        id: string; email: string; name: string; role: string;
        is_active: boolean; created_at: string; last_login_at: string | null;
      }) => (
        <Card key={u.id} className="border-muted">
          <CardContent className="py-3">
            <div className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{u.name}</p>
                <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                <p className="text-[10px] text-muted-foreground">
                  Joined {u.created_at.slice(0, 10)}
                  {u.last_login_at ? ` · Last login ${u.last_login_at.slice(0, 10)}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge variant={u.role === "admin" ? "default" : "secondary"}>
                  {u.role}
                </Badge>
                <Badge variant={u.is_active ? "outline" : "destructive"}>
                  {u.is_active ? "active" : "disabled"}
                </Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => updateUser.mutate({ id: u.id, updates: { is_active: !u.is_active } })}
                  disabled={updateUser.isPending}
                >
                  {u.is_active ? "Disable" : "Enable"}
                </Button>
                {u.role !== "admin" && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => updateUser.mutate({ id: u.id, updates: { role: "admin" } })}
                    disabled={updateUser.isPending}
                  >
                    Make Admin
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Charts tab ────────────────────────────────────────────────────────────────

function ChartsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/admin/charts"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/charts");
      return res.json();
    },
  });

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  const charts = data?.charts ?? [];

  return (
    <div className="space-y-2">
      {charts.map((c: {
        id: string; user_email: string | null; user_name: string | null;
        nickname: string | null; saved_at: string | null;
      }) => (
        <div key={c.id} className="flex items-center gap-3 py-2 border-b border-border/40 text-sm">
          <span className="font-mono text-xs text-muted-foreground w-20 shrink-0 truncate">{c.id.slice(0, 8)}</span>
          <span className="flex-1 truncate">{c.nickname || c.user_name || "Anonymous"}</span>
          <span className="text-xs text-muted-foreground truncate">{c.user_email ?? "public"}</span>
          <span className="text-xs text-muted-foreground">{c.saved_at?.slice(0, 10) ?? ""}</span>
        </div>
      ))}
      {charts.length === 0 && <p className="text-sm text-muted-foreground">No charts found.</p>}
    </div>
  );
}

// ── Audit log tab ─────────────────────────────────────────────────────────────

function AuditTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/admin/audit-log"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/audit-log");
      return res.json();
    },
  });

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  const entries = data?.entries ?? [];

  return (
    <div className="space-y-1">
      {entries.map((e: {
        id: string; action: string; user_id: string | null;
        ip_address: string | null; created_at: string;
      }) => (
        <div key={e.id} className="flex items-center gap-3 py-1.5 border-b border-border/30 text-xs">
          <span className="text-muted-foreground w-32 shrink-0">{e.created_at.slice(0, 16)}</span>
          <Badge variant="outline" className="text-[10px] px-1">{e.action}</Badge>
          <span className="flex-1 text-muted-foreground truncate">{e.user_id ?? "anon"}</span>
          <span className="text-muted-foreground">{e.ip_address ?? ""}</span>
        </div>
      ))}
      {entries.length === 0 && <p className="text-sm text-muted-foreground">No audit entries.</p>}
    </div>
  );
}

// ── Page root ─────────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const { user, isLoading } = useAuth();
  const [, navigate] = useLocation();

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "admin")) {
      navigate("/");
    }
  }, [user, isLoading, navigate]);

  if (isLoading) return <Skeleton className="h-40 w-full mt-8" />;
  if (!user || user.role !== "admin") return null;

  return (
    <div className="max-w-5xl mx-auto py-8 space-y-6">
      <div className="flex items-center gap-2">
        <BarChart2 className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-serif font-bold">Admin Dashboard</h1>
      </div>

      <Tabs defaultValue="stats">
        <TabsList>
          <TabsTrigger value="stats" className="gap-2">
            <BarChart2 className="h-4 w-4" /> Stats
          </TabsTrigger>
          <TabsTrigger value="users" className="gap-2">
            <Users className="h-4 w-4" /> Users
          </TabsTrigger>
          <TabsTrigger value="charts" className="gap-2">
            <FileText className="h-4 w-4" /> Charts
          </TabsTrigger>
          <TabsTrigger value="audit" className="gap-2">
            <ScrollText className="h-4 w-4" /> Audit Log
          </TabsTrigger>
        </TabsList>

        <TabsContent value="stats" className="mt-4">
          <StatsTab />
        </TabsContent>
        <TabsContent value="users" className="mt-4">
          <UsersTab />
        </TabsContent>
        <TabsContent value="charts" className="mt-4">
          <ChartsTab />
        </TabsContent>
        <TabsContent value="audit" className="mt-4">
          <AuditTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
