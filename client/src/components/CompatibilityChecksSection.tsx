// client/src/components/CompatibilityChecksSection.tsx
// Phase G4: "Compatibility checks" list + "Check Compatibility" picker for
// the individual chart screen (chart-detail.tsx) -- Phase G1's
// chart-to-chart prospect links, independent of family groups.

import { useState } from "react";
import { Link, useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Heart, Plus, Trash2, ChevronRight } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";

interface ProspectSummary {
  id: string;
  other_chart_id: string;
  other_name: string;
  score: number | null;
  max_score: number | null;
  grade: string | null;
}

interface CandidateChart {
  chart_id: string;
  nickname: string;
  name: string;
}

async function apiJson(method: string, path: string, body?: unknown) {
  const res = await apiRequest(method, path, body);
  if (res.status === 204) return null;
  return res.json();
}

export function CompatibilityChecksSection({ chartId }: { chartId: string }) {
  const [, navigate] = useLocation();
  const qc = useQueryClient();
  const [showPicker, setShowPicker] = useState(false);
  const [candidateId, setCandidateId] = useState<string>("");
  const [sourceRole, setSourceRole] = useState<"boy" | "girl">("boy");
  const [createError, setCreateError] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["/api/charts", chartId, "prospects"],
    queryFn: () => apiJson("GET", `/api/charts/${chartId}/prospects`),
    enabled: !!chartId,
  });

  const { data: userChartsData } = useQuery({
    queryKey: ["/api/family/user-charts"],
    queryFn: () => apiJson("GET", "/api/family/user-charts"),
    enabled: showPicker,
  });

  const prospects: ProspectSummary[] = data?.prospects ?? [];
  const candidateCharts: CandidateChart[] = (userChartsData?.charts ?? []).filter(
    (c: CandidateChart) => c.chart_id !== chartId
  );

  const createMutation = useMutation({
    mutationFn: () =>
      apiJson("POST", "/api/prospects", {
        source_chart_id: chartId,
        candidate_chart_id: candidateId,
        source_role: sourceRole,
      }),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["/api/charts", chartId, "prospects"] });
      setShowPicker(false);
      setCandidateId("");
      setCreateError("");
      navigate(`/chart/${chartId}/prospects/${created.id}`);
    },
    onError: (err: Error) => setCreateError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (prospectId: string) => apiJson("DELETE", `/api/prospects/${prospectId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/charts", chartId, "prospects"] });
    },
  });

  return (
    <Card className="border-muted">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Heart className="h-4 w-4 text-rose-400" />
          Compatibility Checks
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => {
            setCreateError("");
            setShowPicker(true);
          }}
        >
          <Plus className="h-4 w-4" />
          Check Compatibility
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading && (
          <p className="text-sm text-muted-foreground py-2">Loading…</p>
        )}
        {!isLoading && prospects.length === 0 && (
          <p className="text-sm text-muted-foreground py-2">
            No compatibility checks yet. Check this chart against another chart you own.
          </p>
        )}
        {prospects.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between gap-2 py-2 px-1 rounded-md hover:bg-muted/50 cursor-pointer transition-colors"
            onClick={() => navigate(`/chart/${chartId}/prospects/${p.id}`)}
            data-testid={`row-prospect-${p.id}`}
          >
            <div className="min-w-0">
              <p className="font-medium truncate">{p.other_name || "Candidate"}</p>
              {p.score !== null && p.max_score !== null ? (
                <p className="text-xs text-muted-foreground">
                  {p.score}/{p.max_score} · {p.grade}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">Score unavailable</p>
              )}
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDeleteId(p.id);
                }}
                className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                aria-label="Delete compatibility check"
                data-testid={`button-delete-prospect-${p.id}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        ))}
      </CardContent>

      {/* Check Compatibility picker */}
      <Dialog open={showPicker} onOpenChange={setShowPicker}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Check Compatibility</DialogTitle>
            <DialogDescription>
              Pick another chart you own to check Porutham compatibility against.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Candidate chart</Label>
              <Select value={candidateId} onValueChange={setCandidateId}>
                <SelectTrigger data-testid="select-candidate-chart">
                  <SelectValue placeholder="Select a chart…" />
                </SelectTrigger>
                <SelectContent>
                  {candidateCharts.map((c) => (
                    <SelectItem key={c.chart_id} value={c.chart_id}>
                      {c.nickname || c.name || c.chart_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Don't see the chart you need?{" "}
                <Link href="/" className="underline">
                  Create a new chart
                </Link>{" "}
                first.
              </p>
            </div>

            <div className="space-y-2">
              <Label>This chart's role in the match</Label>
              <RadioGroup value={sourceRole} onValueChange={(v) => setSourceRole(v as "boy" | "girl")}>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="boy" id="role-boy" />
                  <Label htmlFor="role-boy" className="font-normal">Groom (boy)</Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="girl" id="role-girl" />
                  <Label htmlFor="role-girl" className="font-normal">Bride (girl)</Label>
                </div>
              </RadioGroup>
              <p className="text-xs text-muted-foreground">
                Some Porutham categories are direction-sensitive, so this determines how the match is scored.
              </p>
            </div>

            {createError && <p className="text-sm text-destructive">{createError}</p>}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowPicker(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!candidateId || createMutation.isPending}
              data-testid="button-submit-check-compatibility"
            >
              {createMutation.isPending ? "Checking…" : "Check Compatibility"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-80">
            <h3 className="font-semibold mb-2">Delete this compatibility check?</h3>
            <p className="text-gray-400 text-sm mb-4">
              This cannot be undone. The charts themselves are not affected.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  deleteMutation.mutate(confirmDeleteId);
                  setConfirmDeleteId(null);
                }}
                className="flex-1 bg-red-600 hover:bg-red-500 text-white py-2 rounded-lg text-sm font-medium"
              >
                Delete
              </button>
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-white py-2 rounded-lg text-sm font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
