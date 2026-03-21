import { useState, useEffect } from "react";
import { useLocation, Link } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, Pencil, Trash2, Eye, Sparkles } from "lucide-react";

interface SavedChart {
  id: string;
  base_chart_id: string;
  nickname: string;
  name: string;
  date_of_birth: string;
  place_of_birth: string;
  created_at: string;
}

export default function MyCharts() {
  const { user, isLoading: authLoading } = useAuth();
  const [, navigate] = useLocation();
  const qc = useQueryClient();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");

  // Redirect to login when auth is resolved and user is not logged in
  useEffect(() => {
    if (!authLoading && !user) {
      navigate("/login");
    }
  }, [authLoading, user, navigate]);

  const { data, isLoading } = useQuery({
    queryKey: ["/api/user/charts"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/user/charts");
      return res.json();
    },
    enabled: !!user,
  });

  const renameMutation = useMutation({
    mutationFn: async ({ id, nickname }: { id: string; nickname: string }) => {
      await apiRequest("PUT", `/api/user/charts/${id}/nickname`, { nickname });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/user/charts"] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/user/charts/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/user/charts"] });
    },
  });

  if (authLoading || !user) {
    return (
      <div className="max-w-4xl mx-auto py-8 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
      </div>
    );
  }

  const charts: SavedChart[] = data?.charts ?? [];

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex items-center gap-2">
        <BookOpen className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-serif font-bold">My Saved Charts</h1>
        <span className="text-sm text-muted-foreground ml-2">
          ({charts.length} / 10)
        </span>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      )}

      {!isLoading && charts.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground space-y-3">
            <p>No saved charts yet.</p>
            <Link href="/">
              <Button variant="outline">Generate a Chart</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {charts.map((chart) => (
          <Card key={chart.id} className="border-muted">
            <CardContent className="py-4">
              <div className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  {editingId === chart.id ? (
                    <div className="flex gap-2">
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-8 text-sm"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === "Enter") renameMutation.mutate({ id: chart.id, nickname: editName });
                          if (e.key === "Escape") setEditingId(null);
                        }}
                      />
                      <Button
                        size="sm"
                        onClick={() => renameMutation.mutate({ id: chart.id, nickname: editName })}
                        disabled={renameMutation.isPending}
                      >
                        Save
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <>
                      <p className="font-medium truncate">{chart.nickname}</p>
                      <p className="text-xs text-muted-foreground">
                        {chart.date_of_birth}{chart.place_of_birth ? ` · ${chart.place_of_birth}` : ""}
                      </p>
                    </>
                  )}
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    title="View chart"
                    onClick={() => navigate(`/chart/${chart.base_chart_id}`)}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    title="Rename"
                    onClick={() => {
                      setEditingId(chart.id);
                      setEditName(chart.nickname);
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    title="Remove"
                    className="text-destructive hover:text-destructive"
                    onClick={() => deleteMutation.mutate(chart.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
