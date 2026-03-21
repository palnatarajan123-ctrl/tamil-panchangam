// client/src/pages/chart-detail.tsx

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, Link } from "wouter";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { StatusBadge } from "@/components/status-badge";
import { DashaTimeline } from "@/components/DashaTimeline";
import { YogasPanel } from "@/components/YogasPanel";
import { SadeSatiPanel } from "@/components/SadeSatiPanel";
import { ShadbalaPanel } from "@/components/ShadbalaPanel";
import { NatalInterpretationPanel } from "@/components/NatalInterpretationPanel";
import { TabbedChartViewer } from "@/components/TabbedChartViewer";
import { 
  BirthAstroContextTable, 
  adaptBirthChartToAstroContext,
  type RealtimeContextData,
} from "@/components/BirthAstroContextTable";

import {
  ArrowLeft,
  Calendar,
  Clock,
  MapPin,
  User,
  Sparkles,
  Bookmark,
  BookmarkCheck,
} from "lucide-react";

import { apiRequest } from "@/lib/queryClient";
import { getAccessToken } from "@/lib/auth";
import { adaptBirthChart } from "@/adapters/birthChartAdapter";
import { useAuth } from "@/contexts/AuthContext";

export default function ChartDetail() {
  const { id: chartId } = useParams<{ id: string }>();
  const [activeChartTab, setActiveChartTab] = useState<string>("D1");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [nickname, setNickname] = useState("");
  const { user } = useAuth();


  const {
    data: rawView,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["/api/ui/birth-chart", chartId],
    enabled: !!chartId,
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/ui/birth-chart?base_chart_id=${chartId}`
      );
      const json = await res.json();
      if (!res.ok) throw new Error("Birth chart not found");
      if (json?.data?.view) return json.data.view;
      if (json?.view) return json.view;
      if (json?.identity) return json;
      throw new Error("Invalid birth chart response shape");
    },
  });

  const { data: realtimeContextData } = useQuery({
    queryKey: ["/api/realtime/context", chartId],
    enabled: !!chartId,
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/realtime/context/${chartId}`
      );
      if (!res.ok) return null;
      const json = await res.json();
      return json?.context as RealtimeContextData | null;
    },
    staleTime: 60000,
  });


  const saveChartMutation = useMutation({
    mutationFn: async (data: { nickname: string }) => {
      const res = await fetch("/api/user/charts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
        },
        body: JSON.stringify({
          base_chart_id: chartId,
          nickname: data.nickname,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: (data) => {
      setSaved(true);
      setShowSaveDialog(false);
      if (data?.already_saved) {
        setSaveError("Already in your My Charts");
      }
    },
    onError: (err: Error) => setSaveError(err.message),
  });


  if (isLoading) {
    return (
      <div className="container max-w-7xl mx-auto px-4 py-8">
        <Skeleton className="h-8 w-64 mb-8" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (error || !rawView) {
    return (
      <div className="container max-w-7xl mx-auto px-4 py-8">
        <Card className="border-muted">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">Chart not found</p>
            <Link href="/">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const ui = adaptBirthChart({ view: rawView });
  if (!ui || !ui.identity || !ui.southIndianChart) return null;

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>

        <div className="flex-1">
          <h1 className="text-3xl md:text-4xl font-serif font-semibold tracking-tight flex items-center gap-3">
            <Sparkles className="h-7 w-7 text-primary" />
            {ui.identity.name || "Birth Chart"}
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Immutable Birth Chart · Sidereal (Lahiri)
          </p>
        </div>

        <StatusBadge status="ok" />

        {/* Save chart button */}
        {user && !saved && (
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => {
              setNickname(ui.identity.name || "");
              setShowSaveDialog(true);
            }}
            disabled={saveChartMutation.isPending}
          >
            <Bookmark className="h-4 w-4" />
            Save
          </Button>
        )}
        {user && saved && (
          <Button variant="ghost" size="sm" className="gap-2 text-green-500" disabled>
            <BookmarkCheck className="h-4 w-4" />
            Saved
          </Button>
        )}
        {!user && (
          <Link href="/login">
            <Button variant="outline" size="sm" className="gap-2">
              <Bookmark className="h-4 w-4" />
              Save
            </Button>
          </Link>
        )}
        {saveError && (
          <p className="text-xs text-destructive">{saveError}</p>
        )}
      </div>

      {/* Save Chart Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Save Chart</DialogTitle>
            <DialogDescription>
              Give this chart a nickname to find it easily later.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="nickname">Nickname</Label>
            <Input
              id="nickname"
              placeholder="e.g. Self, Amma, Husband, Son..."
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter" && nickname.trim()) {
                  saveChartMutation.mutate({ nickname: nickname.trim() });
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowSaveDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => saveChartMutation.mutate({ nickname: nickname.trim() || (ui.identity.name ?? "Chart") })}
              disabled={saveChartMutation.isPending}
            >
              {saveChartMutation.isPending ? "Saving…" : "Save Chart"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Charts */}
        <div className="lg:col-span-2 space-y-6">
          <TabbedChartViewer
            charts={{
              D1: {
                lagna: ui.southIndianChart.lagna,
                planets: ui.southIndianChart.planets,
              },
              D2: ui.divisionalCharts?.D2,
              D7: ui.divisionalCharts?.D7,
              D9: {
                lagna: ui.navamsaChart.lagna,
                planets: ui.navamsaChart.planets,
                dignity: ui.navamsaChart.dignity,
              },
              D10: ui.divisionalCharts?.D10,
            }}
            onTabChange={setActiveChartTab}
          />

          {/* Only show reference context and AI interpretation for D1 */}
          {activeChartTab === "D1" && (
            <>
              <BirthAstroContextTable 
                data={adaptBirthChartToAstroContext(ui, undefined, realtimeContextData ?? undefined)} 
              />

              <DashaTimeline
                timeline={ui.vimshottari.timeline}
                current={
                  ui.vimshottari.current
                    ? {
                        maha: {
                          lord: ui.vimshottari.current.lord,
                          start: ui.vimshottari.current.start,
                          end: ui.vimshottari.current.end,
                          is_partial: ui.vimshottari.current.is_partial,
                        },
                        antar: ui.vimshottari.current.antar ?? null,
                      }
                    : undefined
                }
              />
            </>
          )}

          {/* Yogas & Sade Sati — Only for D1 */}
          {activeChartTab === "D1" && (
            <>
              <YogasPanel yogas={ui.yogas} />
              <SadeSatiPanel sadeSati={ui.sade_sati} />
              <ShadbalaPanel shadbala={ui.shadbala} />
            </>
          )}

          {/* Natal Chart Reading - Only for D1 */}
          {activeChartTab === "D1" && chartId && (
            <NatalInterpretationPanel chartId={chartId} />
          )}

        </div>

        {/* Sidebar */}
        <div className="space-y-6 lg:sticky lg:top-24">
          <Card className="border-muted">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Birth Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Date</div>
                  <div className="text-muted-foreground">{ui.birth.date}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Time</div>
                  <div className="text-muted-foreground">{ui.birth.time}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Place</div>
                  <div className="text-muted-foreground">
                    {ui.identity.place}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Link href={`/chart/${chartId}/predictions`}>
            <Button className="w-full gap-2 mt-2">
              <Calendar className="h-4 w-4" />
              Generate Predictions
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
