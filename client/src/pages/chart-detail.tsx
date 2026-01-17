import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "wouter";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { SouthIndianChart } from "@/components/south-indian-chart";
import { StatusBadge } from "@/components/status-badge";
import { DashaTimeline } from "@/components/DashaTimeline";

import {
  ArrowLeft,
  Calendar,
  Clock,
  MapPin,
  User,
  Sparkles,
} from "lucide-react";

import { apiRequest } from "@/lib/queryClient";
import { adaptBirthChart } from "@/adapters/birthChartAdapter";

<Link href={`/charts/${baseChartId}/predictions`}>
  <Button variant="outline">Predictions</Button>
</Link>

export default function ChartDetail() {
  const { id: chartId } = useParams<{ id: string }>();

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

  /* ---------------- Loading ---------------- */

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

  /* ---------------- Adapter ---------------- */

  const ui = adaptBirthChart({ view: rawView });

  console.log("🪐 South Indian Chart – lagna:", ui.southIndianChart?.lagna);
  console.log("🪐 South Indian Chart – planets:", ui.southIndianChart?.planets);


  if (!ui || !ui.identity || !ui.southIndianChart) {
    return null;
  }

  /* ---------------- UI ---------------- */

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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Chart */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-muted/30 border-muted">
            <CardHeader>
              <CardTitle>Rāsi Chart (D1)</CardTitle>
              <CardDescription>
                Planetary positions at birth
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center bg-muted/40 rounded-lg py-8">
              <SouthIndianChart
                lagna={ui.southIndianChart.lagna}
                planets={ui.southIndianChart.planets}
                size={400}
              />
            </CardContent>
          </Card>

          <Tabs defaultValue="rasi">
            <TabsList className="inline-grid grid-cols-3 w-fit bg-muted/50">
              <TabsTrigger value="rasi">Rāsi</TabsTrigger>
              <TabsTrigger value="nakshatra">Nakshatra</TabsTrigger>
              <TabsTrigger value="houses">Houses</TabsTrigger>
            </TabsList>

            <TabsContent value="rasi">
              <Card className="border-muted">
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4 py-6">
                  {ui.rasi.map((r) => (
                    <div key={r.name}>
                      <div className="font-medium mb-1">{r.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {r.planets.join(", ") || "—"}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="nakshatra">
              <Card className="border-muted">
                <CardContent className="py-6 space-y-6">
                  {(() => {
                    // Nakshatras that actually contain planets
                    const occupied = ui.nakshatra.filter(
                      (n) => n.planets && n.planets.length > 0
                    );

                    if (occupied.length === 0) {
                      return (
                        <div className="text-sm text-muted-foreground">
                          No planetary Nakshatra data available.
                        </div>
                      );
                    }

                    return occupied.map((n) => {
                      const isJanma = n.planets.includes("Moon");

                      return (
                        <div
                          key={n.name}
                          className={`rounded-lg border p-4 ${
                            isJanma
                              ? "border-primary bg-primary/5"
                              : "border-muted bg-muted/20"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="font-medium text-lg">
                              {n.name}
                            </div>

                            {isJanma && (
                              <span className="text-xs font-semibold text-primary">
                                Janma Nakshatra
                              </span>
                            )}
                          </div>

                          <div className="text-sm">
                            Planets:{" "}
                            <span className="font-medium">
                              {n.planets.join(", ")}
                            </span>
                          </div>

                          {/* Optional: Pada display if present */}
                          {n.padas && n.padas.length > 0 && (
                            <div className="text-xs text-muted-foreground mt-1">
                              Pada: {n.padas.join(", ")}
                            </div>
                          )}
                        </div>
                      );
                    });
                  })()}

                  {/* Explanation */}
                  <div className="text-xs text-muted-foreground pt-4 border-t border-muted">
                    Nakshatra analysis is Moon-centric in Vedic astrology.  
                    Janma Nakshatra (Moon’s Nakshatra) carries primary interpretive weight.
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="houses">
              <Card className="border-muted">
                <CardContent className="space-y-4 py-6">
                  {ui.houses.map((h) => (
                    <div
                      key={h.number}
                      className="border-l-2 border-muted pl-4 py-3"
                    >
                      <div className="font-medium mb-1">
                        House {h.number} · {h.rasi}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Lord: {h.lord} · {h.significations}
                      </div>
                      <div className="text-sm">
                        Planets: {h.planets.join(", ") || "—"}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          <DashaTimeline
            timeline={ui.vimshottari.timeline}
            current={
              ui.vimshottari.current
                ? { lord: ui.vimshottari.current }
                : undefined
            }
          />
        </div>

        {/* Birth Details */}
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
                  <div className="text-muted-foreground">{ui.birth?.date}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Time</div>
                  <div className="text-muted-foreground">{ui.birth?.time}</div>
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

          <Link href={`/predictions/${chartId}`}>
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
