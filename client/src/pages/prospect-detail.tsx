// client/src/pages/prospect-detail.tsx
// Phase G4: prospect detail view -- full Porutham breakdown for one
// Phase G1 chart-to-chart compatibility check, plus "Ask Jyotishi about
// this match", "View PDF", "Proceed to Family", and "Delete" actions.

import { useState } from "react";
import { useParams, useLocation, Link } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PoruthamBreakdown, type PoruthResult, type PoruthamPerson } from "@/components/PoruthamBreakdown";
import { ChatPanel } from "@/components/ChatPanel";
import { ArrowLeft, MessageCircle, FileText, Users, Trash2, AlertCircle } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";

interface ProspectPoruthamResponse {
  boy: PoruthamPerson & { chart_id: string };
  girl: PoruthamPerson & { chart_id: string };
  porutham: PoruthResult;
  commentary?: string | null;
}

async function apiJson(method: string, path: string, body?: unknown) {
  const res = await apiRequest(method, path, body);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export default function ProspectDetail() {
  const { chartId, prospectId } = useParams<{ chartId: string; prospectId: string }>();
  const [, navigate] = useLocation();
  const qc = useQueryClient();
  const [chatOpen, setChatOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [convertError, setConvertError] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["/api/prospects", prospectId, "porutham"],
    queryFn: async (): Promise<ProspectPoruthamResponse> => apiJson("GET", `/api/prospects/${prospectId}/porutham`),
    enabled: !!prospectId,
  });

  const convertMutation = useMutation({
    mutationFn: () => apiJson("POST", `/api/prospects/${prospectId}/convert-to-family`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/family/groups"] });
      navigate("/family");
    },
    onError: (err: Error) => setConvertError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiJson("DELETE", `/api/prospects/${prospectId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/charts", chartId, "prospects"] });
      navigate(`/chart/${chartId}`);
    },
  });

  if (isLoading) {
    return (
      <div className="container max-w-2xl mx-auto px-4 py-8">
        <Skeleton className="h-8 w-64 mb-8" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container max-w-2xl mx-auto px-4 py-8">
        <Card className="border-muted">
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-6 w-6 mx-auto mb-2 text-amber-500" />
            <p className="text-muted-foreground mb-4">
              {error instanceof Error ? error.message : "Compatibility check not found"}
            </p>
            <Link href={`/chart/${chartId}`}>
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Chart
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const anchorIsBoy = data.boy.chart_id === chartId;
  const anchorPerson = anchorIsBoy ? data.boy : data.girl;
  const otherPerson = anchorIsBoy ? data.girl : data.boy;

  return (
    <div className="container max-w-2xl mx-auto px-4 py-8">
      <div className={chatOpen ? "mr-80 transition-all duration-300" : "transition-all duration-300"}>
        <div className="flex items-center gap-4 mb-6">
          <Link href={`/chart/${chartId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-2xl font-serif font-semibold tracking-tight">
            Compatibility Check
          </h1>
        </div>

        <Card className="border-muted">
          <CardContent className="pt-6">
            <PoruthamBreakdown
              personA={data.boy}
              personB={data.girl}
              personALabel="Groom"
              personBLabel="Bride"
              result={data.porutham}
              commentary={data.commentary}
              context="prospect"
            />
          </CardContent>
        </Card>

        {convertError && (
          <p className="text-sm text-destructive mt-3">{convertError}</p>
        )}

        <div className="flex flex-wrap gap-2 mt-4">
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => setChatOpen((v) => !v)}
            data-testid="button-ask-jyotishi-prospect"
          >
            <MessageCircle className="h-4 w-4" />
            {chatOpen ? "Close Chat" : "Ask Jyotishi about this match"}
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => window.open(`/api/reports/birth-chart-pdf?base_chart_id=${chartId}`, "_blank")}
            data-testid="button-view-pdf-prospect"
          >
            <FileText className="h-4 w-4" />
            View PDF
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => convertMutation.mutate()}
            disabled={convertMutation.isPending}
            data-testid="button-proceed-to-family"
          >
            <Users className="h-4 w-4" />
            {convertMutation.isPending ? "Creating…" : "Proceed to Family"}
          </Button>
          <Button
            variant="outline"
            className="gap-2 text-destructive hover:text-destructive"
            onClick={() => setConfirmDelete(true)}
            data-testid="button-delete-prospect-detail"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {chatOpen && (
        <div className="fixed top-12 md:top-0 right-0 bottom-0 w-80 z-40 shadow-xl border-l border-border">
          <ChatPanel
            baseChartId={chartId}
            chartName={anchorPerson.name || "This chart"}
            mahadasha=""
            antardasha=""
            periodLabel={`Compatibility with ${otherPerson.name || "candidate"}`}
            onClose={() => setChatOpen(false)}
          />
        </div>
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-80">
            <h3 className="font-semibold mb-2">Delete this compatibility check?</h3>
            <p className="text-gray-400 text-sm mb-4">
              This cannot be undone. The charts themselves are not affected.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  deleteMutation.mutate();
                  setConfirmDelete(false);
                }}
                className="flex-1 bg-red-600 hover:bg-red-500 text-white py-2 rounded-lg text-sm font-medium"
              >
                Delete
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-white py-2 rounded-lg text-sm font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
