import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "wouter";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SouthIndianChart } from "@/components/south-indian-chart";
import { StatusBadge } from "@/components/status-badge";
import { ArrowLeft, Calendar, Clock, MapPin, User, Sparkles } from "lucide-react";
import type { BaseChart } from "@shared/schema";

export default function ChartDetail() {
  const params = useParams<{ id: string }>();
  const chartId = params.id;

  const { data: chart, isLoading, error } = useQuery<BaseChart>({
    queryKey: ["/api/base-chart", chartId],
    enabled: !!chartId,
  });

  const samplePlanets = {
    "Su": 0,
    "Mo": 3,
    "Ma": 6,
    "Me": 0,
    "Ju": 9,
    "Ve": 1,
    "Sa": 10,
    "Ra": 5,
    "Ke": 11,
  };

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

  if (error || !chart) {
    return (
      <div className="container max-w-7xl mx-auto px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">Chart not found</p>
            <Link href="/">
              <Button variant="outline" data-testid="button-back-to-home">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/">
          <Button variant="ghost" size="icon" data-testid="button-back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-serif font-bold flex items-center gap-3">
            <Sparkles className="h-8 w-8 text-primary" />
            {chart.name}
          </h1>
          <p className="text-muted-foreground">Birth Chart Analysis</p>
        </div>
        <StatusBadge status={chart.status === "stub" ? "stub" : "ok"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <Tabs defaultValue="rasi" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="rasi" data-testid="tab-rasi">D1 Rasi Chart</TabsTrigger>
              <TabsTrigger value="navamsa" data-testid="tab-navamsa">D9 Navamsa</TabsTrigger>
            </TabsList>
            <TabsContent value="rasi">
              <Card>
                <CardHeader>
                  <CardTitle>Rasi Chart (D1)</CardTitle>
                  <CardDescription>
                    Birth chart showing planetary positions at time of birth
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex justify-center">
                  <SouthIndianChart lagna={0} planets={samplePlanets} size={400} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="navamsa">
              <Card>
                <CardHeader>
                  <CardTitle>Navamsa Chart (D9)</CardTitle>
                  <CardDescription>
                    Divisional chart for marriage and dharma analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex justify-center">
                  <SouthIndianChart lagna={4} planets={samplePlanets} size={400} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Birth Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Date of Birth</div>
                  <div className="text-muted-foreground">{chart.date_of_birth}</div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Time of Birth</div>
                  <div className="text-muted-foreground">{chart.time_of_birth}</div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Place of Birth</div>
                  <div className="text-muted-foreground">{chart.place_of_birth}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Coordinates</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Latitude</span>
                <span className="font-mono">{chart.latitude}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Longitude</span>
                <span className="font-mono">{chart.longitude}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Timezone</span>
                <span className="font-mono">{chart.timezone}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Calculation Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Method</span>
                <span>Drik Ganita</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Ayanamsa</span>
                <span>Lahiri</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Chart Style</span>
                <span>South Indian</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Chart ID</span>
                <span className="font-mono text-xs">{chart.id.substring(0, 12)}...</span>
              </div>
            </CardContent>
          </Card>

          <Link href="/predictions">
            <Button className="w-full gap-2" data-testid="button-generate-predictions">
              <Calendar className="h-4 w-4" />
              Generate Predictions
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
